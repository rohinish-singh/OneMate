import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from app.models import Material, AuditLog
from app.schemas.material import ImportSummary, ImportRowError

def process_material_import(
    db: Session, 
    cpse_id: uuid.UUID, 
    file_contents: bytes, 
    filename: str
) -> ImportSummary:
    """
    Parses and validates a CSV/XLSX file, saves valid Material records,
    creates AuditLog entries, and returns an import summary.
    """
    # 1. Parse file
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(file_contents), dtype=str)
        elif filename.lower().endswith(".xlsx"):
            df = pd.read_excel(BytesIO(file_contents), dtype=str)
        else:
            raise ValueError("Unsupported file format. Please upload .csv or .xlsx")
    except Exception as e:
        raise ValueError(f"Failed to parse file: {str(e)}")

    # 1.5 Header alias normalization
    ALIASES_CODE = {"source_material_code", "material code", "material_code", "material number", "material_number", "item code", "item_code", "item number", "item_number"}
    ALIASES_DESC = {"source_description", "description", "material description", "material_description", "long description", "long_description", "item description", "item_description"}
    ALIASES_UOM = {"source_uom", "uom", "unit", "base uom", "base_uom", "unit of measure", "unit_of_measure"}

    new_columns = {}
    canonical_counts = {"source_material_code": 0, "source_description": 0, "source_uom": 0}

    for col in df.columns:
        c = str(col).strip().lower()
        if c in ALIASES_CODE:
            new_columns[col] = "source_material_code"
            canonical_counts["source_material_code"] += 1
        elif c in ALIASES_DESC:
            new_columns[col] = "source_description"
            canonical_counts["source_description"] += 1
        elif c in ALIASES_UOM:
            new_columns[col] = "source_uom"
            canonical_counts["source_uom"] += 1
        else:
            new_columns[col] = col

    for canonical, count in canonical_counts.items():
        if count > 1:
            raise ValueError(f"Ambiguous headers: Multiple columns resolve to {canonical}")

    df.rename(columns=new_columns, inplace=True)

    # 2. Validate columns
    required_cols = {"source_material_code", "source_description", "source_uom"}
    actual_cols = set(df.columns)
    if not required_cols.issubset(actual_cols):
        missing = required_cols - actual_cols
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Replace pandas NaN with None for database insertion
    df = df.where(pd.notnull(df), None)

    # 3. Check for existing codes to prevent duplicate constraint violations
    existing_codes = {
        row[0] for row in 
        db.query(Material.source_material_code).filter(Material.cpse_id == cpse_id).all()
    }

    summary = ImportSummary(
        total_rows=len(df),
        imported_rows=0,
        rejected_rows=0,
        duplicate_rows=0,
        errors=[]
    )

    new_materials = []
    audit_logs = []
    seen_in_file = set()

    # 4. Process Rows
    for idx, row in df.iterrows():
        row_num = idx + 2  # Assuming row 1 is header
        
        mat_code = row.get("source_material_code")
        desc = row.get("source_description")
        uom = row.get("source_uom")
        specs = row.get("source_specifications")
        category = row.get("category")
        
        # Clean strings, treating NaN as None
        def safe_strip(val):
            if pd.isna(val) or val is None:
                return None
            return str(val).strip()

        mat_code = safe_strip(row.get("source_material_code"))
        desc = safe_strip(row.get("source_description"))
        uom = safe_strip(row.get("source_uom"))
        specs = safe_strip(row.get("source_specifications"))
        category = safe_strip(row.get("category"))

        # Row validation
        if not mat_code or not desc or not uom:
            summary.rejected_rows += 1
            summary.errors.append(ImportRowError(row=row_num, error="Missing mandatory fields (code, desc, or uom)"))
            continue

        if category and category.upper() != "VALVE":
            summary.rejected_rows += 1
            summary.errors.append(ImportRowError(row=row_num, error="Category must be 'VALVE' if provided"))
            continue

        if mat_code in existing_codes or mat_code in seen_in_file:
            summary.duplicate_rows += 1
            summary.rejected_rows += 1
            summary.errors.append(ImportRowError(row=row_num, error=f"Duplicate source_material_code: {mat_code}"))
            continue

        seen_in_file.add(mat_code)

        # Convert row to clean dict for raw_source_data
        raw_data = {k: str(v).strip() if isinstance(v, str) else v 
                    for k, v in row.to_dict().items() 
                    if not pd.isna(v) and v is not None}
        
        mat = Material(
            id=uuid.uuid4(),
            cpse_id=cpse_id,
            source_material_code=mat_code,
            source_description=desc,
            source_uom=uom,
            source_specifications=specs,
            category=category.upper() if category else None,
            raw_source_data=raw_data
        )
        new_materials.append(mat)
        
    # 5. Database transaction
    if new_materials:
        try:
            db.add_all(new_materials)
            
            for mat in new_materials:
                audit_logs.append(AuditLog(
                    id=uuid.uuid4(),
                    actor="system_import",
                    action="IMPORT",
                    entity_type="MATERIAL",
                    entity_id=str(mat.id),
                    before_state=None,
                    after_state=mat.raw_source_data,
                    reason="Initial ingestion"
                ))
            
            db.add_all(audit_logs)
            db.commit()
            summary.imported_rows = len(new_materials)
        except IntegrityError:
            db.rollback()
            raise ValueError("Database integrity error during bulk insert.")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Unexpected error saving to database: {str(e)}")
            
    return summary
