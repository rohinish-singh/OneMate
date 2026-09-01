import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.material import ImportSummary, MaterialDetailResponse
from app.services.ingestion import process_material_import
from app.services.normalization import normalize_material_record
from app.models import Material

router = APIRouter()

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/import", response_model=ImportSummary)
async def import_materials(
    cpse_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Ingest a CSV or XLSX file of materials for a specific CPSE.
    """
    # 1. File Type Validation
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")

    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.csv') or filename_lower.endswith('.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload .csv or .xlsx"
        )

    # 2. File Size Validation
    file_contents = await file.read()
    if len(file_contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
        )

    if len(file_contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

    # 3. Process Import
    try:
        summary = process_material_import(
            db=db,
            cpse_id=cpse_id,
            file_contents=file_contents,
            filename=file.filename
        )
        return summary
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Avoid exposing raw DB/internal exceptions
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during import: {str(e)}")

@router.post("/{material_id}/normalize")
def normalize_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Apply deterministic normalization rules to a single material.
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    try:
        audit_log = normalize_material_record(db, material)
        db.commit()
        return {
            "status": "success",
            "material_id": str(material.id),
            "normalized": audit_log is not None
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")

from app.services.matching import create_match_recommendations

@router.post("/{material_id}/match")
def match_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Generate and persist match recommendations for a single material.
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    try:
        recommendations = create_match_recommendations(db, material)
        db.commit()

        return {
            "status": "success",
            "material_id": str(material.id),
            "candidate_count": len(recommendations),
            "recommendations_created": len(recommendations),
            "recommendations": [
                {
                    "candidate_id": str(r.candidate_material_id),
                    "classification": r.classification,
                    "confidence": float(r.confidence) if r.confidence is not None else 0.0,
                    "explanation": r.explanation
                }
                for r in recommendations
            ]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")

from app.services.harmonization import harmonize_material

@router.post("/{material_id}/harmonize")
def harmonize_material_endpoint(
    material_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Attempt to safely auto-harmonize the material.
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    try:
        result = harmonize_material(db, material)
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Harmonization failed: {str(e)}")



@router.get("/{material_id}", response_model=MaterialDetailResponse, status_code=status.HTTP_200_OK)
def get_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get full details for a single material.
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material

from app.schemas.material import MaterialMappingHistory, MaterialDeleteResponse
from typing import List
from app.models import MaterialNationalMapping, MatchRecommendation
from app.api.deps import get_current_reviewer

@router.get("/{material_id}/mapping-history", response_model=List[MaterialMappingHistory])
def get_material_mapping_history(
    material_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get the mapping history for a single material.
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    history = db.query(MaterialNationalMapping).filter(
        MaterialNationalMapping.material_id == material_id
    ).order_by(MaterialNationalMapping.created_at.desc()).all()
    return history


@router.delete("/{material_id}", response_model=MaterialDeleteResponse, status_code=status.HTTP_200_OK)
def delete_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    reviewer: str = Depends(get_current_reviewer)
):
    """
    Delete a single Material and its dependent operational data.
    Atomically removes:
    1. Dependent MaterialNationalMapping rows for this material
    2. Dependent MatchRecommendation rows where this material is source or candidate
    3. The Material record
    National Materials and AuditLog rows are preserved.
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    try:
        # 1. Delete dependent MaterialNationalMapping rows
        db.query(MaterialNationalMapping).filter(
            MaterialNationalMapping.material_id == material_id
        ).delete(synchronize_session=False)

        # 2. Delete dependent MatchRecommendation rows
        db.query(MatchRecommendation).filter(
            (MatchRecommendation.source_material_id == material_id) |
            (MatchRecommendation.candidate_material_id == material_id)
        ).delete(synchronize_session=False)

        # 3. Delete the Material
        db.delete(material)
        db.commit()

        return MaterialDeleteResponse(
            status="success",
            deleted_id=str(material_id),
            deleted_type="MATERIAL"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete material: {str(e)}"
        )
