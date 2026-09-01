import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import (
    Material, NationalMaterial, MatchRecommendation,
    MaterialNationalMapping, AuditLog
)
from app.services.harmonization import get_identity_key, generate_canonical_desc

def get_review_queue(db: Session, limit: int = 150) -> List[Dict[str, Any]]:
    """
    Returns recommendations with authoritative mapping and classification state.
    Includes unresolved POTENTIALLY_EQUIVALENT recommendations, DIFFERENT recommendations,
    and recommendations associated with completed MAPPED records.
    """
    recs = db.query(MatchRecommendation).order_by(MatchRecommendation.created_at.desc()).limit(limit).all()
    if not recs:
        return []

    src_ids = [rec.source_material_id for rec in recs]
    mappings = db.query(
        MaterialNationalMapping.material_id,
        MaterialNationalMapping.basis,
        NationalMaterial.id.label("nm_id"),
        NationalMaterial.national_code
    ).join(
        NationalMaterial, MaterialNationalMapping.national_material_id == NationalMaterial.id
    ).filter(
        MaterialNationalMapping.material_id.in_(src_ids),
        MaterialNationalMapping.status == "ACTIVE"
    ).all()
    mapping_dict = {row.material_id: (row.national_code, row.nm_id, row.basis) for row in mappings}

    queue = []
    for rec in recs:
        src = db.get(Material, rec.source_material_id)
        if not src:
            continue

        if rec.source_material_id in mapping_dict:
            nm_code, nm_id, basis = mapping_dict[rec.source_material_id]
            m_status = "MAPPED"
        elif rec.classification == "POTENTIALLY_EQUIVALENT":
            nm_code, nm_id, basis = None, None, None
            m_status = "NEEDS REVIEW"
        elif rec.classification == "DIFFERENT":
            nm_code, nm_id, basis = None, None, None
            m_status = "DIFFERENT"
        else:
            nm_code, nm_id, basis = None, None, None
            m_status = "UNMATCHED"

        queue.append({
            "recommendation_id": str(rec.id),
            "source_material_id": str(rec.source_material_id),
            "candidate_material_id": str(rec.candidate_material_id),
            "classification": rec.classification,
            "confidence": rec.confidence,
            "evidence": rec.evidence,
            "explanation": rec.explanation,
            "mapping_status": m_status,
            "national_material_code": nm_code,
            "national_material_id": str(nm_id) if nm_id else None,
            "mapping_basis": basis,
            "source_valve_type": src.valve_type,
            "source_size": src.size,
            "source_body_material": src.body_material,
            "source_pressure_class": src.pressure_class,
            "source_connection_type": src.connection_type,
            "source_trim": src.trim
        })
    return queue


def process_review_action(
    db: Session,
    recommendation_id: uuid.UUID,
    action: str,
    reason: str,
    national_material_id: uuid.UUID = None,
    actor: str = "human_reviewer"
) -> Dict[str, Any]:
    """
    Processes a human review action.
    """
    action = action.upper()
    if action in ["REJECT", "MARK_DIFFERENT", "OVERRIDE"] and not reason.strip():
        raise ValueError(f"Reason is required for {action}.")

    rec = db.get(MatchRecommendation, recommendation_id)
    if not rec:
        raise ValueError("Recommendation not found.")

    src = db.get(Material, rec.source_material_id)
    cand = db.get(Material, rec.candidate_material_id)

    # Check mapping safety
    existing_mapping = db.query(MaterialNationalMapping).filter_by(
        material_id=src.id, status="ACTIVE"
    ).first()

    if existing_mapping:
        raise ValueError("Material already has an ACTIVE mapping. Unmap or explicitly remap first.")

    mapping = None
    nm = None

    if action == "ACCEPT":
        # Ensure identity is complete
        identity_key = get_identity_key(src)
        if not identity_key:
            raise ValueError("Cannot ACCEPT: source material has incomplete identity. Use OVERRIDE to map to a specific NationalMaterial.")

        # Re-use or Create NM (same logic as P3)
        nm = db.query(NationalMaterial).filter_by(identity_key=identity_key).first()
        if not nm:
            nm = NationalMaterial(
                id=uuid.uuid4(),
                national_code=f"NM-{uuid.uuid4().hex[:8].upper()}",
                identity_key=identity_key,
                canonical_description=generate_canonical_desc(src),
                category=src.category,
                valve_type=src.valve_type,
                size=src.size,
                body_material=src.body_material,
                pressure_class=src.pressure_class,
                connection_type=src.connection_type,
                trim=src.trim,
                normalized_uom=src.normalized_uom,
                status="ACTIVE"
            )
            db.add(nm)
            db.flush()

            # Audit NM creation
            db.add(AuditLog(
                id=uuid.uuid4(),
                actor=actor,
                action="CREATE_NATIONAL_MATERIAL",
                entity_type="NATIONAL_MATERIAL",
                entity_id=str(nm.id),
                before_state=None,
                after_state={"identity_key": identity_key},
                reason=reason or f"Human confirmed SAME from recommendation {rec.id}"
            ))

        # Create mapping
        mapping = MaterialNationalMapping(
            id=uuid.uuid4(),
            material_id=src.id,
            national_material_id=nm.id,
            basis="HUMAN_CONFIRMED_SAME",
            status="ACTIVE",
            recommendation_id=rec.id
        )
        db.add(mapping)
        db.flush()

    elif action == "OVERRIDE":
        if not national_material_id:
            raise ValueError("OVERRIDE requires a specific national_material_id.")

        nm = db.get(NationalMaterial, national_material_id)
        if not nm:
            raise ValueError("Target NationalMaterial does not exist.")

        mapping = MaterialNationalMapping(
            id=uuid.uuid4(),
            material_id=src.id,
            national_material_id=nm.id,
            basis="HUMAN_OVERRIDE",
            status="ACTIVE",
            recommendation_id=rec.id
        )
        db.add(mapping)
        db.flush()

    elif action in ["REJECT", "MARK_DIFFERENT"]:
        # No mapping is created
        pass
    else:
        raise ValueError(f"Unknown action: {action}")

    # Audit the human action
    after_state = {}
    if mapping:
        after_state = {
            "mapping_id": str(mapping.id),
            "national_material_id": str(mapping.national_material_id),
            "basis": mapping.basis
        }

    db.add(AuditLog(
        id=uuid.uuid4(),
        actor=actor,
        action=action,
        entity_type="MATCH_RECOMMENDATION",
        entity_id=str(rec.id),
        before_state={"classification": rec.classification},
        after_state=after_state,
        reason=reason or f"Action {action} taken"
    ))

    db.commit()

    return {
        "status": "success",
        "action": action,
        "mapping_id": str(mapping.id) if mapping else None,
        "national_material_id": str(nm.id) if nm else None
    }
