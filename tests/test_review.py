from app.core.config import settings
import pytest
import uuid
from fastapi.testclient import TestClient

from app.models import CPSE, Material, MatchRecommendation, NationalMaterial, MaterialNationalMapping, AuditLog

@pytest.fixture
def test_cpse(db):
    c = CPSE(code=f"CPSE-REV-{uuid.uuid4()}", name="REV")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def create_mat(db, cpse, complete=True) -> Material:
    mat = Material(
        id=uuid.uuid4(),
        cpse_id=cpse.id,
        source_material_code=f"M-{uuid.uuid4()}",
        source_description="DESC",
        source_uom="EA",
        category="VALVE",
        normalized_description="NORM DESC",
        valve_type="BALL",
        size="DN50",
        body_material="CARBON_STEEL",
        pressure_class="CLASS300",
        connection_type="RF",
        trim="SS304" if complete else None,
        normalized_uom="EACH"
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat

def create_rec(db, m1, m2, classification):
    rec = MatchRecommendation(
        source_material_id=m1.id,
        candidate_material_id=m2.id,
        classification=classification,
        confidence=0.8 if classification == "SAME" else 0.5,
        evidence={},
        explanation="TEST"
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

def test_unauthorized_rejected(client: TestClient):
    resp = client.get("/api/v1/reviews/queue")
    assert resp.status_code == 401 # 16. unauthorized rejected

def test_queue_appears(client: TestClient, db, test_cpse):
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    rec1 = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")
    
    m3 = create_mat(db, test_cpse, complete=False)
    m4 = create_mat(db, test_cpse)
    rec2 = create_rec(db, m3, m4, "SAME") # Incomplete identity SAME
    
    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.get("/api/v1/reviews/queue", headers=headers)
    assert resp.status_code == 200
    q = resp.json()["queue"]
    
    rec_ids = [r["recommendation_id"] for r in q]
    assert str(rec1.id) in rec_ids # 1. POTENTIALLY_EQUIVALENT appears
    assert str(rec2.id) in rec_ids # 2. Incomplete identity appears

def test_accept_complete(client: TestClient, db, test_cpse):
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")
    
    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT"
    }, headers=headers)
    assert resp.status_code == 200
    
    mapping = db.query(MaterialNationalMapping).filter_by(material_id=m1.id).first()
    assert mapping.basis == "HUMAN_CONFIRMED_SAME" # 3. ACCEPT creates HUMAN_CONFIRMED_SAME mapping
    
    log = db.query(AuditLog).filter_by(entity_id=str(rec.id)).first()
    assert log.action == "ACCEPT" # 11. human action creates AuditLog
    
    nm = db.query(NationalMaterial).filter_by(id=mapping.national_material_id).first()
    assert nm.valve_type == "BALL"
    assert m1.valve_type == "BALL" # 17. source Material data remains unchanged

def test_reject_and_mark_different(client: TestClient, db, test_cpse):
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    rec = create_rec(db, m1, m2, "DIFFERENT")
    
    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "REJECT"
    }, headers=headers)
    assert resp.status_code == 400 # 7. REJECT requires reason
    
    resp2 = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "REJECT", "reason": "No way"
    }, headers=headers)
    assert resp2.status_code == 200
    
    mapping = db.query(MaterialNationalMapping).filter_by(material_id=m1.id).first()
    assert mapping is None # 4. REJECT creates no mapping
    
    log = db.query(AuditLog).filter_by(entity_id=str(rec.id)).first()
    assert log.reason == "No way" # 10. reason is stored in AuditLog
    
    rec2 = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")
    resp3 = client.post(f"/api/v1/reviews/{rec2.id}/action", json={
        "action": "MARK_DIFFERENT"
    }, headers=headers)
    assert resp3.status_code == 400 # 8. MARK_DIFFERENT requires reason
    
    resp4 = client.post(f"/api/v1/reviews/{rec2.id}/action", json={
        "action": "MARK_DIFFERENT", "reason": "Diff class"
    }, headers=headers)
    assert resp4.status_code == 200
    assert db.query(MaterialNationalMapping).filter_by(material_id=m1.id).first() is None # 5. MARK_DIFFERENT creates no mapping
    
    # 14. historical recommendations remain unchanged
    db.refresh(rec)
    assert rec.classification == "DIFFERENT"

def test_override(client: TestClient, db, test_cpse):
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")
    
    # Create NM manually
    nm = NationalMaterial(
        id=uuid.uuid4(), national_code=f"NM-OVR-{uuid.uuid4().hex[:4]}", identity_key=f"OVR-{uuid.uuid4()}",
        category="VALVE", valve_type="BALL", size="DN50", body_material="CS",
        pressure_class="CL", connection_type="RF", trim="SS", normalized_uom="EA", canonical_description="desc"
    )
    db.add(nm)
    db.commit()
    
    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "OVERRIDE"
    }, headers=headers)
    assert resp.status_code == 400 # 9. OVERRIDE requires reason (and nm id)
    
    resp2 = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "OVERRIDE", "reason": "Force mapping", "national_material_id": str(nm.id)
    }, headers=headers)
    assert resp2.status_code == 200
    
    mapping = db.query(MaterialNationalMapping).filter_by(material_id=m1.id).first()
    assert mapping.basis == "HUMAN_OVERRIDE" # 6. OVERRIDE creates HUMAN_OVERRIDE mapping
    assert mapping.national_material_id == nm.id

def test_accept_incomplete_identity_rejected(client: TestClient, db, test_cpse):
    m1 = create_mat(db, test_cpse, complete=False)
    m2 = create_mat(db, test_cpse, complete=False)
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")
    
    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT"
    }, headers=headers)
    
    assert resp.status_code == 400
    assert "incomplete identity" in resp.json()["detail"].lower()
    # 12. Cannot create invalid NM
    # 18. Missing identity attributes never silently inferred

def test_one_active_mapping_enforced(client: TestClient, db, test_cpse):
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    rec1 = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")
    rec2 = create_rec(db, m1, m2, "DIFFERENT")
    
    headers = {"X-Reviewer-Token": settings.reviewer_token}
    client.post(f"/api/v1/reviews/{rec1.id}/action", json={"action": "ACCEPT"}, headers=headers)
    
    resp2 = client.post(f"/api/v1/reviews/{rec2.id}/action", json={"action": "ACCEPT"}, headers=headers)
    assert resp2.status_code == 400
    assert "already has an active mapping" in resp2.json()["detail"].lower() # 13. one ACTIVE mapping rule remains enforced
