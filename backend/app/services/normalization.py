import re
import uuid
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Material, AuditLog

UOM_MAPPING = {
    "EA": "EACH",
    "EACH": "EACH",
    "NOS": "EACH",
    "PCS": "EACH",
    "PIECE": "EACH",
    "PIECES": "EACH",
    "NUMBER": "EACH",
    "NUMBERS": "EACH",
}

def normalize_text(text: str) -> str:
    """
    Normalizes case, whitespace, and basic separators.
    """
    if not text:
        return ""
    # Uppercase
    text = text.upper()
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing spaces
    return text.strip()

def normalize_uom(uom: str) -> Optional[str]:
    """
    Normalizes UOM using an explicit dictionary.
    """
    if not uom:
        return None
    clean_uom = normalize_text(uom)
    # Remove plural S if safe, but dictionary covers most
    return UOM_MAPPING.get(clean_uom, None)

def normalize_trim_grade(raw_trim: str) -> Optional[str]:
    """
    Standardizes trim grade to canonical representation (e.g. SS304, SS316).
    """
    if not raw_trim:
        return None
    raw = normalize_text(raw_trim)
    if re.search(r'\b(SS\s*304|304\s*SS|304)\b', raw):
        return "SS304"
    if re.search(r'\b(SS\s*316|316\s*SS|316)\b', raw):
        return "SS316"
    return raw

def extract_trim(text: str) -> Tuple[Optional[str], str]:
    """
    Extracts trim explicitly. Returns (trim, text_without_trim)
    so trim material isn't confused with body material.
    """
    if not text:
        return None, text

    # 1. Match "... TRIM" (e.g. "SS316 TRIM", "316SS TRIM", "316 SS TRIM", "SS 316 TRIM", "316 TRIM", "8 TRIM")
    match_ss_trim = re.search(r'\b(SS\s*304|304\s*SS|304|SS\s*316|316\s*SS|316)\s+TRIM\b', text)
    if match_ss_trim:
        trim_raw = match_ss_trim.group(1)
        new_text = text[:match_ss_trim.start()] + text[match_ss_trim.end():]
        return normalize_trim_grade(trim_raw), normalize_text(new_text)

    match1 = re.search(r'\b([A-Z0-9.\-]+)\s+TRIM\b', text)
    if match1 and match1.group(1) != "VALVE":
        trim_raw = match1.group(1)
        new_text = text[:match1.start()] + text[match1.end():]
        return normalize_trim_grade(trim_raw), normalize_text(new_text)

    # 2. Match "TRIM ..."
    match_trim_ss = re.search(r'\bTRIM\s+(SS\s*304|304\s*SS|304|SS\s*316|316\s*SS|316)\b', text)
    if match_trim_ss:
        trim_raw = match_trim_ss.group(1)
        new_text = text[:match_trim_ss.start()] + text[match_trim_ss.end():]
        return normalize_trim_grade(trim_raw), normalize_text(new_text)

    match2 = re.search(r'\bTRIM\s+([A-Z0-9.\-]+)\b', text)
    if match2:
        trim_raw = match2.group(1)
        new_text = text[:match2.start()] + text[match2.end():]
        return normalize_trim_grade(trim_raw), normalize_text(new_text)

    # 3. Match trailing trim grade (e.g. 316SS, SS316, 316 SS, SS 316, 304SS, SS304, 304 SS, SS 304, 316, 304)
    # ONLY when a separate primary body material is also present earlier in the text
    match_trailing = re.search(r'\b(SS\s*304|304\s*SS|SS\s*316|316\s*SS|SS304|SS316|304|316)\s*$', text)
    if match_trailing:
        prefix = text[:match_trailing.start()]
        has_primary_body = bool(re.search(r'\b(CS|C\.S\.|CARBON STEEL|WCB|CAST STEEL|CAST IRON|CI|SS|STAINLESS STEEL|CF8M|CF8)\b', prefix))
        if has_primary_body:
            trim_raw = match_trailing.group(1)
            new_text = prefix + text[match_trailing.end():]
            return normalize_trim_grade(trim_raw), normalize_text(new_text)

    # 4. Match explicit compound trim grade (e.g. 316SS, 304SS, 316 SS, SS 316) anywhere in text when primary body exists
    match_grade = re.search(r'\b(304\s*SS|316\s*SS|SS\s*304|SS\s*316)\b', text)
    if match_grade:
        prefix = text[:match_grade.start()]
        suffix = text[match_grade.end():]
        other_text = prefix + " " + suffix
        has_primary_body = bool(re.search(r'\b(CS|C\.S\.|CARBON STEEL|WCB|CAST STEEL|CAST IRON|CI|SS|STAINLESS STEEL|CF8M|CF8)\b', other_text))
        if has_primary_body:
            trim_raw = match_grade.group(1)
            return normalize_trim_grade(trim_raw), normalize_text(other_text)

    return None, text

