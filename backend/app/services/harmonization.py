import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Material, NationalMaterial, MatchRecommendation, MaterialNationalMapping, AuditLog

def get_identity_key(material: Material) -> Optional[str]:
    """
    Constructs a deterministic identity key if and only if all identity-defining
    attributes are strictly known. Returns None if any attribute is missing.
    """
    attrs = [
        material.category,
        material.valve_type,
        material.size,
        material.body_material,
        material.pressure_class,
        material.connection_type,
        material.trim,
        material.normalized_uom
    ]
    if any(attr is None for attr in attrs):
        return None

    return "|".join(str(a) for a in attrs)

def generate_canonical_desc(material: Material) -> str:
    """
    Generates a deterministic canonical description.
    Assumes identity is complete.
    """
    return f"{material.valve_type} VALVE {material.size} {material.body_material} {material.pressure_class} {material.connection_type} {material.trim} TRIM"

def harmonize_material(db: Session, material: Material) -> Dict[str, Any]:
    """
    Orchestrates the safe automatic harmonization of a Material.
    """
    # 1. Check for existing active mapping
    existing = db.query(MaterialNationalMapping).filter_by(
        material_id=material.id,
        status="ACTIVE"
    ).first()

    if existing:
        return {
            "status": "skipped",
            "reason": "Material already has an ACTIVE mapping.",
            "mapping_id": str(existing.id)
        }

    # 2. Check source identity completeness
    identity_key = get_identity_key(material)
    if not identity_key:
        return {
            "status": "skipped",
            "reason": "Incomplete identity (NULL attribute present); human review required."
        }

    # 3. Find eligible SAME recommendation
    recs = db.query(MatchRecommendation).filter_by(
        source_material_id=material.id,
        classification="SAME"
    ).all()

    if not recs:
        return {
            "status": "skipped",
            "reason": "No SAME recommendation found."
        }

    eligible_cand = None
    eligible_rec = None
    for rec in recs:
        cand = db.query(Material).filter_by(id=rec.candidate_material_id).first()
        if not cand:
            continue

        cand_key = get_identity_key(cand)
        if cand_key and cand_key == identity_key:
            eligible_cand = cand
            eligible_rec = rec
            break

    if not eligible_cand:
        return {
            "status": "skipped",
            "reason": "No SAME recommendation found with a completely known and matching candidate identity."
        }

    # 4. Get or Create NationalMaterial
    nm = db.query(NationalMaterial).filter_by(identity_key=identity_key).first()
    nm_action = "REUSED"

    if not nm:
        nm = NationalMaterial(
            id=uuid.uuid4(),
            national_code=f"NM-{uuid.uuid4().hex[:8].upper()}",
            identity_key=identity_key,
            canonical_description=generate_canonical_desc(material),
            category=material.category,
            valve_type=material.valve_type,
            size=material.size,
            body_material=material.body_material,
            pressure_class=material.pressure_class,
            connection_type=material.connection_type,
            trim=material.trim,
            normalized_uom=material.normalized_uom,
            status="ACTIVE"
        )
        db.add(nm)
        db.flush()
        nm_action = "CREATED"

        audit_nm = AuditLog(
            id=uuid.uuid4(),
            actor="system_harmonization",
            action="CREATE_NATIONAL_MATERIAL",
            entity_type="NATIONAL_MATERIAL",
            entity_id=str(nm.id),
            before_state=None,
            after_state={"identity_key": identity_key, "national_code": nm.national_code},
            reason=f"Auto-created from Material {material.id}"
        )
        db.add(audit_nm)

    # 5. Create Active Mapping
    mapping = MaterialNationalMapping(
        id=uuid.uuid4(),
        material_id=material.id,
        national_material_id=nm.id,
        basis="AUTO_SAME",
        status="ACTIVE",
        recommendation_id=eligible_rec.id
    )
    db.add(mapping)
    db.flush()

    audit_map = AuditLog(
        id=uuid.uuid4(),
        actor="system_harmonization",
        action="CREATE_MAPPING",
        entity_type="MATERIAL_NATIONAL_MAPPING",
        entity_id=str(mapping.id),
        before_state=None,
        after_state={"material_id": str(material.id), "national_material_id": str(nm.id), "basis": mapping.basis},
        reason=f"Auto-mapped based on SAME recommendation {eligible_rec.id} with candidate {eligible_cand.id}"
    )
    db.add(audit_map)

    return {
        "status": "success",
        "national_material_id": str(nm.id),
        "national_material_action": nm_action,
        "mapping_id": str(mapping.id),
        "national_code": nm.national_code
    }
