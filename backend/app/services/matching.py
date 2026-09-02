import difflib
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models import Material, MatchRecommendation

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

def classify_match(source: Material, candidate: Material) -> Dict[str, Any]:
    """
    Compares two materials and returns classification, confidence, evidence, and explanation.
    """
    hard_conflicts = []
    matches = []
    missing_source = []
    missing_candidate = []
    missing_both = []

    evidence = {"attributes": {}}

    for attr in ATTRIBUTES:
        val1 = getattr(source, attr)
        val2 = getattr(candidate, attr)

        attr_ev = {"source": val1, "candidate": val2, "match": None, "weight": 0.0}

        if val1 is not None and val2 is not None:
            if val1 == val2:
                matches.append(attr.replace("_", " "))
                attr_ev["match"] = True
                attr_ev["weight"] = ATTR_WEIGHT
            else:
                hard_conflicts.append(f"{attr.replace('_', ' ')} conflict: {val1} vs {val2}")
                attr_ev["match"] = False
        else:
            if val1 is None and val2 is None:
                missing_both.append(attr.replace("_", " "))
            elif val1 is None:
                missing_source.append(attr.replace("_", " "))
            else:
                missing_candidate.append(attr.replace("_", " "))

        evidence["attributes"][attr] = attr_ev

    desc_sim = calculate_text_similarity(source.normalized_description or source.source_description,
                                         candidate.normalized_description or candidate.source_description)
    evidence["description_similarity"] = round(desc_sim, 3)

    if hard_conflicts:
        classification = "DIFFERENT"
        confidence = 0.0
        explanation = "; ".join(hard_conflicts).capitalize() + "."
    else:
        score = (len(matches) * ATTR_WEIGHT) + (desc_sim * DESC_WEIGHT)

        # Reward exact agreement on all known identity attributes.
        # If all 6 attributes match perfectly (meaning none are missing),
        # this is a complete technical equivalent. We ensure it reaches the SAME threshold.
        if len(matches) == len(ATTRIBUTES):
            score = max(score, 0.90)

        confidence = min(round(score, 3), 1.0)

        # Determine classification
        # We enforce that missing attributes intrinsically lower the score
        # (each missing attribute effectively docks 0.12 from the max 1.0).
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

    query = db.query(Material).filter(
        Material.id != source.id,
        Material.cpse_id != source.cpse_id,
        Material.category == source.category
    )

    # If source has a known valve type, only pull candidates with the same type or unknown type
    if source.valve_type:
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
    """
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
