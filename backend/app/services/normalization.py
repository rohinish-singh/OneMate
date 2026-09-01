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

def extract_trim(text: str) -> Tuple[Optional[str], str]:
    """
    Extracts trim explicitly. Returns (trim, text_without_trim)
    so trim material isn't confused with body material.
    """
    if not text:
        return None, text

    # Match "... TRIM", but don't match "VALVE TRIM" (which just means the valve's trim)
    match1 = re.search(r'\b([A-Z0-9.\-]+)\s+TRIM\b', text)
    if match1 and match1.group(1) != "VALVE":
        trim = match1.group(1)
        # Remove it from text
        new_text = text[:match1.start()] + text[match1.end():]
        return trim, new_text

    # Match "TRIM ..."
    match2 = re.search(r'\bTRIM\s+([A-Z0-9.\-]+)\b', text)
    if match2:
        trim = match2.group(1)
        # Remove it from text
        new_text = text[:match2.start()] + text[match2.end():]
        return trim, new_text

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
    # Explicit specific mappings
    if re.search(r'\b(SS304)\b', text):
        return "SS304"
    if re.search(r'\b(SS316)\b', text):
        return "SS316"

    # Generic mappings
    if re.search(r'\b(SS|STAINLESS STEEL)\b', text):
        return "STAINLESS_STEEL"
    if re.search(r'\b(CS|C\.S\.|CARBON STEEL)\b', text):
        return "CARBON_STEEL"

    # Others can be added as needed
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

def normalize_material_record(db: Session, material: Material, actor: str = "system_normalization") -> Optional[AuditLog]:
    """
    Applies deterministic normalization and valve extraction to a material.
    Updates the derived fields idempotently.
    Returns an AuditLog if changes were made.
    """
    # Concatenate description and specifications for extraction search
    search_text = material.source_description or ""
    if material.source_specifications:
        search_text += " " + material.source_specifications

    search_text = normalize_text(search_text)

    # Extract trim first, leaving text without trim to avoid material confusion
    ext_trim, remaining_text = extract_trim(search_text)

    new_vals = {
        "normalized_description": normalize_text(material.source_description),
        "normalized_uom": normalize_uom(material.source_uom),
        "valve_type": extract_valve_type(search_text),
        "size": extract_size(search_text),
        "pressure_class": extract_pressure_class(search_text),
        "body_material": extract_body_material(remaining_text),
        "connection_type": extract_connection_type(search_text),
        "trim": ext_trim,
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
            reason="Deterministic valve normalization"
        )
        db.add(audit_log)
        db.flush()
        return audit_log

    return None
