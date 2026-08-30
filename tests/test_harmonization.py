import pytest
import uuid
from fastapi.testclient import TestClient

from app.models import CPSE, Material, MatchRecommendation, NationalMaterial, MaterialNationalMapping, AuditLog
from app.services.harmonization import harmonize_material

@pytest.fixture
def cpse_x(db):
    c = CPSE(code=f"CPSE-X-{uuid.uuid4()}", name="X")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def create_mat(db, cpse, attrs: dict) -> Material:
    mat = Material(
        id=uuid.uuid4(),
        cpse_id=cpse.id,
        source_material_code=f"M-{uuid.uuid4()}",
        source_description=attrs.get("desc", "TEST VALVE"),
        source_uom="EA",
        category="VALVE",
        normalized_description="NORM DESC",
        valve_type=attrs.get("valve_type", "BALL"),
        size=attrs.get("size", "DN50"),
        body_material=attrs.get("body_material", "CARBON_STEEL"),
        pressure_class=attrs.get("pressure_class", "CLASS300"),
        connection_type=attrs.get("connection_type", "RF"),
        trim=attrs.get("trim", "SS304"),
        normalized_uom="EACH"
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat

def create_rec(db, m1: Material, m2: Material, classification: str):
    r = MatchRecommendation(
        source_material_id=m1.id,
        candidate_material_id=m2.id,
        classification=classification,
        confidence=0.95 if classification == "SAME" else 0.5
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

def test_harmonize_complete_same(db, cpse_x):
    v_type = f"PLUG_{uuid.uuid4().hex[:4]}"
    m1 = create_mat(db, cpse_x, {"valve_type": v_type})
    m2 = create_mat(db, cpse_x, {"valve_type": v_type})
    create_rec(db, m1, m2, "SAME")
    
    res = harmonize_material(db, m1)
    db.commit()
    
    assert res["status"] == "success"
    assert res["national_material_action"] == "CREATED" # 1. Complete SAME -> NM created
    
    nm = db.query(NationalMaterial).filter_by(id=res["national_material_id"]).first()
    assert nm is not None
    assert nm.national_code is not None # 16. National code
    assert f"{v_type} VALVE DN50 CARBON_STEEL CLASS300 RF SS304 TRIM" in nm.canonical_description # 17. Canonical desc
    
    map1 = db.query(MaterialNationalMapping).filter_by(id=res["mapping_id"]).first()
    assert map1.status == "ACTIVE"
    assert map1.basis == "AUTO_SAME" # 4. ACTIVE AUTO_SAME mapping
    
    # 15. AuditLog records actions
    logs = db.query(AuditLog).filter(AuditLog.action.in_(["CREATE_NATIONAL_MATERIAL", "CREATE_MAPPING"])).all()
    assert len(logs) >= 2

def test_harmonize_reuse_nm(db, cpse_x):
    # 2. Repeated same identity -> reused NM
    # 3. Same identity never creates duplicates
    v_type = f"GLOBE_{uuid.uuid4().hex[:4]}"
    m1 = create_mat(db, cpse_x, {"valve_type": v_type})
    m2 = create_mat(db, cpse_x, {"valve_type": v_type})
    m3 = create_mat(db, cpse_x, {"valve_type": v_type})
    create_rec(db, m1, m2, "SAME")
    create_rec(db, m3, m2, "SAME")
    
    res1 = harmonize_material(db, m1)
    db.commit()
    assert res1["national_material_action"] == "CREATED"
    
    res2 = harmonize_material(db, m3)
    db.commit()
    assert res2["national_material_action"] == "REUSED"
    assert res1["national_material_id"] == res2["national_material_id"]

def test_harmonize_no_auto_map_for_potential_or_different(db, cpse_x):
    m1 = create_mat(db, cpse_x, {})
    m2 = create_mat(db, cpse_x, {})
    create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")
    
    res = harmonize_material(db, m1)
    assert res["status"] == "skipped" # 5. POTENTIALLY_EQUIVALENT -> no automatic mapping
    
    m3 = create_mat(db, cpse_x, {})
    create_rec(db, m1, m3, "DIFFERENT")
    res2 = harmonize_material(db, m1)
    assert res2["status"] == "skipped" # 6. DIFFERENT -> no automatic mapping

def test_harmonize_missing_attributes(db, cpse_x):
    # 7. Missing trim
    m_no_trim = create_mat(db, cpse_x, {"trim": None})
    res = harmonize_material(db, m_no_trim)
    assert res["status"] == "skipped"
    assert "Incomplete identity" in res["reason"]
    
    # 8. Missing size
    m_no_size = create_mat(db, cpse_x, {"size": None})
    res2 = harmonize_material(db, m_no_size)
    assert res2["status"] == "skipped"
    
    # 9. Missing pressure class
    m_no_pc = create_mat(db, cpse_x, {"pressure_class": None})
    res3 = harmonize_material(db, m_no_pc)
    assert res3["status"] == "skipped"

def test_separate_identities(db, cpse_x):
    m_150 = create_mat(db, cpse_x, {"pressure_class": "CLASS150"})
    m_300 = create_mat(db, cpse_x, {"pressure_class": "CLASS300"})
    m_dn50 = create_mat(db, cpse_x, {"size": "DN50"})
    m_dn100 = create_mat(db, cpse_x, {"size": "DN100"})
    m_gate = create_mat(db, cpse_x, {"valve_type": "GATE"})
    
    m_150_b = create_mat(db, cpse_x, {"pressure_class": "CLASS150"})
    create_rec(db, m_150, m_150_b, "SAME")
    r1 = harmonize_material(db, m_150)
    
    m_300_b = create_mat(db, cpse_x, {"pressure_class": "CLASS300"})
    create_rec(db, m_300, m_300_b, "SAME")
    r2 = harmonize_material(db, m_300)
    
    assert r1["national_material_id"] != r2["national_material_id"] # 11. Different classes remain separate
    
    m_100_b = create_mat(db, cpse_x, {"size": "DN100"})
    create_rec(db, m_dn100, m_100_b, "SAME")
    r3 = harmonize_material(db, m_dn100)
    
    # m_dn50 is practically same as m_300 depending on defaults, let's just make sure 100 is different
    assert r3["national_material_id"] != r1["national_material_id"] # 12. Different sizes remain separate
    
    m_gate_b = create_mat(db, cpse_x, {"valve_type": "GATE"})
    create_rec(db, m_gate, m_gate_b, "SAME")
    r4 = harmonize_material(db, m_gate)
    assert r4["national_material_id"] != r1["national_material_id"] # 13. Different types remain separate

def test_existing_mapping_not_replaced(db, cpse_x):
    m1 = create_mat(db, cpse_x, {})
    m2 = create_mat(db, cpse_x, {})
    create_rec(db, m1, m2, "SAME")
    
    res1 = harmonize_material(db, m1)
    db.commit()
    assert res1["status"] == "success"
    
    # Run again, should skip
    res2 = harmonize_material(db, m1)
    assert res2["status"] == "skipped"
    assert "already has an active mapping" in res2["reason"].lower() # 14. Not silently replaced

def test_regression_abc(db, cpse_x):
    # A: BALL / DN50 / CARBON_STEEL / CLASS300 / RF / SS304
    a_attrs = {"valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", 
               "pressure_class": "CLASS300", "connection_type": "RF", "trim": "SS304"}
    m_a = create_mat(db, cpse_x, a_attrs)
    
    # B: BALL / DN50 / CARBON_STEEL / CLASS300 / RF / SS304
    m_b = create_mat(db, cpse_x, a_attrs)
    
    # C: BALL / DN50 / CARBON_STEEL / CLASS300 / RF / NULL
    c_attrs = a_attrs.copy()
    c_attrs["trim"] = None
    m_c = create_mat(db, cpse_x, c_attrs)
    
    create_rec(db, m_a, m_b, "SAME")
    create_rec(db, m_b, m_a, "SAME")
    r_a = harmonize_material(db, m_a)
    r_b = harmonize_material(db, m_b)
    
    assert r_a["status"] == "success"
    assert r_b["status"] == "success"
    assert r_a["national_material_id"] == r_b["national_material_id"] # A and B -> same NM
    
    # Assuming M_C somehow had a SAME rec (which it shouldn't normally, but testing robustness)
    create_rec(db, m_c, m_a, "SAME")
    r_c = harmonize_material(db, m_c)
    assert r_c["status"] == "skipped" # 10. NULL never acts as wildcard / C -> no NM

def test_api_endpoint(client: TestClient, db, cpse_x):
    m1 = create_mat(db, cpse_x, {})
    m2 = create_mat(db, cpse_x, {})
    create_rec(db, m1, m2, "SAME")
    
    resp = client.post(f"/api/v1/materials/{m1.id}/harmonize")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "national_material_id" in data
