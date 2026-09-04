import uuid
from typing import Optional, Dict, Any, List
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models import Material, NationalMaterial, MatchRecommendation, MaterialNationalMapping, AuditLog

def normalize_uom_str(uom: Optional[str]) -> str:
    """
    Normalizes UOM strings to canonical representations.
    """
    if not uom:
        return "EACH"
    u = uom.strip().upper()
    if u in ("EA", "EACH", "NOS", "NO", "NUMBER", "NUM", "PC", "PCS"):
        return "EACH"
    if u in ("M", "MTR", "METER", "METERS"):
        return "METER"
    if u in ("SET", "SETS"):
        return "SET"
    return u

def get_identity_key(material: Material) -> Optional[str]:
    """
    Constructs a deterministic identity key if and only if all identity-defining
    attributes for the material's equipment category are strictly known.
    Returns None if any required attribute is missing.
    """
    norm_attrs = material.normalized_attributes or {}
    cat = (norm_attrs.get("category") or material.category or "VALVE").upper()

    if cat == "VALVE":
        vtype = material.valve_type or norm_attrs.get("valve_type")
        size = material.size or norm_attrs.get("size")
        body = material.body_material or norm_attrs.get("body_material") or norm_attrs.get("material_grade")
        pc = material.pressure_class or norm_attrs.get("pressure_class") or norm_attrs.get("pressure_rating")
        conn = material.connection_type or norm_attrs.get("connection_type") or norm_attrs.get("facing_connection")
        trim = material.trim or norm_attrs.get("trim")
        seat = norm_attrs.get("seat_material")
        uom = normalize_uom_str(material.normalized_uom or norm_attrs.get("normalized_uom"))

        if not all([vtype, size, body, pc, conn]):
            return None
        if trim:
            return f"VALVE|{vtype}|{size}|{body}|{pc}|{conn}|{trim}|{uom}"
        elif seat:
            return f"VALVE|{vtype}|{size}|{body}|{pc}|{conn}|SEAT_{seat}|{uom}"
        else:
            return None

    elif cat == "STRAINER":
        stype = norm_attrs.get("type")
        size = norm_attrs.get("size") or material.size
        pc = norm_attrs.get("pressure_rating") or norm_attrs.get("pressure_class") or material.pressure_class
        mat = norm_attrs.get("material_grade") or norm_attrs.get("body_material") or material.body_material
        mesh = norm_attrs.get("mesh")
        uom = normalize_uom_str(material.normalized_uom)
        if not all([stype, size, pc, mat, mesh]):
            return None
        return f"STRAINER|{stype}|{size}|{mat}|{pc}|MESH_{mesh}|{uom}"

    elif cat == "PIPE":
        const = norm_attrs.get("construction")
        size = norm_attrs.get("size") or material.size
        sch = norm_attrs.get("schedule")
        mat = norm_attrs.get("material_grade") or material.body_material
        std = norm_attrs.get("standard_grade")
        uom = normalize_uom_str(material.normalized_uom or "METER")
        if not all([const, size, sch, mat]):
            return None
        return f"PIPE|{const}|{size}|{sch}|{mat}|{std or 'NA'}|{uom}"

    elif cat == "FLANGE":
        ftype = norm_attrs.get("flange_type")
        size = norm_attrs.get("size") or material.size
        pc = norm_attrs.get("pressure_rating") or norm_attrs.get("pressure_class") or material.pressure_class
        mat = norm_attrs.get("material_grade") or norm_attrs.get("body_material") or material.body_material
        conn = norm_attrs.get("facing_connection") or material.connection_type
        uom = normalize_uom_str(material.normalized_uom)
        if not all([ftype, size, pc, mat, conn]):
            return None
        return f"FLANGE|{ftype}|{size}|{mat}|{pc}|{conn}|{uom}"

    elif cat == "GASKET":
        gtype = norm_attrs.get("gasket_type")
        size = norm_attrs.get("size") or material.size
        pc = norm_attrs.get("pressure_rating") or norm_attrs.get("pressure_class") or material.pressure_class
        filler = norm_attrs.get("materials_filler")
        uom = normalize_uom_str(material.normalized_uom)
        if not all([gtype, size, pc, filler]):
            return None
        return f"GASKET|{gtype}|{size}|{pc}|{filler}|{uom}"

    elif cat == "PUMP":
        ptype = norm_attrs.get("pump_type")
        flow = norm_attrs.get("flow_rate")
        head = norm_attrs.get("head")
        mat = norm_attrs.get("casing_material") or material.body_material
        uom = normalize_uom_str(material.normalized_uom or "SET")
        if not all([ptype, flow, head, mat]):
            return None
        return f"PUMP|{ptype}|{flow}|{head}|{mat}|{uom}"

    elif cat == "TRANSMITTER":
        itype = norm_attrs.get("instrument_type")
        mrange = norm_attrs.get("measurement_range")
        sig = norm_attrs.get("signal")
        prot = norm_attrs.get("protocol")
        uom = normalize_uom_str(material.normalized_uom)
        if not all([itype, mrange, sig, prot]):
            return None
        return f"TRANSMITTER|{itype}|{mrange}|{sig}|{prot}|{uom}"

    elif cat == "FITTING":
        ftype = norm_attrs.get("fitting_type")
        size = norm_attrs.get("size") or material.size
        sch = norm_attrs.get("schedule")
        mat = norm_attrs.get("material_grade") or material.body_material
        uom = normalize_uom_str(material.normalized_uom)
        if not all([ftype, size, sch, mat]):
            return None
        return f"FITTING|{ftype}|{size}|{sch}|{mat}|{uom}"

    elif cat == "BEARING":
        btype = norm_attrs.get("bearing_type")
        bnum = norm_attrs.get("bearing_number")
        seal = norm_attrs.get("seal_shield")
        uom = normalize_uom_str(material.normalized_uom)
        if not all([btype, bnum, seal]):
            return None
        return f"BEARING|{btype}|{bnum}|{seal}|{uom}"

    elif cat == "BELT":
        btype = norm_attrs.get("belt_type")
        prof = norm_attrs.get("profile")
        length = norm_attrs.get("length")
        uom = normalize_uom_str(material.normalized_uom)
        if not all([btype, prof, length]):
            return None
        return f"BELT|{btype}|{prof}|{length}|{uom}"

    elif cat == "FASTENER":
        ftype = norm_attrs.get("fastener_type")
        size = norm_attrs.get("size") or material.size
        mat = norm_attrs.get("material_grade") or material.body_material
        uom = normalize_uom_str(material.normalized_uom)
        if not all([ftype, size, mat]):
            return None
        return f"FASTENER|{ftype}|{size}|{mat}|{uom}"

    # Generic fallback
    attrs = [
        material.category or "VALVE",
        material.valve_type,
        material.size,
        material.body_material,
        material.pressure_class,
        material.connection_type,
        material.trim,
        normalize_uom_str(material.normalized_uom)
    ]
    if any(attr is None for attr in attrs):
        return None

    return "|".join(str(a) for a in attrs)

