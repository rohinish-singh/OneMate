import pytest
import uuid
from fastapi.testclient import TestClient

from app.models import CPSE, Material, AuditLog
from app.services.normalization import normalize_material_record

@pytest.fixture
def test_cpse(db):
    cpse = CPSE(code=f"CPSE-NORM-{uuid.uuid4()}", name="Test NORM CPSE")
    db.add(cpse)
    db.commit()
    db.refresh(cpse)
    return cpse

def create_raw_material(db, cpse, desc: str, specs: str = None, uom: str = "EA") -> Material:
    mat = Material(
        id=uuid.uuid4(),
        cpse_id=cpse.id,
        source_material_code=f"M-{uuid.uuid4()}",
        source_description=desc,
        source_uom=uom,
        source_specifications=specs,
        category="VALVE",
        raw_source_data={"original": desc}
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat

def test_norm_valve_types(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "BALL VALVE DN50")
    normalize_material_record(db, mat1)
    assert mat1.valve_type == "BALL"

    mat2 = create_raw_material(db, test_cpse, "GATE VALVE CS")
    normalize_material_record(db, mat2)
    assert mat2.valve_type == "GATE"

def test_norm_body_materials(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "VALVE CS CLASS 150")
    normalize_material_record(db, mat1)
    assert mat1.body_material == "CARBON_STEEL"

    mat2 = create_raw_material(db, test_cpse, "VALVE SS CLASS 300")
    normalize_material_record(db, mat2)
    assert mat2.body_material == "STAINLESS_STEEL"

def test_norm_pressure_classes(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "VALVE CLASS150")
    normalize_material_record(db, mat1)
    assert mat1.pressure_class == "CLASS150"

    mat2 = create_raw_material(db, test_cpse, "VALVE CLASS 150")
    normalize_material_record(db, mat2)
    assert mat2.pressure_class == "CLASS150"

    mat3 = create_raw_material(db, test_cpse, "VALVE 150#")
    normalize_material_record(db, mat3)
    assert mat3.pressure_class == "CLASS150"

    mat4 = create_raw_material(db, test_cpse, "VALVE CLASS300")
    normalize_material_record(db, mat4)
    assert mat4.pressure_class == "CLASS300"

    mat5 = create_raw_material(db, test_cpse, "VALVE 300#")
    normalize_material_record(db, mat5)
    assert mat5.pressure_class == "CLASS300"

def test_norm_sizes(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "VALVE DN50")
    normalize_material_record(db, mat1)
    assert mat1.size == "DN50"

    mat2 = create_raw_material(db, test_cpse, "VALVE 50MM")
    normalize_material_record(db, mat2)
    assert mat2.size == "DN50"

    mat3 = create_raw_material(db, test_cpse, "VALVE 2 IN")
    normalize_material_record(db, mat3)
    assert mat3.size == "DN50"

def test_norm_connections(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "VALVE RF")
    normalize_material_record(db, mat1)
    assert mat1.connection_type == "RF"

    mat2 = create_raw_material(db, test_cpse, "VALVE RAISED FACE")
    normalize_material_record(db, mat2)
    assert mat2.connection_type == "RF"

    mat3 = create_raw_material(db, test_cpse, "VALVE SOCKET WELD")
    normalize_material_record(db, mat3)
    assert mat3.connection_type == "SOCKET_WELD"

def test_norm_trim(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "VALVE SS304 TRIM")
    normalize_material_record(db, mat1)
    assert mat1.trim == "SS304"

    mat2 = create_raw_material(db, test_cpse, "VALVE 316 TRIM")
    normalize_material_record(db, mat2)
    assert mat2.trim == "316"

    mat3 = create_raw_material(db, test_cpse, "VALVE", specs="TRIM 8")
    normalize_material_record(db, mat3)
    assert mat3.trim == "8"

    mat_missing = create_raw_material(db, test_cpse, "VALVE SS CS")
    normalize_material_record(db, mat_missing)
    assert mat_missing.trim is None

def test_norm_missing_attributes_are_null(db, test_cpse):
    mat = create_raw_material(db, test_cpse, "VALVE")
    normalize_material_record(db, mat)
    assert mat.size is None
    assert mat.pressure_class is None
    assert mat.body_material is None

def test_norm_ss_does_not_become_ss304(db, test_cpse):
    mat = create_raw_material(db, test_cpse, "VALVE SS")
    normalize_material_record(db, mat)
    assert mat.body_material == "STAINLESS_STEEL"
    assert mat.body_material != "SS304"

def test_norm_class150_vs_class300(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "CLASS150")
    mat2 = create_raw_material(db, test_cpse, "CLASS300")
    normalize_material_record(db, mat1)
    normalize_material_record(db, mat2)
    assert mat1.pressure_class != mat2.pressure_class

def test_norm_uom(db, test_cpse):
    mat_ea = create_raw_material(db, test_cpse, "V", uom="EA")
    mat_nos = create_raw_material(db, test_cpse, "V", uom="NOS")
    mat_pcs = create_raw_material(db, test_cpse, "V", uom="PCS")
    mat_unknown = create_raw_material(db, test_cpse, "V", uom="UNKNOWN_UOM")

    for mat in [mat_ea, mat_nos, mat_pcs, mat_unknown]:
        normalize_material_record(db, mat)

    assert mat_ea.normalized_uom == "EACH"
    assert mat_nos.normalized_uom == "EACH"
    assert mat_pcs.normalized_uom == "EACH"
    assert mat_unknown.normalized_uom is None
    assert mat_unknown.source_uom == "UNKNOWN_UOM"

def test_norm_source_data_unchanged(db, test_cpse):
    desc = "  BALL VALVE  2 IN CS  "
    mat = create_raw_material(db, test_cpse, desc)
    normalize_material_record(db, mat)

    assert mat.source_description == desc
    assert mat.normalized_description == "BALL VALVE 2 IN CS"
    assert mat.raw_source_data == {"original": desc}

def test_norm_is_idempotent(db, test_cpse):
    mat = create_raw_material(db, test_cpse, "BALL VALVE 2 IN CS CLASS150")

    audit1 = normalize_material_record(db, mat)
    db.commit()
    assert audit1 is not None
    assert mat.valve_type == "BALL"

    # Run again
    audit2 = normalize_material_record(db, mat)
    db.commit()
    assert audit2 is None # No changes means no new audit log
    assert mat.valve_type == "BALL"

# --- SAFETY TESTS ---

def test_critical_safety_1_no_inferred_trim(db, test_cpse):
    # "BALL VALVE 2 IN CS CLASS300 RF"
    mat = create_raw_material(db, test_cpse, "BALL VALVE 2 IN CS CLASS300 RF")
    normalize_material_record(db, mat)
    assert mat.valve_type == "BALL"
    assert mat.size == "DN50"
    assert mat.body_material == "CARBON_STEEL"
    assert mat.pressure_class == "CLASS300"
    assert mat.connection_type == "RF"
    assert mat.trim is None

def test_critical_safety_2_pressure_classes_distinct(db, test_cpse):
    mat_a = create_raw_material(db, test_cpse, "BALL VALVE 2 IN CS CLASS150 RF")
    mat_b = create_raw_material(db, test_cpse, "BALL VALVE 2 IN CS CLASS300 RF")
    normalize_material_record(db, mat_a)
    normalize_material_record(db, mat_b)

    assert mat_a.pressure_class == "CLASS150"
    assert mat_b.pressure_class == "CLASS300"

def test_critical_safety_3_trim_vs_body(db, test_cpse):
    mat1 = create_raw_material(db, test_cpse, "BALL VALVE 2 IN CS CLASS300 RF SS304 TRIM")
    normalize_material_record(db, mat1)
    assert mat1.trim == "SS304"
    assert mat1.body_material == "CARBON_STEEL"

    mat2 = create_raw_material(db, test_cpse, "BALL VALVE 2 IN SS CLASS300 RF")
    normalize_material_record(db, mat2)
    assert mat2.body_material == "STAINLESS_STEEL"
    assert mat2.trim is None

def test_api_endpoint(client: TestClient, db, test_cpse):
    mat = create_raw_material(db, test_cpse, "GATE VALVE")

    response = client.post(f"/api/v1/materials/{mat.id}/normalize")
    assert response.status_code == 200

    db.refresh(mat)
    assert mat.valve_type == "GATE"
    assert mat.category == "VALVE"

    logs = db.query(AuditLog).filter(AuditLog.entity_id == str(mat.id)).all()
    assert len(logs) == 1
    assert logs[0].action == "NORMALIZE"

def test_regression_patch_5d_case1(db, test_cpse):
    # Case 1: BALL VALVE 2 IN CS CLASS300 RF SS304 TRIM
    mat = Material(
        id=uuid.uuid4(),
        cpse_id=test_cpse.id,
        source_material_code="CASE-1",
        source_description="BALL VALVE 2 IN CS CLASS300 RF SS304 TRIM",
        source_uom="EA",
        category=None,
        raw_source_data={"original": "BALL VALVE 2 IN CS CLASS300 RF SS304 TRIM"}
    )
    db.add(mat)
    db.commit()

    normalize_material_record(db, mat)
    db.commit()
    db.refresh(mat)

    assert mat.category == "VALVE"
    assert mat.valve_type == "BALL"
    assert mat.size == "DN50"
    assert mat.body_material == "CARBON_STEEL"
    assert mat.pressure_class == "CLASS300"
    assert mat.connection_type == "RF"
    assert mat.trim == "SS304"
    assert mat.normalized_uom == "EACH"
    assert mat.normalized_description == "BALL VALVE 2 IN CS CLASS300 RF SS304 TRIM"

def test_regression_patch_5d_case2(db, test_cpse):
    # Case 2: BALL VLV DN50 CARBON STEEL CLASS 300 RF SS304
    mat = Material(
        id=uuid.uuid4(),
        cpse_id=test_cpse.id,
        source_material_code="CASE-2",
        source_description="BALL VLV DN50 CARBON STEEL CLASS 300 RF SS304",
        source_uom="EA",
        category=None,
        raw_source_data={"original": "BALL VLV DN50 CARBON STEEL CLASS 300 RF SS304"}
    )
    db.add(mat)
    db.commit()

    normalize_material_record(db, mat)
    db.commit()
    db.refresh(mat)

    assert mat.category == "VALVE"
    assert mat.valve_type == "BALL"
    assert mat.size == "DN50"
    assert mat.body_material == "CARBON_STEEL"
    assert mat.pressure_class == "CLASS300"
    assert mat.connection_type == "RF"
    assert mat.trim == "SS304"
    assert mat.normalized_uom == "EACH"
    assert mat.normalized_description == "BALL VLV DN50 CARBON STEEL CLASS 300 RF SS304"

