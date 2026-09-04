import difflib
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models import Material, MatchRecommendation
from app.core.config import settings

logger = logging.getLogger(__name__)

SCORE_THRESHOLD_SAME = 0.88
SCORE_THRESHOLD_POTENTIAL = 0.45

ATTRIBUTES = [
    "valve_type",
    "size",
    "body_material",
    "pressure_class",
    "connection_type",
    "trim"
]

ATTR_WEIGHT = 0.12
DESC_WEIGHT = 0.28

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Returns a similarity ratio between 0.0 and 1.0 using difflib.
    Handles None values gracefully.
    """
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def format_list(items: List[str]) -> str:
    """Formats a list of strings into 'a, b and c'."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" and {items[-1]}"

CATEGORY_SCHEMAS: Dict[str, List[str]] = {
    "VALVE": ["valve_type", "size", "body_material", "pressure_class", "connection_type", "trim"],
    "STRAINER": ["type", "size", "pressure_rating", "material_grade", "mesh"],
    "PIPE": ["construction", "size", "schedule", "material_grade", "standard_grade"],
    "FLANGE": ["flange_type", "size", "pressure_rating", "material_grade", "facing_connection"],
    "GASKET": ["gasket_type", "size", "pressure_rating", "materials_filler"],
    "PUMP": ["pump_type", "flow_rate", "head", "casing_material"],
    "TRANSMITTER": ["instrument_type", "measurement_range", "signal", "protocol"],
    "O-RING": ["material_elastomer", "inner_diameter", "cross_section"],
    "FASTENER": ["type", "size", "length", "grade", "nut_specification"],
    "FITTING": ["fitting_type", "size", "schedule", "material_grade"],
    "MOTOR": ["motor_type", "phase", "power", "voltage", "speed", "efficiency"],
    "BEARING": ["bearing_type", "bearing_number", "seal_shield"],
    "BELT": ["belt_type", "profile", "length"],
}

CATEGORY_ATTRIBUTE_LABELS: Dict[str, Dict[str, str]] = {
    "VALVE": {
        "seat_material": "seat material",
    },
    "STRAINER": {
        "type": "strainer type",
        "pressure_rating": "pressure rating",
        "material_grade": "material grade",
    },
    "FASTENER": {
        "type": "fastener type",
    },
}

ATTRIBUTE_ALIASES: Dict[str, List[str]] = {
    "pressure_rating": ["pressure_class"],
    "pressure_class": ["pressure_rating"],
    "material_grade": ["body_material", "casing_material"],
    "body_material": ["material_grade"],
    "casing_material": ["material_grade", "body_material"],
    "valve_type": ["type", "material_type"],
    "type": ["valve_type", "material_type"],
    "facing_connection": ["connection_type"],
    "connection_type": ["facing_connection"],
    "trim": ["trim_material"],
    "trim_material": ["trim"],
    "seat_material": ["liner_material"],
    "liner_material": ["seat_material"],
}

def get_material_category(mat: Optional[Material]) -> Optional[str]:
    """Extracts category from material column or normalized_attributes JSONB."""
    if not mat:
        return None
    if mat.category:
        return str(mat.category).strip().upper()
    norm_attrs = getattr(mat, "normalized_attributes", None)
    if isinstance(norm_attrs, dict) and norm_attrs.get("category"):
        return str(norm_attrs["category"]).strip().upper()
    return None

def get_material_attribute(mat: Material, attr: str) -> Optional[str]:
    """Retrieves an attribute value from normalized_attributes or model columns with alias support."""
    raw_attrs = getattr(mat, "normalized_attributes", None) or {}
    if isinstance(raw_attrs, dict) and raw_attrs.get(attr) is not None:
        val = str(raw_attrs[attr]).strip()
        if val and val.upper() != "UNKNOWN":
            return val

    direct_val = getattr(mat, attr, None)
    if direct_val is not None:
        val = str(direct_val).strip()
        if val and val.upper() != "UNKNOWN":
            return val

    for alias in ATTRIBUTE_ALIASES.get(attr, []):
        if isinstance(raw_attrs, dict) and raw_attrs.get(alias) is not None:
            val = str(raw_attrs[alias]).strip()
            if val and val.upper() != "UNKNOWN":
                return val
        alias_val = getattr(mat, alias, None)
        if alias_val is not None:
            val = str(alias_val).strip()
            if val and val.upper() != "UNKNOWN":
                return val

    return None