def generate_canonical_desc(material: Material) -> str:
    """
    Generates a deterministic canonical description.
    """
    norm_attrs = material.normalized_attributes or {}
    cat = (norm_attrs.get("category") or material.category or "VALVE").upper()

    if cat == "VALVE" and (material.valve_type or norm_attrs.get("valve_type")):
        vtype = material.valve_type or norm_attrs.get("valve_type")
        size = material.size or norm_attrs.get("size")
        body = material.body_material or norm_attrs.get("body_material") or norm_attrs.get("material_grade")
        pc = material.pressure_class or norm_attrs.get("pressure_class") or norm_attrs.get("pressure_rating")
        conn = material.connection_type or norm_attrs.get("connection_type") or norm_attrs.get("facing_connection")
        trim = material.trim or norm_attrs.get("trim")
        seat = norm_attrs.get("seat_material")

        if trim:
            return f"{vtype} VALVE {size} {body} {pc} {conn} {trim} TRIM"
        elif seat:
            return f"{vtype} VALVE {size} {body} {pc} {conn} {seat} SEAT"

    if material.normalized_description:
        return material.normalized_description

    return material.source_description or "CANONICAL MATERIAL"

def harmonize_material(db: Session, material: Material) -> Dict[str, Any]:
    """
    Orchestrates the safe automatic harmonization of an individual Material.
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
        norm_attrs = material.normalized_attributes or {}
        col_cat = norm_attrs.get("category") or material.category or "VALVE"
        col_cat = col_cat.upper().strip()

        if col_cat == "VALVE":
            vtype = material.valve_type or norm_attrs.get("valve_type")
            size = material.size or norm_attrs.get("size")
            body = material.body_material or norm_attrs.get("body_material") or norm_attrs.get("material_grade")
            pc = material.pressure_class or norm_attrs.get("pressure_class") or norm_attrs.get("pressure_rating")
            conn = material.connection_type or norm_attrs.get("connection_type") or norm_attrs.get("facing_connection")
            trim = material.trim or norm_attrs.get("trim")
            uom = normalize_uom_str(material.normalized_uom or norm_attrs.get("normalized_uom"))
        else:
            vtype = None
            size = norm_attrs.get("size") or material.size
            body = material.body_material or norm_attrs.get("body_material") or norm_attrs.get("material_grade") or norm_attrs.get("casing_material")
            pc = material.pressure_class or norm_attrs.get("pressure_class") or norm_attrs.get("pressure_rating")
            conn = material.connection_type or norm_attrs.get("connection_type") or norm_attrs.get("facing_connection")
            trim = None
            uom = normalize_uom_str(material.normalized_uom or norm_attrs.get("normalized_uom"))

        nm = NationalMaterial(
            id=uuid.uuid4(),
            national_code=f"NM-{uuid.uuid4().hex[:8].upper()}",
            identity_key=identity_key,
            canonical_description=generate_canonical_desc(material),
            category=col_cat,
            normalized_attributes=material.normalized_attributes,
            valve_type=vtype,
            size=size,
            body_material=body,
            pressure_class=pc,
            connection_type=conn,
            trim=trim,
            normalized_uom=uom,
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
            after_state={"identity_key": identity_key, "national_code": nm.national_code, "category": col_cat},
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

def harmonize_same_families(db: Session) -> Dict[str, Any]:
    """
    Finds all connected components of materials connected by authoritative SAME
    recommendations across distinct CPSEs, and creates or reuses National Material
    records and active mappings idempotently.
    """
    recs = db.query(MatchRecommendation).filter_by(classification="SAME").all()
    adj = defaultdict(set)
    rec_map = {}
    for r in recs:
        adj[r.source_material_id].add(r.candidate_material_id)
        adj[r.candidate_material_id].add(r.source_material_id)
        rec_map[(r.source_material_id, r.candidate_material_id)] = r.id
        rec_map[(r.candidate_material_id, r.source_material_id)] = r.id

    visited = set()
    families = []
    for node in sorted(adj.keys()):
        if node not in visited:
            comp = []
            q = [node]
            visited.add(node)
            while q:
                curr = q.pop(0)
                comp.append(curr)
                for neighbor in sorted(adj[curr]):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append(neighbor)
            families.append(comp)

    families_processed = 0
    families_skipped = 0
    nm_created = 0
    nm_reused = 0
    mappings_created = 0
    mappings_reused = 0
    created_national_materials = []

    for comp in families:
        if len(comp) < 2:
            families_skipped += 1
            continue

        mats = [db.query(Material).filter_by(id=mid).first() for mid in comp]
        mats = [m for m in mats if m is not None]
        if len(mats) < 2:
            families_skipped += 1
            continue

        keys = [get_identity_key(m) for m in mats]
        if any(k is None for k in keys) or len(set(keys)) != 1:
            families_skipped += 1
            continue

        cpse_ids = set(m.cpse_id for m in mats)
        if len(cpse_ids) < 2:
            families_skipped += 1
            continue

        ident_key = keys[0]
        sample_mat = mats[0]
        families_processed += 1

        # Check if any material in this component already has an ACTIVE mapping
        existing_nm = None
        for m in mats:
            act_map = db.query(MaterialNationalMapping).filter_by(material_id=m.id, status="ACTIVE").first()
            if act_map:
                existing_nm = db.query(NationalMaterial).filter_by(id=act_map.national_material_id).first()
                if existing_nm:
                    break

        if not existing_nm:
            existing_nm = db.query(NationalMaterial).filter_by(identity_key=ident_key).first()

        if existing_nm:
            nm = existing_nm
            nm_reused += 1
        else:
            norm_attrs = sample_mat.normalized_attributes or {}
            col_cat = norm_attrs.get("category") or sample_mat.category or "VALVE"
            col_cat = col_cat.upper().strip()

            if col_cat == "VALVE":
                vtype = sample_mat.valve_type or norm_attrs.get("valve_type")
                size = sample_mat.size or norm_attrs.get("size")
                body = sample_mat.body_material or norm_attrs.get("body_material") or norm_attrs.get("material_grade")
                pc = sample_mat.pressure_class or norm_attrs.get("pressure_class") or norm_attrs.get("pressure_rating")
                conn = sample_mat.connection_type or norm_attrs.get("connection_type") or norm_attrs.get("facing_connection")
                trim = sample_mat.trim or norm_attrs.get("trim")
                uom = normalize_uom_str(sample_mat.normalized_uom or norm_attrs.get("normalized_uom"))
            else:
                vtype = None
                size = norm_attrs.get("size") or sample_mat.size
                body = sample_mat.body_material or norm_attrs.get("body_material") or norm_attrs.get("material_grade") or norm_attrs.get("casing_material")
                pc = sample_mat.pressure_class or norm_attrs.get("pressure_class") or norm_attrs.get("pressure_rating")
                conn = sample_mat.connection_type or norm_attrs.get("connection_type") or norm_attrs.get("facing_connection")
                trim = None
                uom = normalize_uom_str(sample_mat.normalized_uom or norm_attrs.get("normalized_uom"))

            nm = NationalMaterial(
                id=uuid.uuid4(),
                national_code=f"NM-{uuid.uuid4().hex[:8].upper()}",
                identity_key=ident_key,
                canonical_description=generate_canonical_desc(sample_mat),
                category=col_cat,
                normalized_attributes=sample_mat.normalized_attributes,
                valve_type=vtype,
                size=size,
                body_material=body,
                pressure_class=pc,
                connection_type=conn,
                trim=trim,
                normalized_uom=uom,
                status="ACTIVE"
            )
            db.add(nm)
            db.flush()
            nm_created += 1
            created_national_materials.append(nm.national_code)

            audit_nm = AuditLog(
                id=uuid.uuid4(),
                actor="system_harmonization",
                action="CREATE_NATIONAL_MATERIAL",
                entity_type="NATIONAL_MATERIAL",
                entity_id=str(nm.id),
                before_state=None,
                after_state={"identity_key": ident_key, "national_code": nm.national_code, "category": col_cat},
                reason=f"Auto-created family for {len(comp)} materials"
            )
            db.add(audit_nm)

        for m in mats:
            act_map = db.query(MaterialNationalMapping).filter_by(material_id=m.id, status="ACTIVE").first()
            if act_map:
                mappings_reused += 1
            else:
                rid = None
                for other_m in mats:
                    if (m.id, other_m.id) in rec_map:
                        rid = rec_map[(m.id, other_m.id)]
                        break

                mapping = MaterialNationalMapping(
                    id=uuid.uuid4(),
                    material_id=m.id,
                    national_material_id=nm.id,
                    basis="AUTO_SAME",
                    status="ACTIVE",
                    recommendation_id=rid
                )
                db.add(mapping)
                db.flush()
                mappings_created += 1

                audit_map = AuditLog(
                    id=uuid.uuid4(),
                    actor="system_harmonization",
                    action="CREATE_MAPPING",
                    entity_type="MATERIAL_NATIONAL_MAPPING",
                    entity_id=str(mapping.id),
                    before_state=None,
                    after_state={"material_id": str(m.id), "national_material_id": str(nm.id), "basis": mapping.basis},
                    reason=f"Auto-mapped based on SAME family {nm.national_code}"
                )
                db.add(audit_map)

    return {
        "status": "success",
        "families_processed": families_processed,
        "families_skipped": families_skipped,
        "national_materials_created": nm_created,
        "national_materials_reused": nm_reused,
        "mappings_created": mappings_created,
        "mappings_reused": mappings_reused,
        "created_national_codes": created_national_materials
    }
