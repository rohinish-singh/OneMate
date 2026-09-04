"""
AI Explainability & Reviewer Intelligence Engine for OneMate.

Phase 4: Structured evidence generation for human reviewers and audit trails.
AI explains evidence; engineering rules enforce correctness; humans govern uncertainty.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models import Material
from app.services.ai.embedding import EmbeddingService, cosine_similarity
from app.services.ai.profile import MaterialProfile
from app.services.ai.retrieval import get_material_search_text
from app.services.ai.validation import (
    EngineeringKnowledgeEngine,
    ValidationResult,
)
from app.services.matching import classify_match

logger = logging.getLogger(__name__)


@dataclass
class AttributeComparisonItem:
    """Individual attribute comparison between source and candidate."""
    attribute: str
    source_value: Optional[str]
    candidate_value: Optional[str]
    status: str  # MATCH | CONFLICT | MISSING | UNKNOWN | NOT_APPLICABLE
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attribute": self.attribute,
            "source_value": self.source_value,
            "candidate_value": self.candidate_value,
            "status": self.status,
            "evidence": self.evidence,
        }


@dataclass
class EngineeringConflictItem:
    """Authoritative physical or engineering conflict identified by EngineeringKnowledgeEngine."""
    attribute: str
    source: Optional[str]
    candidate: Optional[str]
    severity: str  # HARD
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attribute": self.attribute,
            "source": self.source,
            "candidate": self.candidate,
            "severity": self.severity,
            "reason": self.reason,
        }


@dataclass
class SemanticEvidence:
    """Quantitative semantic retrieval and reranking evidence."""
    semantic_similarity_score: float
    candidate_rank: Optional[int]
    retrieval_source: str  # BASELINE | AI_SEMANTIC | HYBRID | DIRECT_PAIR
    is_in_baseline: bool
    is_in_ai: bool
    is_reranked: bool
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "semantic_similarity_score": round(self.semantic_similarity_score, 4),
            "candidate_rank": self.candidate_rank,
            "retrieval_source": self.retrieval_source,
            "is_in_baseline": self.is_in_baseline,
            "is_in_ai": self.is_in_ai,
            "is_reranked": self.is_reranked,
            "summary": self.summary,
        }


@dataclass
class RecommendationExplanation:
    """
    Comprehensive structured explanation report for reviewer decision-making and audit trails.
    Combines AI semantic similarity, structured attribute comparisons, and authoritative engineering rules.
    """
    source_material_id: str
    candidate_material_id: str
    source_code: str
    candidate_code: str
    source_description: str
    candidate_description: str
    classification: str  # SAME | POTENTIALLY_EQUIVALENT | DIFFERENT
    confidence: float
    recommended_action: str  # AUTO_SAFE | REVIEW_REQUIRED | REJECT
    why_considered: str
    safety_assessment: str
    matching_attributes: List[str]
    conflicting_attributes: List[str]
    unknown_or_missing_attributes: List[str]
    attribute_comparisons: List[AttributeComparisonItem]
    engineering_conflicts: List[EngineeringConflictItem]
    semantic_evidence: SemanticEvidence
    audit_trail: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_material_id": self.source_material_id,
            "candidate_material_id": self.candidate_material_id,
            "source_code": self.source_code,
            "candidate_code": self.candidate_code,
            "source_description": self.source_description,
            "candidate_description": self.candidate_description,
            "classification": self.classification,
            "confidence": round(self.confidence, 4),
            "recommended_action": self.recommended_action,
            "why_considered": self.why_considered,
            "safety_assessment": self.safety_assessment,
            "matching_attributes": self.matching_attributes,
            "conflicting_attributes": self.conflicting_attributes,
            "unknown_or_missing_attributes": self.unknown_or_missing_attributes,
            "attribute_comparisons": [a.to_dict() for a in self.attribute_comparisons],
            "engineering_conflicts": [e.to_dict() for e in self.engineering_conflicts],
            "semantic_evidence": self.semantic_evidence.to_dict(),
            "audit_trail": self.audit_trail,
            "error": self.error,
        }


class MaterialExplanationService:
    """
    Generates structured reviewer intelligence reports for material pairs.
    Purely deterministic & explainable: does not call external LLMs or mutate database records.
    """

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService.get_instance()

    def generate_explanation(
        self,
        source: Material,
        candidate: Material,
        candidate_rank: Optional[int] = None,
        retrieval_source: str = "DIRECT_PAIR",
        is_in_baseline: bool = True,
        is_in_ai: bool = False,
        is_reranked: bool = False,
    ) -> RecommendationExplanation:
        """
        Generates structured explanation from deterministic classification,
        engineering knowledge engine rules, and semantic embeddings.
        """
        try:
            # 1. Authoritative deterministic classification
            match_res = classify_match(source, candidate)
            classification = match_res["classification"]
            confidence = match_res["confidence"]

            # 2. Authoritative engineering validation
            val_res: ValidationResult = EngineeringKnowledgeEngine.validate_materials(source, candidate)

            # 3. Dense semantic similarity calculation
            sem_score, sem_summary = self._compute_semantic_evidence(source, candidate, val_res, classification)

            # 4. Attribute-by-attribute structured comparisons
            comparisons, matches, conflicts, missing = self._build_attribute_comparisons(source, candidate, val_res)

            # 5. Extract structured engineering conflicts
            eng_conflicts = self._extract_engineering_conflicts(source, candidate, val_res)

            # 6. Synthesize recommended reviewer action
            recommended_action = self._determine_recommended_action(classification, confidence, eng_conflicts)

            # 7. Synthesize why candidate was considered
            why_considered = self._determine_why_considered(source, candidate, sem_score, retrieval_source)

            # 8. Synthesize safety assessment
            safety_assessment = self._determine_safety_assessment(classification, eng_conflicts, missing)

            # 9. Build reproducible deterministic audit trail metadata
            audit_trail = self._build_audit_trail(source, candidate, classification, confidence)

            sem_evidence = SemanticEvidence(
                semantic_similarity_score=sem_score,
                candidate_rank=candidate_rank,
                retrieval_source=retrieval_source,
                is_in_baseline=is_in_baseline,
                is_in_ai=is_in_ai,
                is_reranked=is_reranked,
                summary=sem_summary,
            )

            return RecommendationExplanation(
                source_material_id=str(source.id),
                candidate_material_id=str(candidate.id),
                source_code=source.source_material_code,
                candidate_code=candidate.source_material_code,
                source_description=source.source_description or source.normalized_description or "",
                candidate_description=candidate.source_description or candidate.normalized_description or "",
                classification=classification,
                confidence=confidence,
                recommended_action=recommended_action,
                why_considered=why_considered,
                safety_assessment=safety_assessment,
                matching_attributes=matches,
                conflicting_attributes=conflicts,
                unknown_or_missing_attributes=missing,
                attribute_comparisons=comparisons,
                engineering_conflicts=eng_conflicts,
                semantic_evidence=sem_evidence,
                audit_trail=audit_trail,
            )

        except Exception as e:
            logger.error(f"Error generating material explanation: {e}", exc_info=True)
            # Safe degradation: preserve deterministic classification and report error
            fallback_match = classify_match(source, candidate)
            return RecommendationExplanation(
                source_material_id=str(source.id),
                candidate_material_id=str(candidate.id),
                source_code=source.source_material_code,
                candidate_code=candidate.source_material_code,
                source_description=source.source_description or "",
                candidate_description=candidate.source_description or "",
                classification=fallback_match["classification"],
                confidence=fallback_match["confidence"],
                recommended_action="REVIEW_REQUIRED",
                why_considered="Direct candidate evaluation.",
                safety_assessment="Explanation fallback: deterministic classifier active; detailed AI synthesis degraded.",
                matching_attributes=[],
                conflicting_attributes=[],
                unknown_or_missing_attributes=[],
                attribute_comparisons=[],
                engineering_conflicts=[],
                semantic_evidence=SemanticEvidence(
                    semantic_similarity_score=0.0,
                    candidate_rank=None,
                    retrieval_source=retrieval_source,
                    is_in_baseline=is_in_baseline,
                    is_in_ai=is_in_ai,
                    is_reranked=is_reranked,
                    summary="Semantic computation unavailable; safe fallback active.",
                ),
                audit_trail={"engine_version": "OneMate-AI-v4.0-fallback", "error": str(e)},
                error=str(e),
            )

    def _compute_semantic_evidence(
        self,
        source: Material,
        candidate: Material,
        val_res: ValidationResult,
        classification: str,
    ) -> tuple[float, str]:
        src_text = get_material_search_text(source)
        cand_text = get_material_search_text(candidate)

        vec_src = self.embedding_service.encode_one(src_text)
        vec_cand = self.embedding_service.encode_one(cand_text)

        score = float(cosine_similarity(vec_src, vec_cand))

        if val_res.hard_conflicts:
            summary = (
                f"AI semantic similarity is {score:.2f}, but deterministic engineering rules detected "
                f"{len(val_res.hard_conflicts)} physical conflict(s). Semantic similarity does not equal engineering equivalence."
            )
        elif classification == "SAME":
            summary = f"High semantic similarity ({score:.2f}) confirmed with full technical attribute agreement and zero conflicts."
        elif classification == "POTENTIALLY_EQUIVALENT":
            summary = (
                f"Moderate-to-high semantic similarity ({score:.2f}) with compatible known attributes, "
                f"but missing specifications require human reviewer confirmation."
            )
        else:
            summary = f"Low-to-moderate semantic similarity ({score:.2f}) with insufficient attribute agreement."

        return score, summary

    def _build_attribute_comparisons(
        self,
        source: Material,
        candidate: Material,
        val_res: ValidationResult,
    ) -> tuple[List[AttributeComparisonItem], List[str], List[str], List[str]]:
        from app.services.matching import get_material_category, get_material_attribute, CATEGORY_SCHEMAS

        cat = get_material_category(source) or get_material_category(candidate)
        schema_attrs = CATEGORY_SCHEMAS.get(cat or "", None)

        if schema_attrs:
            attributes_to_check = [("category", "category")]
            for a in schema_attrs:
                slot = a
                if a == "type": slot = "material_type"
                elif a == "pressure_rating": slot = "pressure_rating"
                elif a == "material_grade": slot = "material_grade"
                elif a == "facing_connection": slot = "connection_type"
                elif a == "trim": slot = "trim_material"
                elif a == "seat_material": slot = "seat_material"
                attributes_to_check.append((a, slot))
            if cat == "VALVE":
                s_seat = get_material_attribute(source, "seat_material")
                c_seat = get_material_attribute(candidate, "seat_material")
                if (s_seat is not None or c_seat is not None) and not any(f == "seat_material" for f, _ in attributes_to_check):
                    attributes_to_check.append(("seat_material", "seat_material"))
            attributes_to_check.append(("normalized_uom", "normalized_uom"))
        else:
            attributes_to_check = [
                ("category", "category"),
                ("valve_type", "material_type"),
                ("size", "size"),
                ("pressure_class", "pressure_rating"),
                ("body_material", "material_grade"),
                ("connection_type", "connection_type"),
                ("trim", "trim_material"),
                ("source_uom", "normalized_uom"),
            ]
            s_seat = get_material_attribute(source, "seat_material")
            c_seat = get_material_attribute(candidate, "seat_material")
            if s_seat is not None or c_seat is not None:
                attributes_to_check.append(("seat_material", "seat_material"))

        comparisons: List[AttributeComparisonItem] = []
        matching_attrs: List[str] = []
        conflicting_attrs: List[str] = []
        missing_attrs: List[str] = []

        matrix = val_res.attribute_matrix

        s_attrs = getattr(source, "normalized_attributes", None) or {}
        c_attrs = getattr(candidate, "normalized_attributes", None) or {}

        checked_keys = set()
        for mat_field, profile_slot in attributes_to_check:
            checked_keys.add(mat_field)
            s_val = get_material_attribute(source, mat_field)
            c_val = get_material_attribute(candidate, mat_field)

            # Check if EngineeringKnowledgeEngine evaluated this slot
            matrix_entry = matrix.get(profile_slot) or matrix.get(mat_field)

            if matrix_entry:
                if matrix_entry.get("conflict"):
                    status = "CONFLICT"
                    evidence = f"Physical conflict: {s_val} vs {c_val}"
                    conflicting_attrs.append(mat_field)
                elif matrix_entry.get("match"):
                    status = "MATCH"
                    evidence = f"Confirmed match: {s_val}"
                    matching_attrs.append(mat_field)
                elif s_val is None or c_val is None:
                    status = "MISSING"
                    if s_val is None and c_val is None:
                        status = "UNKNOWN"
                        evidence = "Unspecified on both source and candidate"
                    elif s_val is None:
                        evidence = "Unspecified in source material"
                    else:
                        evidence = "Unspecified in candidate material"
                    missing_attrs.append(mat_field)
                else:
                    status = "NOT_APPLICABLE"
                    evidence = "Evaluated non-identity slot"
            else:
                # Direct evaluation
                if s_val is not None and c_val is not None:
                    if str(s_val).strip().upper() == str(c_val).strip().upper():
                        status = "MATCH"
                        evidence = f"Values match: {s_val}"
                        matching_attrs.append(mat_field)
                    else:
                        status = "CONFLICT"
                        evidence = f"Values differ: {s_val} vs {c_val}"
                        conflicting_attrs.append(mat_field)
                elif s_val is None and c_val is None:
                    status = "UNKNOWN"
                    evidence = "Unspecified on both materials"
                    missing_attrs.append(mat_field)
                else:
                    status = "MISSING"
                    evidence = f"Present in {'source' if s_val else 'candidate'}, missing in {'candidate' if s_val else 'source'}"
                    missing_attrs.append(mat_field)

            comparisons.append(AttributeComparisonItem(
                attribute=mat_field,
                source_value=s_val,
                candidate_value=c_val,
                status=status,
                evidence=evidence,
            ))

        # Check category-specific attributes from normalized_attributes
        extra_keys = set(s_attrs.keys()) | set(c_attrs.keys())
        # Filter out keys already compared or internal
        standard_keys = {
            "category", "valve_type", "type", "size", "pressure_class", "pressure_rating",
            "body_material", "material_grade", "connection_type", "facing_connection",
            "trim", "trim_material", "seat_material", "liner_material", "source_uom", "normalized_uom",
            "normalized_description", "schema_version", "additional_attributes", "extraction_confidence",
            "provenance_tokens", "component_type", "material_type"
        } | checked_keys

        for extra_key in sorted(extra_keys - standard_keys):
            s_extra = s_attrs.get(extra_key)
            c_extra = c_attrs.get(extra_key)
            if s_extra is not None and c_extra is not None:
                if str(s_extra).strip().upper() == str(c_extra).strip().upper():
                    status = "MATCH"
                    evidence = f"Values match: {s_extra}"
                    matching_attrs.append(extra_key)
                else:
                    status = "CONFLICT"
                    evidence = f"Values differ: {s_extra} vs {c_extra}"
                    conflicting_attrs.append(extra_key)
            elif s_extra is None and c_extra is None:
                status = "UNKNOWN"
                evidence = "Unspecified on both materials"
                missing_attrs.append(extra_key)
            else:
                status = "MISSING"
                evidence = f"Present in {'source' if s_extra else 'candidate'}, missing in {'candidate' if s_extra else 'source'}"
                missing_attrs.append(extra_key)

            comparisons.append(AttributeComparisonItem(
                attribute=extra_key,
                source_value=s_extra,
                candidate_value=c_extra,
                status=status,
                evidence=evidence,
            ))

        return comparisons, matching_attrs, conflicting_attrs, missing_attrs

    def _extract_engineering_conflicts(
        self,
        source: Material,
        candidate: Material,
        val_res: ValidationResult,
    ) -> List[EngineeringConflictItem]:
        from app.services.matching import get_material_attribute

        conflicts: List[EngineeringConflictItem] = []

        s_attrs = getattr(source, "normalized_attributes", None) or {}
        c_attrs = getattr(candidate, "normalized_attributes", None) or {}

        for conf_str in val_res.hard_conflicts:
            c_lower = conf_str.lower()
            if "category" in c_lower:
                attr = "category"
            elif "mesh" in c_lower:
                attr = "mesh"
            elif "seat" in c_lower or "liner" in c_lower:
                attr = "seat_material"
            elif "connection" in c_lower:
                attr = "connection_type"
            elif "type" in c_lower:
                attr = "type" if ("type" in s_attrs or "type" in c_attrs) else "valve_type"
            elif "size" in c_lower:
                attr = "size"
            elif "pressure" in c_lower:
                attr = "pressure_rating" if ("pressure_rating" in s_attrs or "pressure_rating" in c_attrs) else "pressure_class"
            elif "material" in c_lower or "metallurgy" in c_lower:
                attr = "material_grade" if ("material_grade" in s_attrs or "material_grade" in c_attrs) else "body_material"
            elif "trim" in c_lower:
                attr = "trim"
            else:
                attr = "general"

            conflicts.append(EngineeringConflictItem(
                attribute=attr,
                source=get_material_attribute(source, attr) or getattr(source, attr, None) or s_attrs.get(attr),
                candidate=get_material_attribute(candidate, attr) or getattr(candidate, attr, None) or c_attrs.get(attr),
                severity="HARD",
                reason=conf_str,
            ))

        # Check for conflicts in category-specific attributes (e.g., mesh conflict, seat_material conflict)
        for key in ["mesh", "seat_material", "schedule", "flow_rate", "head", "fitting_type", "bearing_number"]:
            if key in s_attrs and key in c_attrs:
                s_val = str(s_attrs[key]).strip().upper()
                c_val = str(c_attrs[key]).strip().upper()
                if s_val and c_val and s_val != c_val:
                    # Avoid duplicate if already logged
                    if not any(c.attribute == key for c in conflicts):
                        conflicts.append(EngineeringConflictItem(
                            attribute=key,
                            source=s_attrs[key],
                            candidate=c_attrs[key],
                            severity="HARD",
                            reason=f"Seat material conflict: {s_attrs[key]} vs {c_attrs[key]}" if key == "seat_material" else f"{key.capitalize()} specification conflict: {s_attrs[key]} vs {c_attrs[key]}",
                        ))
                c_val = str(c_attrs[key]).strip().upper()
                if s_val and c_val and s_val != c_val:
                    # Avoid duplicate if already logged
                    if not any(c.attribute == key for c in conflicts):
                        conflicts.append(EngineeringConflictItem(
                            attribute=key,
                            source=s_attrs[key],
                            candidate=c_attrs[key],
                            severity="HARD",
                            reason=f"{key.capitalize()} specification conflict: {s_attrs[key]} vs {c_attrs[key]}",
                        ))

        return conflicts

    def _determine_recommended_action(
        self,
        classification: str,
        confidence: float,
        eng_conflicts: List[EngineeringConflictItem],
    ) -> str:
        if classification == "SAME" and len(eng_conflicts) == 0 and confidence >= 0.90:
            return "AUTO_SAFE"
        elif classification == "POTENTIALLY_EQUIVALENT":
            return "REVIEW_REQUIRED"
        else:
            return "REJECT"

    def _determine_why_considered(
        self,
        source: Material,
        candidate: Material,
        sem_score: float,
        retrieval_source: str,
    ) -> str:
        cat = source.category or "VALVE"
        pct = int(sem_score * 100)
        return (
            f"Candidate retrieved via {retrieval_source} within category '{cat}' "
            f"exhibiting {pct}% dense semantic description similarity."
        )

    def _determine_safety_assessment(
        self,
        classification: str,
        eng_conflicts: List[EngineeringConflictItem],
        missing: List[str],
    ) -> str:
        if eng_conflicts:
            conflict_reasons = "; ".join(c.reason for c in eng_conflicts)
            return (
                f"REJECTION: Not safe for SAME classification. Identified {len(eng_conflicts)} hard "
                f"engineering conflict(s): {conflict_reasons}."
            )
        elif classification == "POTENTIALLY_EQUIVALENT":
            missing_text = ", ".join(missing) if missing else "critical specifications"
            return (
                f"GOVERNANCE REQUIRED: Not safe for automated SAME. Missing technical attributes "
                f"({missing_text}) introduce physical ambiguity requiring human reviewer approval."
            )
        else:
            return "SAFE: Verified identical technical specifications with zero engineering conflicts."

    def _build_audit_trail(
        self,
        source: Material,
        candidate: Material,
        classification: str,
        confidence: float,
    ) -> Dict[str, Any]:
        raw_token = f"{source.id}:{candidate.id}:{classification}:{confidence}"
        det_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:16]

        return {
            "engine_version": "OneMate-AI-v4.0-hybrid",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "deterministic_hash": det_hash,
            "authoritative_classifier": "classify_match-v1.0",
            "engineering_knowledge_engine": "EngineeringKnowledgeEngine-v1.0",
            "semantic_model": self.embedding_service.model_name,
            "source_material_id": str(source.id),
            "candidate_material_id": str(candidate.id),
            "classification_basis": classification,
        }