def extract_valve_type(text: str) -> Optional[str]:
    """
    Extracts the valve type deterministically.
    """
    types = ["BALL", "GATE", "GLOBE", "BUTTERFLY", "CHECK", "NEEDLE", "PLUG", "DIAPHRAGM"]
    for vtype in types:
        if re.search(rf'\b{vtype}\b', text):
            return vtype
    return None

def extract_size(text: str) -> Optional[str]:
    """
    Extracts and standardizes size to DN representation.
    """
    # Look for DN xx
    match_dn = re.search(r'\bDN\s*(\d+)\b', text)
    if match_dn:
        return f"DN{match_dn.group(1)}"

    # Look for xx MM
    match_mm = re.search(r'\b(\d+)\s*MM\b', text)
    if match_mm:
        return f"DN{match_mm.group(1)}"

    # Look for INCH / IN / "
    match_in = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:IN|INCH|")\b', text)
    if match_in:
        val = match_in.group(1)
        # Convert deterministically
        inch_map = {
            "0.5": "DN15", "1/2": "DN15",
            "0.75": "DN20", "3/4": "DN20",
            "1": "DN25",
            "1.5": "DN40", "1-1/2": "DN40",
            "2": "DN50",
            "2.5": "DN65",
            "3": "DN80",
            "4": "DN100",
            "6": "DN150",
            "8": "DN200",
            "10": "DN250",
            "12": "DN300"
        }
        return inch_map.get(val, None)

    return None

def extract_pressure_class(text: str) -> Optional[str]:
    """
    Extracts pressure class deterministically.
    """
    match = re.search(r'\b(?:CLASS|CL)\s*(\d+)\b|\b(\d+)\s*#', text)
    if match:
        val = match.group(1) or match.group(2)
        return f"CLASS{val}"
    return None

def extract_body_material(text: str) -> Optional[str]:
    """
    Extracts body material deterministically from remaining text.
    """
    # Explicit carbon steel mappings have precedence if present
    if re.search(r'\b(CS|C\.S\.|CARBON STEEL|WCB|CAST STEEL)\b', text):
        return "CARBON_STEEL"

    # Explicit specific mappings
    if re.search(r'\b(SS304)\b', text):
        return "SS304"
    if re.search(r'\b(SS316)\b', text):
        return "SS316"

    # Generic mappings
    if re.search(r'\b(SS|STAINLESS STEEL|CF8M|CF8)\b', text):
        return "STAINLESS_STEEL"

    if re.search(r'\b(CAST IRON|CI)\b', text):
        return "CAST_IRON"

    return None

def extract_connection_type(text: str) -> Optional[str]:
    """
    Extracts connection type deterministically.
    """
    if re.search(r'\b(RF|RAISED FACE)\b', text):
        return "RF"
    if re.search(r'\b(SW|SOCKET WELD)\b', text):
        return "SOCKET_WELD"
    if re.search(r'\b(BW|BUTT WELD)\b', text):
        return "BUTT_WELD"
    if re.search(r'\b(THREADED|SCREWED)\b', text):
        return "THREADED"
    if re.search(r'\b(FLANGED|FLANGE)\b', text):
        return "FLANGED"
    return None

SUPPORTED_CATEGORIES = {"VALVE", "PUMP", "GASKET", "FLANGE", "BEARING", "FASTENER"}

