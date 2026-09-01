from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
import uuid

from app.api.deps import get_current_reviewer
from app.core.config import Settings, settings
from app.models import CPSE, Material, MatchRecommendation, NationalMaterial, MaterialNationalMapping, AuditLog

def test_get_current_reviewer_accepts_configured_tokens(monkeypatch):
    monkeypatch.setattr(settings, "reviewer_tokens_raw", "token_a, token_b , ,token_c")
    monkeypatch.setattr(settings, "reviewer_token", None)

    assert settings.reviewer_tokens == ["token_a", "token_b", "token_c"]
    assert get_current_reviewer("token_a") == "human_reviewer"
    assert get_current_reviewer("token_b") == "human_reviewer"

    with pytest.raises(HTTPException) as exc:
        get_current_reviewer("invalid-token")
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        get_current_reviewer("")
    assert exc.value.status_code == 401


def test_get_current_reviewer_supports_legacy_single_token(monkeypatch):
    monkeypatch.setattr(settings, "reviewer_tokens_raw", None)
    monkeypatch.setattr(settings, "reviewer_token", "legacy-token")

    assert settings.reviewer_tokens == ["legacy-token"]
    assert get_current_reviewer("legacy-token") == "human_reviewer"


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

def test_accept_incomplete_non_conflicting_allowed(client: TestClient, db, test_cpse):
    # CASE 1: Non-conflicting missing attributes on both source and candidate (e.g. trim=None)
    m1 = create_mat(db, test_cpse, complete=False)
    m2 = create_mat(db, test_cpse, complete=False)
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT",
        "reason": "Human verified equivalent despite unspecified trim"
    }, headers=headers)

    assert resp.status_code == 200
    mapping = db.query(MaterialNationalMapping).filter_by(material_id=m1.id).first()
    assert mapping is not None
    assert mapping.basis == "HUMAN_CONFIRMED_SAME"
    assert mapping.status == "ACTIVE"

    log = db.query(AuditLog).filter_by(entity_id=str(rec.id)).first()
    assert log.action == "ACCEPT"
    assert "unspecified trim" in log.reason

    nm = db.query(NationalMaterial).filter_by(id=mapping.national_material_id).first()
    assert nm is not None
    assert nm.trim == "UNKNOWN"
    assert nm.identity_key == "VALVE|BALL|DN50|CARBON_STEEL|CLASS300|RF|UNKNOWN|EACH"

def test_accept_asymmetric_missing_rejected(client: TestClient, db, test_cpse):
    # Asymmetric missing attribute (SS304 vs UNKNOWN)
    m1 = create_mat(db, test_cpse, complete=True)  # trim=SS304
    m2 = create_mat(db, test_cpse, complete=False) # trim=None
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT"
    }, headers=headers)

    assert resp.status_code == 400
    assert "asymmetric missing attributes" in resp.json()["detail"].lower()

def test_accept_conflict_size_blocked(client: TestClient, db, test_cpse):
    # CASE 2: DN50 vs DN80
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    m2.size = "DN80"
    db.commit()
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT"
    }, headers=headers)

    assert resp.status_code == 400
    assert "conflicting attributes" in resp.json()["detail"].lower()
    assert "size" in resp.json()["detail"].lower()

def test_accept_conflict_pressure_class_blocked(client: TestClient, db, test_cpse):
    # CASE 3: CLASS300 vs CLASS150
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    m2.pressure_class = "CLASS150"
    db.commit()
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT"
    }, headers=headers)

    assert resp.status_code == 400
    assert "conflicting attributes" in resp.json()["detail"].lower()
    assert "pressure_class" in resp.json()["detail"].lower()

def test_accept_conflict_trim_blocked(client: TestClient, db, test_cpse):
    # CASE 4: SS304 vs SS316
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    m2.trim = "SS316"
    db.commit()
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT"
    }, headers=headers)

    assert resp.status_code == 400
    assert "conflicting attributes" in resp.json()["detail"].lower()
    assert "trim" in resp.json()["detail"].lower()

