from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import NationalMaterial
from app.schemas.national_material import NationalMaterialListResponse, NationalMaterialDetailResponse

router = APIRouter()

@router.get("", response_model=List[NationalMaterialListResponse])
def get_national_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get a list of national materials.
    """
    materials = db.query(NationalMaterial).offset(skip).limit(limit).all()
    return materials

@router.get("/{national_material_id}", response_model=NationalMaterialDetailResponse)
def get_national_material(
    national_material_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a single national material by ID.
    """
    material = db.query(NationalMaterial).filter(NationalMaterial.id == national_material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="National material not found")
    return material