def canonicalize_value(attr: str, val: Optional[str]) -> Optional[str]:
    """Canonicalizes standard engineering values for comparison."""
    if not val:
        return None
    val_str = str(val).strip().upper()
    if attr in ("size", "inner_diameter", "cross_section"):
        from app.services.ai.validation import EngineeringKnowledgeEngine
        return EngineeringKnowledgeEngine.canonicalize_size(val_str)
    if attr in ("pressure_class", "pressure_rating"):
        from app.services.ai.validation import EngineeringKnowledgeEngine
        return EngineeringKnowledgeEngine.canonicalize_pressure(val_str)
    if attr in ("body_material", "material_grade", "casing_material", "trim", "trim_material"):
        from app.services.ai.validation import EngineeringKnowledgeEngine
        return EngineeringKnowledgeEngine.canonicalize_metallurgy(val_str)
    if attr in ("seat_material", "liner_material"):
        from app.services.normalization import normalize_seat_material
        return normalize_seat_material(val_str)
    return val_str

def classify_match(source: Material, candidate: Material) -> Dict[str, Any]:
    """
    Compares two materials and returns classification, confidence, evidence, and explanation.
    Uses category-aware schema comparisons and engineering canonicalization.
    """
    desc_sim = calculate_text_similarity(
        source.normalized_description or source.source_description,
        candidate.normalized_description or candidate.source_description
    )

    cat_src = get_material_category(source)
    cat_cand = get_material_category(candidate)

    # Equipment category check
    if cat_src and cat_cand and cat_src != cat_cand:
        return {
            "classification": "DIFFERENT",
            "confidence": 0.0,
            "evidence": {
                "attributes": {},
                "description_similarity": round(desc_sim, 3),
                "category_conflict": f"Category mismatch: {cat_src} vs {cat_cand}",
            },
            "explanation": f"Category conflict: {cat_src} vs {cat_cand}."
        }

    primary_cat = cat_src or cat_cand
    if primary_cat and primary_cat in CATEGORY_SCHEMAS:
        attrs_to_compare = list(CATEGORY_SCHEMAS[primary_cat])
    else:
        attrs_to_compare = list(ATTRIBUTES)

    # If category is VALVE and either source or candidate specifies seat_material,
    # evaluate seat_material as an engineering attribute.
    if primary_cat == "VALVE":
        s_seat = get_material_attribute(source, "seat_material")
        c_seat = get_material_attribute(candidate, "seat_material")
        if s_seat is not None or c_seat is not None:
            if "seat_material" not in attrs_to_compare:
                attrs_to_compare.append("seat_material")
            s_trim = get_material_attribute(source, "trim")
            c_trim = get_material_attribute(candidate, "trim")
            if s_trim is None and c_trim is None and "trim" in attrs_to_compare:
                attrs_to_compare.remove("trim")

    hard_conflicts = []
    matches = []
    missing_source = []
    missing_candidate = []
    missing_both = []

    evidence = {"attributes": {}}
    attr_weight = round(0.72 / len(attrs_to_compare), 4) if attrs_to_compare else 0.12

    for attr in attrs_to_compare:
        label = CATEGORY_ATTRIBUTE_LABELS.get(primary_cat or "", {}).get(attr, attr.replace("_", " "))
        val1 = get_material_attribute(source, attr)
        val2 = get_material_attribute(candidate, attr)

        attr_ev = {"source": val1, "candidate": val2, "match": None, "weight": 0.0}

        if val1 is not None and val2 is not None:
            c1 = canonicalize_value(attr, val1)
            c2 = canonicalize_value(attr, val2)
            if c1 == c2:
                matches.append(label)
                attr_ev["match"] = True
                attr_ev["weight"] = attr_weight
            else:
                hard_conflicts.append(f"{label} conflict: {val1} vs {val2}")
                attr_ev["match"] = False
        else:
            if val1 is None and val2 is None:
                missing_both.append(label)
            elif val1 is None:
                missing_source.append(label)
            else:
                missing_candidate.append(label)

        evidence["attributes"][attr] = attr_ev

    evidence["description_similarity"] = round(desc_sim, 3)

    if hard_conflicts:
        classification = "DIFFERENT"
        confidence = 0.0
        parts = []
        if matches:
            parts.append(f"Same {format_list(matches)}")
        parts.extend(hard_conflicts)
        explanation = "; ".join(parts).capitalize() + "."
    else:
        score = (len(matches) * attr_weight) + (desc_sim * DESC_WEIGHT)

        # Reward exact agreement on all known identity attributes in schema.
        if len(matches) == len(attrs_to_compare) and len(attrs_to_compare) > 0:
            score = max(score, 0.90)

        confidence = min(round(score, 3), 1.0)

        # Determine classification
        if confidence >= SCORE_THRESHOLD_SAME:
            if missing_source or missing_candidate or missing_both:
                classification = "POTENTIALLY_EQUIVALENT"
            else:
                classification = "SAME"
        elif confidence >= SCORE_THRESHOLD_POTENTIAL:
            classification = "POTENTIALLY_EQUIVALENT"
        else:
            classification = "DIFFERENT"

        # Formulate explanation
        parts = []
        if matches:
            parts.append(f"Same {format_list(matches)}")

        missing_all = missing_source + missing_candidate + missing_both
        if missing_all:
            parts.append(f"missing information for {format_list(missing_all)}")

        if not matches and not missing_all:
            explanation = "No attribute evidence available."
        else:
            explanation = "; ".join(parts).capitalize() + "."

    return {
        "classification": classification,
        "confidence": confidence,
        "evidence": evidence,
        "explanation": explanation
    }

