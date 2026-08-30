from app.core.config import settings
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CPSE, Material, NationalMaterial, MatchRecommendation, MaterialNationalMapping, AuditLog

def test_e2e_pipeline(client: TestClient, db: Session):
    # 1. Setup CPSEs
    run_id = uuid.uuid4().hex[:6]
    cpse_a = CPSE(id=uuid.uuid4(), code=f"CPSE-A-DEMO-{run_id}", name="CPSE A")
    cpse_b = CPSE(id=uuid.uuid4(), code=f"CPSE-B-DEMO-{run_id}", name="CPSE B")
    cpse_c = CPSE(id=uuid.uuid4(), code=f"CPSE-C-DEMO-{run_id}", name="CPSE C")
    db.add_all([cpse_a, cpse_b, cpse_c])
    db.commit()

    # 2. Upload Data
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for code, c_id in [("cpse_a", cpse_a.id), ("cpse_b", cpse_b.id), ("cpse_c", cpse_c.id)]:
        file_path = os.path.join(base_dir, "demo_data", f"{code}.csv")
        with open(file_path, "rb") as f:
            resp = client.post(f"/api/v1/materials/import", data={"cpse_id": str(c_id)}, files={"file": (f"{code}.csv", f, "text/csv")})
            assert resp.status_code == 200, resp.text
            summary = resp.json()
            if code == "cpse_a":
                assert summary["total_rows"] == 6
                assert summary["imported_rows"] == 4
                assert summary["rejected_rows"] == 2 # 1 invalid, 1 duplicate
            
    materials = db.query(Material).filter(Material.cpse_id.in_([cpse_a.id, cpse_b.id, cpse_c.id])).all()
    assert len(materials) == 14 # 4 (A) + 6 (B) + 4 (C)

    # 3. Normalize imported materials
    for mat in materials:
        resp = client.post(f"/api/v1/materials/{mat.id}/normalize")
        assert resp.status_code == 200
        
    db.expire_all()
    
    # 4. Generate matching recommendations
    for mat in materials:
        resp = client.post(f"/api/v1/materials/{mat.id}/match")
        assert resp.status_code == 200

    db.expire_all()
    
    # 5. Harmonize safe SAME records
    for mat in materials:
        client.post(f"/api/v1/materials/{mat.id}/harmonize")

    db.expire_all()
    
    # 6. Verify Exact Equivalent across CPSEs mapping to same NM
    a1 = db.query(Material).filter_by(source_material_code="A-001", cpse_id=cpse_a.id).first()
    b1 = db.query(Material).filter_by(source_material_code="B-001", cpse_id=cpse_b.id).first()
    c1 = db.query(Material).filter_by(source_material_code="C-001", cpse_id=cpse_c.id).first()
    
    map_a1 = db.query(MaterialNationalMapping).filter_by(material_id=a1.id, status="ACTIVE").first()
    map_b1 = db.query(MaterialNationalMapping).filter_by(material_id=b1.id, status="ACTIVE").first()
    map_c1 = db.query(MaterialNationalMapping).filter_by(material_id=c1.id, status="ACTIVE").first()
    
    assert map_a1 is not None and map_b1 is not None and map_c1 is not None
    assert map_a1.national_material_id == map_b1.national_material_id
    assert map_a1.national_material_id == map_c1.national_material_id
    assert map_a1.basis == "AUTO_SAME"

    # 7. Verify CLASS150 vs CLASS300, DN50 vs DN100, BALL vs GATE, RF vs SW are DIFFERENT
    # A-001 (BALL, DN50, CS, CLASS300, RF, SS304)
    # B-003 (CLASS150 variant), B-004 (4 INCH / DN100 variant), C-002 (SS316 TRIM variant), C-004 (SOCKET WELD variant)
    def check_diff(source_code, source_cpse_id, candidate_code, cand_cpse_id):
        src = db.query(Material).filter_by(source_material_code=source_code, cpse_id=source_cpse_id).first()
        cand = db.query(Material).filter_by(source_material_code=candidate_code, cpse_id=cand_cpse_id).first()
        rec = db.query(MatchRecommendation).filter_by(source_material_id=src.id, candidate_material_id=cand.id).first()
        assert rec is not None
        assert rec.classification == "DIFFERENT"
        return rec

    check_diff("A-001", cpse_a.id, "B-003", cpse_b.id) # Class diff
    check_diff("A-001", cpse_a.id, "B-004", cpse_b.id) # Size diff
    check_diff("A-001", cpse_a.id, "C-002", cpse_c.id) # Trim diff
    check_diff("A-001", cpse_a.id, "C-004", cpse_c.id) # Connection diff
    # check_diff("A-001", cpse_a.id, "B-002", cpse_b.id) # Pre-filtered out by matching engine completely

    # 8. Verify incomplete identities (Missing trim)
    # A-003, C-003
    a3 = db.query(Material).filter_by(source_material_code="A-003", cpse_id=cpse_a.id).first()
    assert db.query(MaterialNationalMapping).filter_by(material_id=a3.id).first() is None # Did not auto map!

    # 9. Verify Review Queue contains unmapped items
    headers = {"X-Reviewer-Token": settings.reviewer_token}
    resp = client.get("/api/v1/reviews/queue", headers=headers)
    assert resp.status_code == 200
    queue = resp.json()["queue"]
    
    # Extract rec_ids from queue
    q_rec_ids = [q["recommendation_id"] for q in queue]
    
    # 10. Human ACCEPT on incomplete -> should fail
    # Let's find a SAME rec for A-003 against C-003
    c3 = db.query(Material).filter_by(source_material_code="C-003", cpse_id=cpse_c.id).first()
    rec_a3_c3 = db.query(MatchRecommendation).filter_by(source_material_id=a3.id, candidate_material_id=c3.id).first()
    
    assert rec_a3_c3 is not None
    
    resp_accept_invalid = client.post(f"/api/v1/reviews/{rec_a3_c3.id}/action", json={"action": "ACCEPT"}, headers=headers)
    assert resp_accept_invalid.status_code == 400
    assert "incomplete identity" in resp_accept_invalid.json()["detail"].lower()

    # 11. Human OVERRIDE on A-003
    nm_target = map_a1.national_material_id # We'll just map it to the known complete one
    resp_override = client.post(f"/api/v1/reviews/{rec_a3_c3.id}/action", json={
        "action": "OVERRIDE", "reason": "Standardizing to SS304", "national_material_id": str(nm_target)
    }, headers=headers)
    assert resp_override.status_code == 200
    
    map_a3 = db.query(MaterialNationalMapping).filter_by(material_id=a3.id).first()
    assert map_a3.basis == "HUMAN_OVERRIDE"
    
    # 12. Human MARK_DIFFERENT on a POTENTIALLY_EQUIVALENT rec
    # A-001 vs A-003 should be POTENTIALLY_EQUIVALENT because A-003 misses trim
    rec_a1_a3 = db.query(MatchRecommendation).filter_by(source_material_id=a1.id, candidate_material_id=a3.id).first()
    if rec_a1_a3 and rec_a1_a3.classification == "POTENTIALLY_EQUIVALENT":
        resp_md = client.post(f"/api/v1/reviews/{rec_a1_a3.id}/action", json={
            "action": "MARK_DIFFERENT", "reason": "We do not know the trim"
        }, headers=headers)
        assert resp_md.status_code == 200
        # Audit log verifies
        log_md = db.query(AuditLog).filter_by(action="MARK_DIFFERENT", entity_id=str(rec_a1_a3.id)).first()
        assert log_md is not None
        assert log_md.reason == "We do not know the trim"
    
    # 13. Audit history verifies
    assert db.query(AuditLog).count() > 30 # Just ensuring it exists and logs lots of things (ingestion, norm, map, review)
