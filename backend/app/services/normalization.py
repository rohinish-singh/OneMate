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
    "SET": "SET",
    "M": "METER",
    "MTR": "METER",
    "KG": "KG",
}

def normalize_text(text: str) -> str:
    """
    Normalizes case, whitespace, and basic separators.
    """
    if not text:
        return ""
    text = text.upper()
    text = re.sub(r'[\t\r\n]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_uom(uom: Optional[str]) -> Optional[str]:
    """
    Standardizes UOMs deterministically according to UOM_MAPPING.
    Returns None if UOM is not recognized.
    """
    if not uom:
        return None
    cleaned = normalize_text(uom)
    return UOM_MAPPING.get(cleaned, None)

def normalize_trim_grade(raw_trim: str) -> str:
    """
    Normalizes trim material string to standard representation.
    """
    norm = normalize_text(raw_trim)
    if "316" in norm:
        return "SS316"
    if "304" in norm:
        return "SS304"
    if "STELLITE" in norm:
        return "STELLITE"
    if "MONEL" in norm:
        return "MONEL"
    if "SS" in norm or "13CR" in norm:
        return "SS"
    return norm.replace(" ", "")

def extract_trim(text: str) -> Tuple[Optional[str], str]:
    """
    Extracts trim material and returns (trim_value, remaining_text).
    """
    non_trim_words = {
        "VALVE", "GATE", "BALL", "GLOBE", "CHECK", "BUTTERFLY", "PLUG",
        "NEEDLE", "DIAPHRAGM", "BODY", "CLASS", "CL", "TYPE", "INCH", "MM", "DN"
    }
    seat_elastomers = {"SEAT", "LINER", "SLEEVE", "EPDM", "PTFE", "TEFLON", "NBR", "BUNA", "VITON", "FKM"}

    # 1. Match explicit <grade> TRIM: e.g. SS316 TRIM, 316 TRIM, STELLITE TRIM
    match_kw_trim = re.search(r'\b([A-Z0-9\.\-]+)\s+TRIM\b', text)
    if match_kw_trim:
        trim_raw = match_kw_trim.group(1)
        if trim_raw not in non_trim_words and trim_raw not in seat_elastomers:
            remaining = text[:match_kw_trim.start()] + text[match_kw_trim.end():]
            return normalize_trim_grade(trim_raw), normalize_text(remaining)

    # 2. Match explicit TRIM <grade>: e.g. TRIM 8, TRIM SS316, TRIM 316, TRIM STELLITE
    match_trim_kw = re.search(r'\bTRIM\s+([A-Z0-9\.\-]+)\b', text)
    if match_trim_kw:
        trim_raw = match_trim_kw.group(1)
        after_pos = match_trim_kw.end()
        after_text = text[after_pos:].strip()
        is_seat_spec = bool(re.match(r'^(?:SEAT|LINER|SLEEVE)\b', after_text))
        if trim_raw not in seat_elastomers and not is_seat_spec and trim_raw not in non_trim_words:
            remaining = text[:match_trim_kw.start()] + text[match_trim_kw.end():]
            return normalize_trim_grade(trim_raw), normalize_text(remaining)

    # 2. Match compound trim e.g. CS/SS, CS/SS316, CS/316
    match_slash = re.search(r'\b(?:CS|C\.S\.|CARBON\s+STEEL)/(SS\s*304|SS\s*316|304\s*SS|316\s*SS|SS304|SS316|316|304|SS)\b', text)
    if match_slash:
        trim_raw = match_slash.group(1)
        # Replace the compound with just the body material for further processing
        remaining = text[:match_slash.start()] + " CS " + text[match_slash.end():]
        return normalize_trim_grade(trim_raw), normalize_text(remaining)

    # 3. Match trailing SS grades if preceded by an explicit carbon steel or other body material
    match_trailing = re.search(r'\b(SS\s*304|304\s*SS|SS\s*316|316\s*SS|SS304|SS316|304|316)\s*$', text)
    if match_trailing:
        prefix = text[:match_trailing.start()]
        has_primary_body = bool(re.search(r'\b(CS|C\.S\.|CARBON STEEL|WCB|CAST STEEL|CAST IRON|CI|SS|STAINLESS STEEL|CF8M|CF8)\b', prefix))
        if has_primary_body:
            trim_raw = match_trailing.group(1)
            new_text = prefix + text[match_trailing.end():]
            return normalize_trim_grade(trim_raw), normalize_text(new_text)

    # 4. Match explicit compound trim grade anywhere in text when primary body exists
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
    if re.search(r'\b(SAFETY\s+RELIEF|RELIEF\s+VALVE|\bPSV\b|\bSRV\b)\b', text):
        return "SAFETY_RELIEF"

    if re.search(r'\b(B/F\s*VALVE|BF\s*VALVE|B/F\s+VLV|B/F)\b', text):
        return "BUTTERFLY"

    types = ["BALL", "GATE", "GLOBE", "BUTTERFLY", "CHECK", "NEEDLE", "PLUG", "DIAPHRAGM"]
    for vtype in types:
        if re.search(rf'\b{vtype}\b', text):
            return vtype
    return None

def normalize_seat_material(raw: str) -> str:
    """Normalizes valve seat/liner/elastomer material string to standard representation."""
    cleaned = raw.strip().upper().replace(" ", "")
    if "TEFLON" in cleaned or cleaned == "TFE":
        return "PTFE"
    if "BUNA" in cleaned or "NITRILE" in cleaned:
        return "NBR"
    if cleaned in ("FKM", "FPM"):
        return "VITON"
    if cleaned == "R-PTFE":
        return "RTFE"
    return cleaned

def extract_seat_material(text: str, valve_type: Optional[str] = None) -> Optional[str]:
    """
    Extracts seat/liner/elastomer material deterministically.
    Recognizes explicit seat/liner designations across all valves,
    and soft seat/liner materials in butterfly/resilient-seated valves.
    """
    # 1. Explicit mention: <material> SEAT / LINER / SLEEVE
    m_seat_post = re.search(
        r'\b(EPDM|PTFE|TEFLON|TFE|RTFE|R-PTFE|NBR|BUNA[\s\-]*N|BUNA|NITRILE|VITON|FKM|PEEK|STELLITE|METAL|RUBBER)\s+(?:SEAT|LINER|SLEEVE|INSERT)\b',
        text,
        re.IGNORECASE
    )
    if m_seat_post:
        return normalize_seat_material(m_seat_post.group(1))

    # 2. Explicit mention: SEAT / LINER / SLEEVE [OF / : / -] <material>
    m_seat_pre = re.search(
        r'\b(?:SEAT|LINER|SLEEVE)\s*(?:MATERIAL|MATL|MAT)?\s*(?:OF|[:\-=])?\s*(EPDM|PTFE|TEFLON|TFE|RTFE|R-PTFE|NBR|BUNA[\s\-]*N|BUNA|NITRILE|VITON|FKM|PEEK|STELLITE|METAL|RUBBER)\b',
        text,
        re.IGNORECASE
    )
    if m_seat_pre:
        return normalize_seat_material(m_seat_pre.group(1))

    # 3. In butterfly valves, standalone elastomer/soft material indicates the seat/liner
    is_butterfly = (valve_type == "BUTTERFLY") or bool(re.search(r'\b(BUTTERFLY|B/F|BF)\b', text, re.IGNORECASE))
    if is_butterfly:
        m_elastomer = re.search(
            r'\b(EPDM|PTFE|TEFLON|TFE|RTFE|NBR|BUNA[\s\-]*N|BUNA|NITRILE|VITON|FKM|PEEK)\b',
            text,
            re.IGNORECASE
        )
        if m_elastomer:
            return normalize_seat_material(m_elastomer.group(1))

    return None

def extract_size(text: str) -> Optional[str]:
    """
    Extracts and standardizes size to DN representation.
    """
    # Look for DN xx
    match_dn = re.search(r'\bDN\s*(\d+)\b', text)
    if match_dn:
        return f"DN{match_dn.group(1)}"

    # Look for xx NB
    match_nb = re.search(r'\b(\d+)\s*NB\b', text)
    if match_nb:
        return f"DN{match_nb.group(1)}"

    # Look for xx MM
    match_mm = re.search(r'\b(\d+)\s*MM\b', text)
    if match_mm:
        return f"DN{match_mm.group(1)}"

    # Look for INCH / IN / "
    match_in = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:IN|INCH|")|\b(\d+(?:\.\d+)?)"', text)
    if match_in:
        val = match_in.group(1) or match_in.group(2)
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
    match = re.search(r'\b(?:CLASS|CL)\s*(\d+)\b|\b(\d+)\s*#|\b(\d+)\s*LB\b', text)
    if match:
        val = match.group(1) or match.group(2) or match.group(3)
        return f"CLASS{val}"

    match_bar = re.search(r'\b(\d+)\s*BAR\b', text)
    if match_bar:
        return f"{match_bar.group(1)} BAR"

    match_psi = re.search(r'\b(\d+)\s*PSI\b', text)
    if match_psi:
        return f"{match_psi.group(1)}PSI"

    return None

def extract_body_material(text: str) -> Optional[str]:
    """
    Extracts body material deterministically from text with comprehensive synonym support.
    """
    # Explicit carbon steel mappings have precedence if present
    if re.search(r'\b(CS|CARBON STEEL|WCB|A216[\s\-]*WCB|CAST STEEL|A105|FORGED STEEL)\b|\bC\.S\.(?!\w)', text):
        return "CARBON_STEEL"

    # Explicit specific mappings
    if re.search(r'\b(SS\s*316L?|316L?\s*SS|AISI\s*316|CF8M|A351[\s\-]*CF8M)\b', text):
        return "SS316"
    if re.search(r'\b(SS\s*304L|304L\s*SS|SS304L)\b', text):
        return "SS304L"
    if re.search(r'\b(SS\s*304|304\s*SS|AISI\s*304|CF8|A351[\s\-]*CF8)\b', text):
        return "SS304"

    if re.search(r'\b(ALLOY\s*20)\b', text):
        return "ALLOY_20"

    # Generic mappings
    if re.search(r'\b(SS|STAINLESS STEEL)\b', text):
        return "STAINLESS_STEEL"

    if re.search(r'\b(CAST IRON|CI)\b|\bC\.I\.(?!\w)', text):
        return "CAST_IRON"

    return None

def extract_connection_type(text: str) -> Optional[str]:
    """
    Extracts connection type deterministically.
    """
    if re.search(r'\b(RTJ|RING JOINT)\b', text):
        return "RTJ"
    if re.search(r'\b(RF|RAISED FACE|WNRF)\b', text):
        return "RF"
    if re.search(r'\b(SW|SOCKET WELD)\b', text):
        return "SOCKET_WELD"
    if re.search(r'\b(BW|BUTT WELD)\b', text):
        return "BUTT_WELD"
    if re.search(r'\b(THREADED|SCREWED|NPT)\b', text):
        return "NPT" if "NPT" in text else "THREADED"
    if re.search(r'\b(FLANGED|FLANGE)\b', text):
        return "FLANGED"
    if re.search(r'\b(WAFER)\b', text):
        return "WAFER"
    return None

SUPPORTED_CATEGORIES = {
    "VALVE", "PIPE", "FLANGE", "GASKET", "PUMP",
    "TRANSMITTER", "O-RING", "FASTENER", "FITTING",
    "MOTOR", "BEARING", "BELT", "STRAINER"
}

# The database table 'material' has a check constraint restricting the 'category' column to these values or NULL.
# Non-valve categories outside this set have their true category stored in normalized_attributes to obey schema without migration.
DB_ALLOWED_CATEGORIES = {"VALVE", "PUMP", "GASKET", "FLANGE", "BEARING", "FASTENER"}

CATEGORY_PATTERNS = [
    ("STRAINER", r"\b(Y-STRAINER|BASKET STRAINER|DUPLEX STRAINER|CONICAL STRAINER|STRAINER)\b"),
    ("TRANSMITTER", r"\b(PRESSURE TRANSMITTER|TEMPERATURE TRANSMITTER|PRESS XMTR|TEMP TRANSMITTER|TRANSMITTER|\bPT\s+0-|\bTT\s+PT)\b"),
    ("O-RING", r"\b(O-RING|O RING|ORING)\b"),
    ("BEARING", r"\b(BALL BEARING|ROLLER BEARING|NEEDLE BEARING|TAPERED BEARING|BEARING)\b"),
    ("BELT", r"\b(V-BELT|V-TYPE BELT|TIMING BELT|CONVEYOR BELT|BELT)\b"),
    ("MOTOR", r"\b(INDUCTION MOTOR|AC MOTOR|ELECTRIC MOTOR|MOTOR)\b"),
    ("PUMP", r"\b(CENTRIFUGAL PUMP|VACUUM PUMP|SUBMERSIBLE PUMP|POSITIVE DISPLACEMENT PUMP|PUMP)\b"),
    ("GASKET", r"\b(SPIRAL WOUND GASKET|SPW GASKET|\bSWG\b|RING JOINT GASKET|RTJ GASKET|SHEET GASKET|GASKET)\b"),
    ("FLANGE", r"\b(WELD NECK FLANGE|WN FLANGE|BLIND FLANGE|SLIP ON FLANGE|SO FLANGE|SOCKET WELD FLANGE|THREADED FLANGE|\bWNRF\b|FLANGE)\b"),
    ("PIPE", r"\b(SEAMLESS PIPE|SMLS PIPE|ERW PIPE|WELDED PIPE|PIPE)\b"),
    ("FASTENER", r"\b(STUD BOLT|HEX BOLT|ANCHOR BOLT|EYE BOLT|U BOLT|HEX NUT|LOCK NUT|WASHER|FASTENER|\bBOLT\b|\bSCREW\b)\b"),
    ("FITTING", r"\b(ELBOW|EQUAL TEE|REDUCING TEE|\bTEE\b|CONCENTRIC REDUCER|ECCENTRIC REDUCER|CONC REDUCER|REDUCER|COUPLING|UNION|NIPPLE|FITTING)\b"),
    ("VALVE", r"\b(BALL VALVE|BALL VLV|GATE VALVE|GATE VLV|GLOBE VALVE|GLOBE VLV|CHECK VALVE|CHECK VLV|BUTTERFLY VALVE|BUTTERFLY VLV|NEEDLE VALVE|NEEDLE VLV|PLUG VALVE|PLUG VLV|DIAPHRAGM VALVE|DIAPHRAGM VLV|SAFETY RELIEF VALVE|RELIEF VALVE|\bPSV\b|\bSRV\b|VALVE|\bVLV\b|\bB/F VALVE\b|\bCHK VALVE\b)\b"),
]

def detect_category(text: str, explicit_category: Optional[str] = None) -> Optional[str]:
    """
    Deterministically detects the industrial material family/category.
    Precedence:
    1. Explicit source category, if provided and valid.
    2. Specific multi-word patterns.
    3. Standalone valve types.
    4. None (UNKNOWN) if no safe category can be established.
    """
    if explicit_category and explicit_category.upper() in SUPPORTED_CATEGORIES:
        return explicit_category.upper()

    if not text:
        return None

    for cat, pat in CATEGORY_PATTERNS:
        if re.search(pat, text):
            return cat

    valve_types = ["BALL", "GATE", "GLOBE", "BUTTERFLY", "CHECK", "NEEDLE", "PLUG", "DIAPHRAGM"]
    for vt in valve_types:
        if re.search(rf'\b{vt}\b', text):
            return "VALVE"

    return None

def extract_category_attributes(category: str, text: str) -> Tuple[Dict[str, Any], str]:
    """
    Extracts category-specific structured attributes and produces a deterministic canonical description.
    """
    attrs: Dict[str, Any] = {"category": category}
    parts = [category]

    if category == "STRAINER":
        st_type = "Y-TYPE" if re.search(r"\b(Y-STRAINER|Y-TYPE|Y TYPE)\b", text) else ("BASKET" if "BASKET" in text else None)
        sz = extract_size(text)
        pr = extract_pressure_class(text)
        mat = extract_body_material(text)
        m = re.search(r"(?:MESH\s*(\d+)|\b(\d+)\s*MESH|\b(\d+)MESH)\b", text)
        mesh = m.group(1) or m.group(2) or m.group(3) if m else None

        if st_type: attrs["type"] = st_type; parts.append(st_type)
        if sz: attrs["size"] = sz; parts.append(sz)
        if pr: attrs["pressure_rating"] = pr; parts.append(pr)
        if mat: attrs["material_grade"] = mat; parts.append(mat)
        if mesh: attrs["mesh"] = mesh; parts.append(f"MESH{mesh}")

    elif category == "PIPE":
        cons = "SEAMLESS" if re.search(r"\b(SEAMLESS|SMLS)\b", text) else ("ERW" if "ERW" in text else ("WELDED" if "WELDED" in text else None))
        sz = extract_size(text)
        sch_m = re.search(r"\b(SCH\s*\d+[A-Z]?)\b", text)
        sch = sch_m.group(1).replace(" ", "") if sch_m else None
        mat = extract_body_material(text)
        std = "ASTM A106 GR B" if re.search(r"\b(ASTM\s+A106|A106)\b", text) else None

        if cons: attrs["construction"] = cons; parts.append(cons)
        if sz: attrs["size"] = sz; parts.append(sz)
        if sch: attrs["schedule"] = sch; parts.append(sch)
        if mat: attrs["material_grade"] = mat; parts.append(mat)
        if std: attrs["standard_grade"] = std; parts.append(std)

    elif category == "FLANGE":
        fl_type = "WELD_NECK" if re.search(r"\b(WELD\s+NECK|WN|WNRF)\b", text) else ("BLIND" if re.search(r"\b(BLIND|BLND)\b", text) else None)
        sz = extract_size(text)
        pr = extract_pressure_class(text)
        mat = extract_body_material(text)
        conn = "RTJ" if "RTJ" in text else ("RF" if re.search(r"\b(RF|RAISED\s+FACE|WNRF)\b", text) else None)

        if fl_type: attrs["flange_type"] = fl_type; parts.append(fl_type)
        if sz: attrs["size"] = sz; parts.append(sz)
        if pr: attrs["pressure_rating"] = pr; parts.append(pr)
        if mat: attrs["material_grade"] = mat; parts.append(mat)
        if conn: attrs["facing_connection"] = conn; parts.append(conn)

    elif category == "GASKET":
        g_type = "SPIRAL_WOUND" if re.search(r"\b(SPIRAL\s+WOUND|SPW|SWG)\b", text) else ("RING_JOINT" if re.search(r"\b(RING\s+JOINT|RTJ)\b", text) else None)
        sz = extract_size(text)
        pr = extract_pressure_class(text)
        mat_fill = "SS316/GRAPHITE" if re.search(r"\b(SS316.*GRAPHITE|GRAPHITE.*SS316)\b", text) else ("SS304/GRAPHITE" if re.search(r"\b(SS304.*GRAPHITE|GRAPHITE.*SS304)\b", text) else None)

        if g_type: attrs["gasket_type"] = g_type; parts.append(g_type)
        if sz: attrs["size"] = sz; parts.append(sz)
        if pr: attrs["pressure_rating"] = pr; parts.append(pr)
        if mat_fill: attrs["materials_filler"] = mat_fill; parts.append(mat_fill)

    elif category == "PUMP":
        p_type = "CENTRIFUGAL" if "CENTRIFUGAL" in text else None
        flow_m = re.search(r"\b(\d+)\s*(?:M3/HR|M3/H)\b", text)
        flow = f"{flow_m.group(1)} M3/HR" if flow_m else None
        head_m = re.search(r"\b(\d+)\s*(?:M\s+HEAD|MTR\s+HD|M)\b", text)
        head = f"{head_m.group(1)}M" if head_m else None
        mat = extract_body_material(text)

        if p_type: attrs["pump_type"] = p_type; parts.append(p_type)
        if flow: attrs["flow_rate"] = flow; parts.append(flow)
        if head: attrs["head"] = head; parts.append(head)
        if mat: attrs["casing_material"] = mat; parts.append(mat)

    elif category == "TRANSMITTER":
        i_type = "PRESSURE" if re.search(r"\b(PRESSURE|PRESS|\bPT\b)\b", text) else ("TEMPERATURE" if re.search(r"\b(TEMPERATURE|TEMP|\bTT\b)\b", text) else None)
        rng_m = re.search(r"\b(0-\d+\s*BAR|PT-?100|THERMOCOUPLE\s+TYPE\s+[A-Z])\b", text)
        rng = rng_m.group(1).replace("-", " ") if rng_m else None
        if rng and "0 " in rng:
            rng = rng.replace("0 ", "0-")
        sig = "4-20MA" if re.search(r"4-20\s*MA", text) else None
        proto = "HART" if "HART" in text else None

        if i_type: attrs["instrument_type"] = i_type; parts.append(i_type)
        if rng: attrs["measurement_range"] = rng; parts.append(rng)
        if sig: attrs["signal"] = sig; parts.append(sig)
        if proto: attrs["protocol"] = proto; parts.append(proto)

    elif category == "O-RING":
        mat = "VITON" if "VITON" in text else ("FKM" if "FKM" in text else ("NBR" if "NBR" in text else None))
        id_m = re.search(r"(?:(\d+)\s*MM\s*ID|ID\s*(\d+))", text)
        in_d = f"{id_m.group(1) or id_m.group(2)}MM" if id_m else None
        cs_m = re.search(r"(?:(\d+)\s*MM\s*CS|X\s*(\d+)\s*MM)", text)
        cs = f"{cs_m.group(1) or cs_m.group(2)}MM" if cs_m else None

        if mat: attrs["material_elastomer"] = mat; parts.append(mat)
        if in_d: attrs["inner_diameter"] = in_d; parts.append(f"ID {in_d}")
        if cs: attrs["cross_section"] = cs; parts.append(f"CS {cs}")

    elif category == "FASTENER":
        f_type = "STUD_BOLT" if re.search(r"\b(STUD\s+BOLT|BOLT,\s*STUD)\b", text) else ("HEX_BOLT" if re.search(r"\b(HEX\s+BOLT)\b", text) else None)
        sz_m = re.search(r"\b(M\d+)\b", text)
        sz = sz_m.group(1) if sz_m else None
        len_m = re.search(r"(?:X\s*(\d+)\s*MM|\b(\d+)\s*MM\b)", text)
        length = f"{len_m.group(1) or len_m.group(2)}MM" if len_m else None
        gr = "B7/2H" if re.search(r"\b(B7/2H|B7\s*/\s*A194\s*2H)\b", text) else ("B7" if re.search(r"\bB7\b", text) else None)
        nuts = "2 NUTS" if re.search(r"\b2\s*NUTS\b", text) else None

        if f_type: attrs["type"] = f_type; parts.append(f_type)
        if sz: attrs["size"] = sz; parts.append(sz)
        if length: attrs["length"] = length; parts.append(f"X {length}")
        if gr: attrs["grade"] = gr; parts.append(gr)
        if nuts: attrs["nut_specification"] = nuts; parts.append(nuts)

    elif category == "FITTING":
        fit_type = None
        if re.search(r"\b(90\s*DEG|90\s*DEGREE)\b", text): fit_type = "ELBOW 90 DEG"
        elif re.search(r"\b(45\s*DEG|45\s*DEGREE)\b", text): fit_type = "ELBOW 45 DEG"
        elif re.search(r"\b(EQUAL\s+TEE|TEE\s+EQUAL)\b", text): fit_type = "TEE EQUAL"
        elif re.search(r"\b(REDUCING\s+TEE|TEE\s+REDUCING)\b", text): fit_type = "TEE REDUCING"
        elif re.search(r"\b(CONCENTRIC\s+REDUCER|REDUCER\s+CONCENTRIC|CONC\s+REDUCER|REDUCER\s+CONC)\b", text): fit_type = "REDUCER CONCENTRIC"
        elif re.search(r"\b(ECCENTRIC\s+REDUCER|REDUCER\s+ECCENTRIC)\b", text): fit_type = "REDUCER ECCENTRIC"

        sz = extract_size(text)
        if not sz:
            sz_m = re.search(r"\b(\d+X\d+\s*IN|\d+X\d+\s*MM)\b", text)
            if sz_m: sz = sz_m.group(1)
        sch_m = re.search(r"\b(SCH\s*\d+[A-Z]?)\b", text)
        sch = sch_m.group(1).replace(" ", "") if sch_m else None
        mat = extract_body_material(text)

        if fit_type: attrs["fitting_type"] = fit_type; parts.append(fit_type)
        if sz: attrs["size"] = sz; parts.append(sz)
        if sch: attrs["schedule"] = sch; parts.append(sch)
        if mat: attrs["material_grade"] = mat; parts.append(mat)

    elif category == "MOTOR":
        m_type = "INDUCTION" if "INDUCTION" in text else "AC"
        ph = "3PH" if re.search(r"\b(3PH|3-PHASE)\b", text) else None
        pwr_m = re.search(r"\b(\d+)\s*KW\b", text)
        pwr = f"{pwr_m.group(1)}KW" if pwr_m else None
        volt_m = re.search(r"\b(\d+)\s*V\b", text)
        volt = f"{volt_m.group(1)}V" if volt_m else None
        spd_m = re.search(r"\b(\d+)\s*RPM\b", text)
        spd = f"{spd_m.group(1)}RPM" if spd_m else None
        eff_m = re.search(r"\b(IE\d)\b", text)
        eff = eff_m.group(1) if eff_m else None

        if m_type: attrs["motor_type"] = m_type; parts.append(m_type)
        if ph: attrs["phase"] = ph; parts.append(ph)
        if pwr: attrs["power"] = pwr; parts.append(pwr)
        if volt: attrs["voltage"] = volt; parts.append(volt)
        if spd: attrs["speed"] = spd; parts.append(spd)
        if eff: attrs["efficiency"] = eff; parts.append(eff)

    elif category == "BEARING":
        b_type = "BALL DEEP GROOVE" if re.search(r"\b(BALL\s+DEEP\s+GROOVE|BALL\s+BEARING)\b", text) else ("ROLLER CYLINDRICAL" if re.search(r"\b(ROLLER\s+CYLINDRICAL)\b", text) else None)
        num_m = re.search(r"\b(6\d{3}|NU\d{3})\b", text)
        num = num_m.group(1) if num_m else None
        seal_m = re.search(r"\b(ZZ|2Z|2RS|RS)\b", text)
        seal = "ZZ" if seal_m and seal_m.group(1) in ["ZZ", "2Z"] else (seal_m.group(1) if seal_m else None)

        if b_type: attrs["bearing_type"] = b_type; parts.append(b_type)
        if num: attrs["bearing_number"] = num; parts.append(num)
        if seal: attrs["seal_shield"] = seal; parts.append(seal)

    elif category == "BELT":
        b_type = "V-BELT" if re.search(r"\b(V-BELT|V-TYPE)\b", text) else None
        prof_m = re.search(r"\b(SPB|SPA|SPC)\b", text)
        prof = prof_m.group(1) if prof_m else None
        len_m = re.search(r"\b(\d{4})\b", text)
        length = len_m.group(1) if len_m else None

        if b_type: attrs["belt_type"] = b_type; parts.append(b_type)
        if prof: attrs["profile"] = prof; parts.append(prof)
        if length: attrs["length"] = length; parts.append(length)

    canonical_desc = " ".join(parts) if len(parts) > 1 else text
    return attrs, canonical_desc

def normalize_material_record(db: Session, material: Material, actor: str = "system_normalization") -> Optional[AuditLog]:
    """
    Applies category-aware deterministic normalization to a material.
    Updates the derived fields and JSONB normalized_attributes idempotently.
    Returns an AuditLog if changes were made.
    """
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
    normalized_attributes: Dict[str, Any] = {}

    if category == "VALVE":
        ext_trim, remaining_text = extract_trim(search_text)
        valve_type = extract_valve_type(search_text)
        size = extract_size(search_text)
        pressure_class = extract_pressure_class(search_text)
        body_material = extract_body_material(remaining_text)
        connection_type = extract_connection_type(search_text)
        trim = ext_trim
        seat_material = extract_seat_material(search_text, valve_type=valve_type)

        normalized_attributes = {
            "schema_version": "2.0",
            "category": category,
            "valve_type": valve_type,
            "size": size,
            "pressure_class": pressure_class,
            "body_material": body_material,
            "connection_type": connection_type,
            "trim": trim,
            "seat_material": seat_material,
        }
    elif category == "FLANGE":
        cat_attrs, _ = extract_category_attributes(category, search_text)
        normalized_attributes = {
            "schema_version": "2.0",
            **cat_attrs
        }
        size = extract_size(search_text)
        pressure_class = extract_pressure_class(search_text)
        body_material = extract_body_material(search_text)
        if re.search(r'\b(RF|RAISED FACE|SW|SOCKET WELD|BW|BUTT WELD|THREADED|SCREWED)\b', search_text):
            connection_type = extract_connection_type(search_text)
    elif category == "GASKET":
        cat_attrs, _ = extract_category_attributes(category, search_text)
        normalized_attributes = {
            "schema_version": "2.0",
            **cat_attrs
        }
        size = extract_size(search_text)
        pressure_class = extract_pressure_class(search_text)
        body_material = extract_body_material(search_text)
    elif category == "PUMP":
        cat_attrs, _ = extract_category_attributes(category, search_text)
        normalized_attributes = {
            "schema_version": "2.0",
            **cat_attrs
        }
        body_material = extract_body_material(search_text)
    elif category == "FASTENER":
        cat_attrs, _ = extract_category_attributes(category, search_text)
        normalized_attributes = {
            "schema_version": "2.0",
            **cat_attrs
        }
        body_material = extract_body_material(search_text)
    elif category == "BEARING":
        cat_attrs, _ = extract_category_attributes(category, search_text)
        normalized_attributes = {
            "schema_version": "2.0",
            **cat_attrs
        }
    elif category:
        cat_attrs, c_desc = extract_category_attributes(category, search_text)
        norm_desc = c_desc
        normalized_attributes = {
            "schema_version": "2.0",
            **cat_attrs
        }
        size = cat_attrs.get("size")
        pressure_class = cat_attrs.get("pressure_rating") or cat_attrs.get("pressure_class")
        body_material = cat_attrs.get("material_grade") or cat_attrs.get("casing_material")
        connection_type = cat_attrs.get("facing_connection") or extract_connection_type(search_text)
    else:
        normalized_attributes = {
            "schema_version": "2.0",
            "category": None
        }

    # Respect DB check constraint chk_material_category_valid:
    # Only assign material.category if in DB_ALLOWED_CATEGORIES; otherwise store None on column.
    db_category = category if category in DB_ALLOWED_CATEGORIES else None

    new_vals = {
        "category": db_category,
        "normalized_description": norm_desc,
        "normalized_uom": norm_uom,
        "valve_type": valve_type,
        "size": size,
        "pressure_class": pressure_class,
        "body_material": body_material,
        "connection_type": connection_type,
        "trim": trim,
        "normalized_attributes": normalized_attributes,
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
