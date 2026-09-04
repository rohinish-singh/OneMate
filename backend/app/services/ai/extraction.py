"""
AI Material Attribute Extraction & Understanding Service for OneMate.

Phase 3A: Shadow-mode extraction transforming industrial material descriptions
into structured semantic MaterialProfile objects with explicit 4-state uncertainty
(KNOWN_VALUE, UNKNOWN, NOT_PRESENT, CONFLICTING) and attribute-level confidence.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

from app.models import Material
from app.services.ai.profile import AttributeState, MaterialProfile, ProfileAttribute

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical Dictionaries & Lookup Tables
# ---------------------------------------------------------------------------

INCH_TO_DN = {
    "0.25": "DN8",
    "1/4": "DN8",
    "0.375": "DN10",
    "3/8": "DN10",
    "0.5": "DN15",
    "1/2": "DN15",
    "0.75": "DN20",
    "3/4": "DN20",
    "1": "DN25",
    "1.25": "DN32",
    "1-1/4": "DN32",
    "1 1/4": "DN32",
    "1.5": "DN40",
    "1-1/2": "DN40",
    "1 1/2": "DN40",
    "2": "DN50",
    "2.5": "DN65",
    "2-1/2": "DN65",
    "2 1/2": "DN65",
    "3": "DN80",
    "4": "DN100",
    "5": "DN125",
    "6": "DN150",
    "8": "DN200",
    "10": "DN250",
    "12": "DN300",
    "14": "DN350",
    "16": "DN400",
    "18": "DN450",
    "20": "DN500",
    "24": "DN600",
}

PRESSURE_CLASS_CANONICAL = {
    "150": "CLASS150",
    "300": "CLASS300",
    "400": "CLASS400",
    "600": "CLASS600",
    "800": "CLASS800",
    "900": "CLASS900",
    "1500": "CLASS1500",
    "2500": "CLASS2500",
    "3000": "3000PSI",
    "6000": "6000PSI",
    "10000": "10000PSI",
}

BODY_MATERIAL_SYNONYMS = {
    "CARBON_STEEL": [
        r"\bCARBON\s+STEEL\b",
        r"\bC\.S\.\b",
        r"\bCS\b",
        r"\bWCB\b",
        r"\bA216[\s\-]*WCB\b",
        r"\bCAST\s+STEEL\b",
        r"\bA105\b",
        r"\bFORGED\s+STEEL\b",
    ],
    "SS316": [
        r"\bSS\s*316L?\b",
        r"\b316L?\s*SS\b",
        r"\bAISI\s*316\b",
        r"\bCF8M\b",
        r"\bA351[\s\-]*CF8M\b",
    ],
    "SS304": [
        r"\bSS\s*304L?\b",
        r"\b304L?\s*SS\b",
        r"\bAISI\s*304\b",
        r"\bCF8\b",
        r"\bA351[\s\-]*CF8\b",
    ],
    "STAINLESS_STEEL": [
        r"\bSTAINLESS\s+STEEL\b",
        r"\bSS\b",
    ],
    "CAST_IRON": [
        r"\bCAST\s+IRON\b",
        r"\bC\.I\.\b",
        r"\bCI\b",
    ],
}

VALVE_TYPE_SYNONYMS = {
    "GATE": [r"\bGATE\b", r"\bGT\s+VLV\b"],
    "BALL": [r"\bBALL\b", r"\bBL\s+VLV\b"],
    "GLOBE": [r"\bGLOBE\b", r"\bGLB\b"],
    "CHECK": [r"\bCHECK\b", r"\bCHK\s+VLV\b", r"\bNRV\b"],
    "NEEDLE": [r"\bNEEDLE\b", r"\bNDL\b"],
    "BUTTERFLY": [r"\bBUTTERFLY\b", r"\bBFV\b"],
    "PLUG": [r"\bPLUG\b"],
    "DIAPHRAGM": [r"\bDIAPHRAGM\b"],
}

VALVE_TYPES = list(VALVE_TYPE_SYNONYMS.keys())

CONNECTION_SYNONYMS = {
    "RF": [r"\bRAISED\s+FACE\b", r"\bRF\b"],
    "SOCKET_WELD": [r"\bSOCKET\s+WELD(?:ED)?\b", r"\bSW\b"],
    "BUTT_WELD": [r"\bBUTT\s+WELD(?:ED)?\b", r"\bBW\b"],
    "NPT": [r"\bTHREADED\s+NPT\b", r"\bSCREWED\s+NPT\b", r"\bNPT\b"],
    "THREADED": [r"\bTHREADED\b", r"\bSCREWED\b", r"\bBSPT\b", r"\bBSPP\b"],
    "FLANGED": [r"\bFLANGED\b", r"\bFLANGE\b"],
}

CATEGORY_SYNONYMS = {
    "VALVE": [r"\bVALVE\b", r"\bVALVES\b", r"\bVLV\b", r"\bVLVS\b"],
    "PUMP": [r"\bCENTRIFUGAL\s+PUMP\b", r"\bVACUUM\s+PUMP\b", r"\bSUBMERSIBLE\s+PUMP\b", r"\bPUMP\b", r"\bPUMPS\b"],
    "GASKET": [r"\bSPIRAL\s+WOUND\s+GASKET\b", r"\bSPW\s+GASKET\b", r"\bRTJ\s+GASKET\b", r"\bSHEET\s+GASKET\b", r"\bGASKET\b", r"\bGASKETS\b"],
    "FLANGE": [r"\bWELD\s+NECK\s+FLANGE\b", r"\bWN\s+FLANGE\b", r"\bBLIND\s+FLANGE\b", r"\bSLIP\s+ON\s+FLANGE\b", r"\bSO\s+FLANGE\b", r"\bFLANGE\b", r"\bFLANGES\b"],
    "BEARING": [r"\bBALL\s+BEARING\b", r"\bROLLER\s+BEARING\b", r"\bNEEDLE\s+BEARING\b", r"\bBEARING\b", r"\bBEARINGS\b"],
    "FASTENER": [r"\bHEX\s+HEAD\s+BOLT\b", r"\bHEX\s+BOLT\b", r"\bSTUD\s+BOLT\b", r"\bCAP\s+SCREW\b", r"\bHEX\s+NUT\b", r"\bFASTENER\b", r"\bFASTENERS\b", r"\bWASHER\b"],
}

UOM_CANONICAL = {
    "EA": "EACH",
    "EACH": "EACH",
    "NOS": "EACH",
    "PCS": "EACH",
    "PIECE": "EACH",
    "PIECES": "EACH",
    "SET": "SET",
    "M": "METER",
    "MTR": "METER",
    "KG": "KG",
}


# ---------------------------------------------------------------------------
# Extractor Protocol & Concrete Implementation
# ---------------------------------------------------------------------------

class MaterialAttributeExtractor(Protocol):
    """Protocol for pluggable material attribute extraction components."""

    def extract(
        self,
        text: str,
        source_uom: Optional[str] = None,
        category_hint: Optional[str] = None,
    ) -> MaterialProfile:
        ...


class PatternMaterialExtractor:
    """
    Local, deterministic rule-augmented NLP material extractor.

    Understands:
    - Linguistic variations (word reordering, abbreviations, punctuation variants)
    - Uncertainty: explicitly distinguishes KNOWN_VALUE, UNKNOWN, NOT_PRESENT, CONFLICTING
    - Conflict detection: identifies self-contradictory mentions in descriptions
    - Confidence scoring: produces calibrated attribute-level confidence
    """

    def extract(
        self,
        text: str,
        source_uom: Optional[str] = None,
        category_hint: Optional[str] = None,
    ) -> MaterialProfile:
        clean_text = self._clean_input(text)

        # 1. Category extraction
        category_attr = self._extract_category(clean_text, category_hint)

        # 2. Trim extraction (isolated early to prevent confusing trim with body metallurgy)
        trim_attr, text_no_trim = self._extract_trim(clean_text)

        # 3. Valve type extraction
        valve_type_attr = self._extract_valve_type(text_no_trim, category_attr.value)

        # 4. Size extraction
        size_attr = self._extract_size(text_no_trim)

        # 5. Pressure rating extraction
        pressure_attr = self._extract_pressure(text_no_trim)

        # 6. Body material / metallurgy extraction
        body_attr = self._extract_body_material(text_no_trim, trim_attr)

        # 7. Connection type extraction
        connection_attr = self._extract_connection_type(text_no_trim)

        # 8. Normalized UOM extraction
        uom_attr = self._extract_uom(clean_text, source_uom)

        # Composite component type
        comp_type_val = None
        if category_attr.value == "VALVE" and valve_type_attr.is_known:
            comp_type_val = f"{valve_type_attr.value} VALVE"
        elif category_attr.is_known:
            comp_type_val = category_attr.value

        comp_attr = (
            ProfileAttribute.known(comp_type_val, confidence=category_attr.confidence)
            if comp_type_val
            else ProfileAttribute.not_present()
        )

        # Compute overall extraction confidence
        evaluated_attrs = [
            category_attr,
            valve_type_attr,
            size_attr,
            pressure_attr,
            body_attr,
            connection_attr,
        ]
        known_confs = [a.confidence for a in evaluated_attrs if a.is_known]
        overall_conf = round(sum(known_confs) / len(known_confs), 4) if known_confs else 0.0

        provenance = [
            a.raw_token for a in evaluated_attrs if a.raw_token is not None
        ]
        if trim_attr.raw_token:
            provenance.append(trim_attr.raw_token)

        return MaterialProfile(
            category=category_attr,
            material_type=valve_type_attr,
            component_type=comp_attr,
            size=size_attr,
            pressure_rating=pressure_attr,
            material_grade=body_attr,
            connection_type=connection_attr,
            trim_material=trim_attr,
            normalized_uom=uom_attr,
            extraction_confidence=overall_conf,
            provenance_tokens=provenance,
        )

    def _clean_input(self, text: str) -> str:
        if not text:
            return ""
        t = text.upper()
        t = re.sub(r"[\t\r\n]+", " ", t)
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    def _extract_category(self, text: str, category_hint: Optional[str]) -> ProfileAttribute:
        if category_hint and category_hint.upper() in CATEGORY_SYNONYMS:
            return ProfileAttribute.known(category_hint.upper(), raw_token=category_hint, confidence=1.0)

        # Check for explicit unknown
        if re.search(r"\b(?:CATEGORY|EQUIPMENT)\s*:\s*(?:UNKNOWN|UNSPECIFIED)\b", text):
            return ProfileAttribute.unknown(raw_token="CATEGORY: UNKNOWN")

        # Detect category candidates
        found_categories: Set[str] = set()
        matched_tokens: List[str] = []

        # Check bearings first to avoid "BALL BEARING" being categorized as "BALL VALVE"
        if re.search(r"\b(?:BALL|ROLLER|NEEDLE|TAPERED)?\s*BEARING\b", text):
            found_categories.add("BEARING")
            matched_tokens.append("BEARING")

        for cat, patterns in CATEGORY_SYNONYMS.items():
            if cat == "BEARING" and "BEARING" in found_categories:
                continue
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    found_categories.add(cat)
                    matched_tokens.append(m.group(0))
                    break

        if len(found_categories) > 1:
            return ProfileAttribute.conflicting(raw_token=" vs ".join(sorted(found_categories)))

        if len(found_categories) == 1:
            cat = list(found_categories)[0]
            return ProfileAttribute.known(cat, raw_token=matched_tokens[0] if matched_tokens else cat, confidence=0.95)

        return ProfileAttribute.not_present()

    def _extract_valve_type(self, text: str, category: Optional[str]) -> ProfileAttribute:
        if category and category != "VALVE":
            return ProfileAttribute.not_present()

        if re.search(r"\b(?:VALVE\s+TYPE|TYPE)\s*:\s*(?:UNKNOWN|UNSPECIFIED)\b", text):
            return ProfileAttribute.unknown(raw_token="TYPE: UNKNOWN")

        found_types: List[str] = []
        found_tokens: List[str] = []

        for vtype, patterns in VALVE_TYPE_SYNONYMS.items():
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    # Disambiguate "BALL" in "BALL BEARING"
                    if vtype == "BALL" and re.search(r"\bBALL\s+BEARING\b", text):
                        continue
                    # Disambiguate "NEEDLE" in "NEEDLE BEARING"
                    if vtype == "NEEDLE" and re.search(r"\bNEEDLE\s+BEARING\b", text):
                        continue
                    found_types.append(vtype)
                    found_tokens.append(m.group(0))
                    break

        if len(found_types) > 1:
            return ProfileAttribute.conflicting(raw_token=" vs ".join(found_tokens))
        elif len(found_types) == 1:
            return ProfileAttribute.known(found_types[0], raw_token=found_tokens[0], confidence=0.95)

        return ProfileAttribute.not_present()

    def _extract_size(self, text: str) -> ProfileAttribute:
        if re.search(r"\b(?:SIZE|DIMENSION|DIAMETER|NB)\s*:\s*(?:UNKNOWN|UNSPECIFIED)\b", text):
            return ProfileAttribute.unknown(raw_token="SIZE: UNKNOWN")

        candidates: List[Tuple[str, str]] = []

        # 1. DN xx
        for m in re.finditer(r"\bDN\s*(\d+)(?:\b|(?=[\s,;/\-]|$))", text):
            val = f"DN{m.group(1)}"
            candidates.append((val, m.group(0)))

        # 2. xx MM
        for m in re.finditer(r"\b(\d+)\s*MM(?:\b|(?=[\s,;/\-]|$))", text):
            mm_val = m.group(1)
            candidates.append((f"DN{mm_val}", m.group(0)))

        # 3. Fractional and Decimal Inches (e.g. 1/2", 1/2 IN, 2", 2 INCH, 2-IN)
        for m in re.finditer(r"\b((?:\d+[\s\-]*)?\d+/\d+|\d+(?:\.\d+)?)\s*(?:INCH|INCHES|IN|\"|-IN)(?:\b|(?=[\s,;/\-]|$))", text):
            raw_str = m.group(1).replace(" ", "-")
            canonical = INCH_TO_DN.get(raw_str)
            if canonical:
                candidates.append((canonical, m.group(0)))

        if not candidates:
            return ProfileAttribute.not_present()

        unique_canonicals = list(dict.fromkeys(c[0] for c in candidates))
        if len(unique_canonicals) > 1:
            conflicts = " vs ".join(f"{c[1]} ({c[0]})" for c in candidates)
            return ProfileAttribute.conflicting(raw_token=conflicts)

        return ProfileAttribute.known(candidates[0][0], raw_token=candidates[0][1], confidence=0.92)

    def _extract_pressure(self, text: str) -> ProfileAttribute:
        if re.search(r"\b(?:PRESSURE|RATING|CLASS)\s*:\s*(?:UNKNOWN|UNRATED|UNSPECIFIED)\b", text):
            return ProfileAttribute.unknown(raw_token="PRESSURE: UNKNOWN")

        candidates: List[Tuple[str, str]] = []

        # 1. Class / CL xx
        for m in re.finditer(r"\b(?:CLASS|CL)\s*(\d+)(?:\b|(?=[\s,;/\-]|$))", text):
            val = m.group(1)
            canon = PRESSURE_CLASS_CANONICAL.get(val, f"CLASS{val}")
            candidates.append((canon, m.group(0)))

        # 2. xx# or xx LBS
        for m in re.finditer(r"\b(\d+)\s*(?:#|LBS|LB)(?:\b|(?=[\s,;/\-]|$))", text):
            val = m.group(1)
            canon = PRESSURE_CLASS_CANONICAL.get(val, f"CLASS{val}")
            candidates.append((canon, m.group(0)))

        # 3. xx PSI
        for m in re.finditer(r"\b(\d+)\s*PSI(?:\b|(?=[\s,;/\-]|$))", text):
            val = m.group(1)
            candidates.append((f"{val}PSI", m.group(0)))

        if not candidates:
            return ProfileAttribute.not_present()

        unique_canonicals = list(dict.fromkeys(c[0] for c in candidates))
        if len(unique_canonicals) > 1:
            conflicts = " vs ".join(c[1] for c in candidates)
            return ProfileAttribute.conflicting(raw_token=conflicts)

        return ProfileAttribute.known(candidates[0][0], raw_token=candidates[0][1], confidence=0.92)

    def _extract_body_material(
        self,
        text: str,
        trim_attr: ProfileAttribute,
    ) -> ProfileAttribute:
        if re.search(r"\b(?:BODY|MATERIAL|METALLURGY)\s*:\s*(?:UNKNOWN|UNSPECIFIED)\b", text):
            return ProfileAttribute.unknown(raw_token="BODY: UNKNOWN")

        work_text = text
        if trim_attr.raw_token:
            work_text = work_text.replace(trim_attr.raw_token, " ")

        detected: List[Tuple[str, str]] = []

        for grade in ["CARBON_STEEL", "SS316", "SS304", "CAST_IRON"]:
            for pat in BODY_MATERIAL_SYNONYMS[grade]:
                m = re.search(pat, work_text)
                if m:
                    detected.append((grade, m.group(0)))
                    break

        if not any(d[0] in ["SS316", "SS304"] for d in detected):
            for pat in BODY_MATERIAL_SYNONYMS["STAINLESS_STEEL"]:
                m = re.search(pat, work_text)
                if m:
                    detected.append(("STAINLESS_STEEL", m.group(0)))
                    break

        if not detected:
            return ProfileAttribute.not_present()

        unique_grades = list(dict.fromkeys(d[0] for d in detected))
        if len(unique_grades) > 1:
            conflicts = " vs ".join(d[1] for d in detected)
            return ProfileAttribute.conflicting(raw_token=conflicts)

        return ProfileAttribute.known(detected[0][0], raw_token=detected[0][1], confidence=0.90)

    def _extract_connection_type(self, text: str) -> ProfileAttribute:
        if re.search(r"\b(?:CONNECTION|END|ENDS)\s*:\s*(?:UNKNOWN|UNSPECIFIED)\b", text):
            return ProfileAttribute.unknown(raw_token="CONNECTION: UNKNOWN")

        detected: List[Tuple[str, str]] = []

        for conn, patterns in CONNECTION_SYNONYMS.items():
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    detected.append((conn, m.group(0)))
                    break

        if not detected:
            return ProfileAttribute.not_present()

        unique_conns = list(dict.fromkeys(d[0] for d in detected))
        if len(unique_conns) > 1:
            conflicts = " vs ".join(d[1] for d in detected)
            return ProfileAttribute.conflicting(raw_token=conflicts)

        return ProfileAttribute.known(detected[0][0], raw_token=detected[0][1], confidence=0.90)

    def _extract_trim(self, text: str) -> Tuple[ProfileAttribute, str]:
        match_trim = re.search(r"\bTRIM\s+(SS\s*304|304\s*SS|304|SS\s*316|316\s*SS|316|13CR|STELLITE)\b", text)
        if match_trim:
            raw = match_trim.group(1)
            canon = self._canonical_trim(raw)
            remaining = text[:match_trim.start()] + text[match_trim.end():]
            return ProfileAttribute.known(canon, raw_token=match_trim.group(0), confidence=0.92), remaining

        match_trim_post = re.search(r"\b(SS\s*304|304\s*SS|304|SS\s*316|316\s*SS|316|13CR)\s+TRIM\b", text)
        if match_trim_post:
            raw = match_trim_post.group(1)
            canon = self._canonical_trim(raw)
            remaining = text[:match_trim_post.start()] + text[match_trim_post.end():]
            return ProfileAttribute.known(canon, raw_token=match_trim_post.group(0), confidence=0.92), remaining

        return ProfileAttribute.not_present(), text

    def _canonical_trim(self, raw: str) -> str:
        r = raw.upper().replace(" ", "")
        if "316" in r:
            return "SS316"
        if "304" in r:
            return "SS304"
        return r

    def _extract_uom(self, text: str, source_uom: Optional[str]) -> ProfileAttribute:
        if source_uom:
            clean = source_uom.strip().upper()
            canon = UOM_CANONICAL.get(clean)
            if canon:
                return ProfileAttribute.known(canon, raw_token=source_uom, confidence=1.0)

        match = re.search(r"\b(?:UOM|UNIT)\s*:\s*([A-Z]+)\b", text)
        if match:
            clean = match.group(1)
            canon = UOM_CANONICAL.get(clean)
            if canon:
                return ProfileAttribute.known(canon, raw_token=match.group(0), confidence=0.85)

        return ProfileAttribute.not_present()


# ---------------------------------------------------------------------------
# Profile Comparison Engine (Deterministic vs AI Extraction)
# ---------------------------------------------------------------------------

@dataclass
class ProfileComparisonReport:
    """Side-by-side diagnostic comparison between deterministic normalization and AI extraction."""
    material_id: Optional[uuid.UUID]
    source_description: str
    agreed_attributes: Dict[str, str] = field(default_factory=dict)
    disagreed_attributes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ai_only_extracted: Dict[str, str] = field(default_factory=dict)
    deterministic_only_extracted: Dict[str, str] = field(default_factory=dict)
    ai_uncertain_or_conflicting: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    agreement_score: float = 0.0
    deterministic_profile: Dict[str, Any] = field(default_factory=dict)
    ai_profile: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": str(self.material_id) if self.material_id else None,
            "source_description": self.source_description,
            "agreement_score": round(self.agreement_score, 4),
            "summary": {
                "agreed_count": len(self.agreed_attributes),
                "disagreed_count": len(self.disagreed_attributes),
                "ai_only_count": len(self.ai_only_extracted),
                "deterministic_only_count": len(self.deterministic_only_extracted),
                "ai_uncertain_count": len(self.ai_uncertain_or_conflicting),
            },
            "agreed_attributes": self.agreed_attributes,
            "disagreed_attributes": self.disagreed_attributes,
            "ai_only_extracted": self.ai_only_extracted,
            "deterministic_only_extracted": self.deterministic_only_extracted,
            "ai_uncertain_or_conflicting": self.ai_uncertain_or_conflicting,
            "deterministic_profile": self.deterministic_profile,
            "ai_profile": self.ai_profile,
        }


def compare_material_profiles(
    material: Material,
    ai_profile: MaterialProfile,
) -> ProfileComparisonReport:
    """
    Compares the existing deterministic Material attributes against
    the hypothetical AI-extracted MaterialProfile.

    Pure diagnostic function: does NOT mutate database state or Material models.
    """
    det_profile = MaterialProfile.from_material(material)

    slots_mapping = [
        ("category", "category", getattr(material, "category", None)),
        ("valve_type", "material_type", getattr(material, "valve_type", None)),
        ("size", "size", getattr(material, "size", None)),
        ("pressure_class", "pressure_rating", getattr(material, "pressure_class", None)),
        ("body_material", "material_grade", getattr(material, "body_material", None)),
        ("connection_type", "connection_type", getattr(material, "connection_type", None)),
        ("trim", "trim_material", getattr(material, "trim", None)),
    ]

    agreed: Dict[str, str] = {}
    disagreed: Dict[str, Dict[str, Any]] = {}
    ai_only: Dict[str, str] = {}
    det_only: Dict[str, str] = {}
    uncertain: Dict[str, Dict[str, Any]] = {}

    for slot_name, ai_slot_name, det_val in slots_mapping:
        ai_attr: ProfileAttribute = getattr(ai_profile, ai_slot_name)

        if ai_attr.state in (AttributeState.UNKNOWN, AttributeState.CONFLICTING):
            uncertain[slot_name] = {
                "state": ai_attr.state.value,
                "raw_token": ai_attr.raw_token,
            }

        d_has_val = bool(det_val)
        ai_has_val = ai_attr.is_known and ai_attr.value is not None

        if d_has_val and ai_has_val:
            if det_val == ai_attr.value:
                agreed[slot_name] = det_val
            else:
                disagreed[slot_name] = {
                    "deterministic": det_val,
                    "ai": ai_attr.value,
                    "ai_confidence": ai_attr.confidence,
                }
        elif ai_has_val and not d_has_val:
            ai_only[slot_name] = ai_attr.value
        elif d_has_val and not ai_has_val:
            det_only[slot_name] = det_val

    evaluated_count = len(agreed) + len(disagreed) + len(ai_only) + len(det_only)
    score = (len(agreed) / evaluated_count) if evaluated_count > 0 else 1.0

    return ProfileComparisonReport(
        material_id=material.id if hasattr(material, "id") else None,
        source_description=material.source_description or material.normalized_description or "",
        agreed_attributes=agreed,
        disagreed_attributes=disagreed,
        ai_only_extracted=ai_only,
        deterministic_only_extracted=det_only,
        ai_uncertain_or_conflicting=uncertain,
        agreement_score=score,
        deterministic_profile=det_profile.to_dict(),
        ai_profile=ai_profile.to_dict(),
    )