def detect_category(text: str, explicit_category: Optional[str] = None) -> Optional[str]:
    """
    Deterministically detects the industrial material family/category.
    Precedence:
    1. Explicit source category, if provided and valid.
    2. Specific multi-word keywords.
    3. Broader family keywords.
    4. None (UNKNOWN) if no safe category can be established.
    """
    if explicit_category and explicit_category.upper() in SUPPORTED_CATEGORIES:
        return explicit_category.upper()

    if not text:
        return None

    # 1. Gasket
    if re.search(r'\b(SPIRAL WOUND GASKET|SPW GASKET|RING JOINT GASKET|RTJ GASKET|SHEET GASKET|GASKET)\b', text):
        return "GASKET"

    # 2. Bearing (prioritized before valve ball check)
    if re.search(r'\b(BALL BEARING|ROLLER BEARING|NEEDLE BEARING|TAPERED BEARING|BEARING)\b', text):
        return "BEARING"

    # 3. Flange
    if re.search(r'\b(WELD NECK FLANGE|WN FLANGE|BLIND FLANGE|SLIP ON FLANGE|SO FLANGE|SOCKET WELD FLANGE|THREADED FLANGE|FLANGE)\b', text):
        return "FLANGE"

    # 4. Pump
    if re.search(r'\b(CENTRIFUGAL PUMP|VACUUM PUMP|SUBMERSIBLE PUMP|POSITIVE DISPLACEMENT PUMP|PUMP)\b', text):
        return "PUMP"

    # 5. Fastener
    if re.search(r'\b(HEX BOLT|STUD BOLT|ANCHOR BOLT|EYE BOLT|U BOLT|HEX NUT|LOCK NUT|WASHER|FASTENER|BOLT|SCREW)\b', text):
        return "FASTENER"

    # 6. Valve
    if re.search(r'\b(BALL VALVE|BALL VLV|GATE VALVE|GATE VLV|GLOBE VALVE|GLOBE VLV|CHECK VALVE|CHECK VLV|BUTTERFLY VALVE|BUTTERFLY VLV|NEEDLE VALVE|NEEDLE VLV|PLUG VALVE|PLUG VLV|DIAPHRAGM VALVE|DIAPHRAGM VLV|VALVE|VLV)\b', text):
        return "VALVE"

    # Fallback to single standalone valve type words
    valve_types = ["BALL", "GATE", "GLOBE", "BUTTERFLY", "CHECK", "NEEDLE", "PLUG", "DIAPHRAGM"]
    for vt in valve_types:
        if re.search(rf'\b{vt}\b', text):
            return "VALVE"

    return None

def normalize_material_record(db: Session, material: Material, actor: str = "system_normalization") -> Optional[AuditLog]:
    """
    Applies category-aware deterministic normalization to a material.
    Updates the derived fields idempotently.
    Returns an AuditLog if changes were made.
    """
    # Concatenate description and specifications for extraction search
    search_text = material.source_description or ""
    if material.source_specifications:
        search_text += " " + material.source_specifications

    search_text = normalize_text(search_text)

    # 1. Detect Category
    category = detect_category(search_text, material.category)

    norm_desc = normalize_text(material.source_description)
    norm_uom = normalize_uom(material.source_uom)

    valve_type = None
    size = None
    pressure_class = None
    body_material = None
    connection_type = None
    trim = None

    if category == "VALVE":
        ext_trim, remaining_text = extract_trim(search_text)
        valve_type = extract_valve_type(search_text)
        size = extract_size(search_text)
        pressure_class = extract_pressure_class(search_text)
        body_material = extract_body_material(remaining_text)
        connection_type = extract_connection_type(search_text)
        trim = ext_trim
    elif category == "FLANGE":
        size = extract_size(search_text)
        pressure_class = extract_pressure_class(search_text)
        body_material = extract_body_material(search_text)
        # For flanges, check if RF or explicit connection facing is stated
        if re.search(r'\b(RF|RAISED FACE|SW|SOCKET WELD|BW|BUTT WELD|THREADED|SCREWED)\b', search_text):
            connection_type = extract_connection_type(search_text)
    elif category == "GASKET":
        size = extract_size(search_text)
        pressure_class = extract_pressure_class(search_text)
        body_material = extract_body_material(search_text)
    elif category == "PUMP":
        body_material = extract_body_material(search_text)
    elif category == "FASTENER":
        body_material = extract_body_material(search_text)
    elif category == "BEARING":
        pass

    new_vals = {
        "category": category,
        "normalized_description": norm_desc,
        "normalized_uom": norm_uom,
        "valve_type": valve_type,
        "size": size,
        "pressure_class": pressure_class,
        "body_material": body_material,
        "connection_type": connection_type,
        "trim": trim,
    }

    # Check if anything actually changed (idempotency)
    changed = False
    before_state = {}
    after_state = {}

    for key, new_val in new_vals.items():
        old_val = getattr(material, key)
        if old_val != new_val:
            changed = True
            before_state[key] = old_val
            after_state[key] = new_val
            setattr(material, key, new_val)

    if changed:
        audit_log = AuditLog(
            id=uuid.uuid4(),
            actor=actor,
            action="NORMALIZE",
            entity_type="MATERIAL",
            entity_id=str(material.id),
            before_state=before_state,
            after_state=after_state,
            reason="Deterministic category-aware normalization"
        )
        db.add(audit_log)
        db.flush()
        return audit_log

    return None