def generate_candidates(db: Session, source: Material) -> List[Material]:
    """
    Generates plausible candidates for matching.
    Avoids cross-comparing the exact same CPSE and entirely incompatible base types.
    Enforces candidate.id != source.id and candidate.cpse_id != source.cpse_id.
    """
    if not source or source.cpse_id is None:
        return []

    src_cat = get_material_category(source)

    query = db.query(Material).filter(
        Material.id != source.id,
        Material.cpse_id != source.cpse_id,
    )

    if src_cat:
        query = query.filter(
            (Material.category == src_cat) |
            (Material.normalized_attributes["category"].astext == src_cat)
        )
    else:
        query = query.filter(Material.category.is_(None))

    # If source has a known valve type, only pull candidates with the same type or unknown type
    if getattr(source, "valve_type", None):
        query = query.filter(
            (Material.valve_type == source.valve_type) | (Material.valve_type.is_(None))
        )

    candidates = query.all()

    # Enforce backend candidate-selection invariants before returning
    return [
        cand for cand in candidates
        if cand.id != source.id and cand.cpse_id != source.cpse_id
    ]

def create_match_recommendations(db: Session, source_material: Material) -> List[MatchRecommendation]:
    """
    Executes the matching pipeline for a source material and persists recommendations.
    Returns the created MatchRecommendation objects.

    When settings.ai_hybrid_retrieval_enabled is False (default):
        Uses baseline deterministic candidate retrieval exclusively.
    When settings.ai_hybrid_retrieval_enabled is True:
        Uses baseline candidates UNION AI semantic candidates deduplicated.
        If AI retrieval fails, safely falls back to baseline retrieval.
    """
    if getattr(settings, "ai_hybrid_retrieval_enabled", False):
        try:
            from app.services.ai.shadow import generate_hybrid_candidates
            hybrid_candidates, _ = generate_hybrid_candidates(
                db=db,
                source=source_material,
                top_k=getattr(settings, "candidate_retrieval_top_k", 15),
                min_similarity=getattr(settings, "candidate_similarity_threshold", 0.50),
                category_filter=True,
            )
            candidates = [c.material for c in hybrid_candidates]
        except Exception as e:
            logger.warning(
                f"AI hybrid candidate retrieval failed for material {source_material.id}: {e}; "
                f"falling back to baseline deterministic candidate retrieval."
            )
            candidates = generate_candidates(db, source_material)
    else:
        candidates = generate_candidates(db, source_material)

    recommendations = []

    for cand in candidates:
        if cand.id == source_material.id or cand.cpse_id == source_material.cpse_id:
            continue

        result = classify_match(source_material, cand)

        rec = MatchRecommendation(
            source_material_id=source_material.id,
            candidate_material_id=cand.id,
            classification=result["classification"],
            confidence=result["confidence"],
            evidence=result["evidence"],
            explanation=result["explanation"]
        )
        recommendations.append(rec)
        db.add(rec)

    db.flush()
    return recommendations