def test_accept_conflict_valve_type_blocked(client: TestClient, db, test_cpse):
    # CASE 5: BALL vs GATE
    m1 = create_mat(db, test_cpse)
    m2 = create_mat(db, test_cpse)
    m2.valve_type = "GATE"
    db.commit()
    rec = create_rec(db, m1, m2, "POTENTIALLY_EQUIVALENT")

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{rec.id}/action", json={
        "action": "ACCEPT"
    }, headers=headers)

    assert resp.status_code == 400
    assert "conflicting attributes" in resp.json()["detail"].lower()
    assert "valve_type" in resp.json()["detail"].lower()

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

def test_mapped_semantics_exact_recommendation_only(client: TestClient, db, test_cpse):
    # CASE 1: Source has active mapping through recommendation R1.
    # R1 = SAME, R2 = DIFFERENT, R3 = POTENTIALLY_EQUIVALENT
    # Expected: R1 -> MAPPED, R2 -> DIFFERENT, R3 -> NEEDS REVIEW
    m_src = create_mat(db, test_cpse)
    m_cand1 = create_mat(db, test_cpse)
    m_cand2 = create_mat(db, test_cpse)
    m_cand3 = create_mat(db, test_cpse)

    r1 = create_rec(db, m_src, m_cand1, "SAME")
    r2 = create_rec(db, m_src, m_cand2, "DIFFERENT")
    r3 = create_rec(db, m_src, m_cand3, "POTENTIALLY_EQUIVALENT")

    # Create NM and mapping strictly linked to r1
    nm = NationalMaterial(
        id=uuid.uuid4(),
        national_code=f"NM-TEST-{uuid.uuid4().hex[:6]}",
        identity_key=f"TEST-KEY-{uuid.uuid4()}",
        canonical_description="CANONICAL DESC",
        category="VALVE",
        valve_type="BALL",
        size="DN50",
        body_material="CARBON_STEEL",
        pressure_class="CLASS300",
        connection_type="RF",
        trim="SS304",
        normalized_uom="EACH",
        status="ACTIVE"
    )
    db.add(nm)
    db.flush()

    mapping = MaterialNationalMapping(
        id=uuid.uuid4(),
        material_id=m_src.id,
        national_material_id=nm.id,
        basis="AUTO_SAME",
        status="ACTIVE",
        recommendation_id=r1.id
    )
    db.add(mapping)
    db.commit()

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.get("/api/v1/reviews/queue", headers=headers)
    assert resp.status_code == 200
    q = resp.json()["queue"]
    q_map = {item["recommendation_id"]: item for item in q}

    assert q_map[str(r1.id)]["mapping_status"] == "MAPPED"
    assert q_map[str(r1.id)]["national_material_code"] == nm.national_code
    assert q_map[str(r1.id)]["mapping_basis"] == "AUTO_SAME"

    assert q_map[str(r2.id)]["mapping_status"] == "DIFFERENT"
    assert q_map[str(r2.id)]["national_material_code"] is None

    assert q_map[str(r3.id)]["mapping_status"] == "NEEDS REVIEW"
    assert q_map[str(r3.id)]["national_material_code"] is None

def test_mapped_semantics_human_accept_preserves_other_recs(client: TestClient, db, test_cpse):
    # CASE 3 & 4: Human ACCEPT on R1 only marks R1 as MAPPED; R2 remains DIFFERENT
    m_src = create_mat(db, test_cpse)
    m_cand1 = create_mat(db, test_cpse)
    m_cand2 = create_mat(db, test_cpse)

    r1 = create_rec(db, m_src, m_cand1, "POTENTIALLY_EQUIVALENT")
    r2 = create_rec(db, m_src, m_cand2, "DIFFERENT")

    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.post(f"/api/v1/reviews/{r1.id}/action", json={
        "action": "ACCEPT",
        "reason": "Verified matching specifications"
    }, headers=headers)
    assert resp.status_code == 200

    q_resp = client.get("/api/v1/reviews/queue", headers=headers)
    assert q_resp.status_code == 200
    q = q_resp.json()["queue"]
    q_map = {item["recommendation_id"]: item for item in q}

    # R1 is MAPPED
    assert q_map[str(r1.id)]["mapping_status"] == "MAPPED"
    assert q_map[str(r1.id)]["mapping_basis"] == "HUMAN_CONFIRMED_SAME"

    # R2 remains DIFFERENT
    assert q_map[str(r2.id)]["mapping_status"] == "DIFFERENT"
    assert q_map[str(r2.id)]["national_material_code"] is None


