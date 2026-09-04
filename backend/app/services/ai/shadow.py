"""
Hybrid Retrieval Shadow Integration Service for OneMate.

Provides controlled shadow integration combining baseline deterministic
candidate retrieval with AI semantic candidate retrieval in a deduplicated union.
Evaluates hypothetical downstream classification and noise without modifying
persisted production state or recommendation workflows.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models import Material
from app.services.ai.retrieval import SemanticCandidate, generate_semantic_candidates
from app.services.ai.validation import EngineeringKnowledgeEngine
from app.services.matching import classify_match, generate_candidates as baseline_generate_candidates

logger = logging.getLogger(__name__)


@dataclass
class HybridCandidate:
    """
    A deduplicated candidate in the hybrid union, tracking provenance.
    """
    material: Material
    is_in_baseline: bool
    is_in_ai: bool
    ai_similarity: Optional[float] = None

    @property
    def candidate_id(self) -> uuid.UUID:
        return self.material.id

    @property
    def origin(self) -> str:
        if self.is_in_baseline and self.is_in_ai:
            return "BOTH"
        elif self.is_in_baseline:
            return "BASELINE"
        else:
            return "AI_ONLY"


@dataclass
class ShadowClassificationResult:
    """Hypothetical classification result for a candidate in shadow mode."""
    candidate_id: uuid.UUID
    source_material_code: str
    source_description: str
    category: str
    origin: str
    classification: str
    confidence: float
    ai_similarity: Optional[float]
    explanation: str
    evidence: Dict[str, Any]
    hard_conflicts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": str(self.candidate_id),
            "source_material_code": self.source_material_code,
            "source_description": self.source_description,
            "category": self.category,
            "origin": self.origin,
            "classification": self.classification,
            "confidence": round(float(self.confidence), 4),
            "ai_similarity": round(self.ai_similarity, 4) if self.ai_similarity is not None else None,
            "explanation": self.explanation,
            "hard_conflicts": self.hard_conflicts,
        }


@dataclass
class ShadowComparisonReport:
    """
    Comparative report analyzing baseline recommendations vs hypothetical hybrid recommendations.
    """
    source_material_id: uuid.UUID
    baseline_candidate_count: int
    ai_candidate_count: int
    hybrid_candidate_count: int
    intersection_count: int
    ai_only_candidate_count: int
    baseline_only_candidate_count: int
    baseline_distribution: Dict[str, int]
    hybrid_distribution: Dict[str, int]
    delta_distribution: Dict[str, int]
    baseline_recommendations: List[ShadowClassificationResult] = field(default_factory=list)
    hybrid_recommendations: List[ShadowClassificationResult] = field(default_factory=list)
    ai_only_recommendations: List[ShadowClassificationResult] = field(default_factory=list)
    baseline_retrieval_latency_ms: float = 0.0
    ai_retrieval_latency_ms: float = 0.0
    hybrid_union_latency_ms: float = 0.0
    classification_latency_ms: float = 0.0
    total_shadow_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_material_id": str(self.source_material_id),
            "baseline_candidate_count": self.baseline_candidate_count,
            "ai_candidate_count": self.ai_candidate_count,
            "hybrid_candidate_count": self.hybrid_candidate_count,
            "intersection_count": self.intersection_count,
            "ai_only_candidate_count": self.ai_only_candidate_count,
            "baseline_only_candidate_count": self.baseline_only_candidate_count,
            "baseline_distribution": self.baseline_distribution,
            "hybrid_distribution": self.hybrid_distribution,
            "delta_distribution": self.delta_distribution,
            "baseline_recommendations": [r.to_dict() for r in self.baseline_recommendations],
            "hybrid_recommendations": [r.to_dict() for r in self.hybrid_recommendations],
            "ai_only_recommendations": [r.to_dict() for r in self.ai_only_recommendations],
            "latencies_ms": {
                "baseline_retrieval": round(self.baseline_retrieval_latency_ms, 2),
                "ai_retrieval": round(self.ai_retrieval_latency_ms, 2),
                "hybrid_union": round(self.hybrid_union_latency_ms, 2),
                "classification": round(self.classification_latency_ms, 2),
                "total_shadow": round(self.total_shadow_latency_ms, 2),
            },
        }


def generate_hybrid_candidates(
    db: Session,
    source: Material,
    top_k: Optional[int] = None,
    min_similarity: Optional[float] = None,
    category_filter: bool = True,
    candidate_cpse_id: Optional[uuid.UUID] = None,
) -> Tuple[List[HybridCandidate], Dict[str, float]]:
    """
    Constructs the deduplicated hybrid candidate union:
    Baseline Candidates UNION AI Semantic Candidates.

    Invariants enforced:
    - candidate.id != source.id (self-match excluded)
    - candidate.cpse_id != source.cpse_id (same-CPSE excluded)
    - Deduplicated by material ID
    - Preserves baseline candidates in original order
    - Appends AI-only candidates sorted by semantic similarity
    - Pure retrieval: does NOT mutate database state
    """
    latencies: Dict[str, float] = {}

    if not source or source.cpse_id is None:
        return [], latencies

    # 1. Baseline retrieval
    t0_base = time.perf_counter()
    all_base_records = baseline_generate_candidates(db, source)
    if candidate_cpse_id is not None:
        base_records = [c for c in all_base_records if c.cpse_id == candidate_cpse_id]
    else:
        base_records = all_base_records
    latencies["baseline_retrieval"] = (time.perf_counter() - t0_base) * 1000.0

    # 2. AI semantic retrieval
    t0_ai = time.perf_counter()
    try:
        ai_candidates = generate_semantic_candidates(
            db=db,
            source=source,
            top_k=top_k,
            min_similarity=min_similarity,
            category_filter=category_filter,
            candidate_cpse_id=candidate_cpse_id,
        )
    except Exception as e:
        logger.warning(
            f"AI semantic candidate retrieval failed for material {source.id}: {e}; "
            f"falling back to baseline candidates only."
        )
        ai_candidates = []
    latencies["ai_retrieval"] = (time.perf_counter() - t0_ai) * 1000.0

    # 3. Deduplicated Hybrid Union
    t0_union = time.perf_counter()
    ai_candidate_map: Dict[uuid.UUID, SemanticCandidate] = {
        c.material_id: c for c in ai_candidates
    }

    seen_ids: Set[uuid.UUID] = set()
    hybrid_list: List[HybridCandidate] = []

    # First: Add all baseline candidates in their original order
    for cand in base_records:
        if cand.id == source.id or cand.cpse_id == source.cpse_id:
            continue
        if cand.id in seen_ids:
            continue

        seen_ids.add(cand.id)
        ai_match = ai_candidate_map.get(cand.id)
        hybrid_list.append(
            HybridCandidate(
                material=cand,
                is_in_baseline=True,
                is_in_ai=ai_match is not None,
                ai_similarity=ai_match.similarity_score if ai_match else None,
            )
        )

    # Second: Append AI-only candidates (not present in baseline)
    for ai_cand in ai_candidates:
        cand_mat = ai_cand.material
        if cand_mat.id == source.id or cand_mat.cpse_id == source.cpse_id:
            continue
        if cand_mat.id in seen_ids:
            continue

        seen_ids.add(cand_mat.id)
        hybrid_list.append(
            HybridCandidate(
                material=cand_mat,
                is_in_baseline=False,
                is_in_ai=True,
                ai_similarity=ai_cand.similarity_score,
            )
        )

    latencies["hybrid_union"] = (time.perf_counter() - t0_union) * 1000.0
    return hybrid_list, latencies


def run_shadow_matching_analysis(
    db: Session,
    source: Material,
    top_k: Optional[int] = None,
    min_similarity: Optional[float] = None,
    category_filter: bool = True,
    candidate_cpse_id: Optional[uuid.UUID] = None,
) -> ShadowComparisonReport:
    """
    Executes a complete shadow matching analysis for a source material.

    1. Retrieves baseline and AI candidates.
    2. Builds the deduplicated hybrid union.
    3. Executes the existing production classification logic (classify_match) in memory.
    4. Evaluates authoritative hard engineering conflicts (EngineeringKnowledgeEngine).
    5. Computes classification distributions and downstream recommendation noise.
    6. Does NOT write to MatchRecommendation, MaterialNationalMapping, or AuditLog.
    """
    t_start = time.perf_counter()

    hybrid_candidates, latencies = generate_hybrid_candidates(
        db=db,
        source=source,
        top_k=top_k,
        min_similarity=min_similarity,
        category_filter=category_filter,
        candidate_cpse_id=candidate_cpse_id,
    )

    t0_classify = time.perf_counter()
    baseline_recs: List[ShadowClassificationResult] = []
    hybrid_recs: List[ShadowClassificationResult] = []
    ai_only_recs: List[ShadowClassificationResult] = []

    base_dist = {"SAME": 0, "POTENTIALLY_EQUIVALENT": 0, "DIFFERENT": 0}
    hyb_dist = {"SAME": 0, "POTENTIALLY_EQUIVALENT": 0, "DIFFERENT": 0}

    for hyb_cand in hybrid_candidates:
        cand_mat = hyb_cand.material

        # Reuse existing production classification logic
        class_res = classify_match(source, cand_mat)
        classification = class_res["classification"]
        confidence = float(class_res["confidence"]) if class_res.get("confidence") is not None else 0.0

        # Run authoritative engineering validation to diagnose hard conflicts
        val_res = EngineeringKnowledgeEngine.validate_materials(source, cand_mat)
        hard_conflicts = val_res.hard_conflicts

        shadow_rec = ShadowClassificationResult(
            candidate_id=cand_mat.id,
            source_material_code=cand_mat.source_material_code,
            source_description=cand_mat.source_description,
            category=cand_mat.category,
            origin=hyb_cand.origin,
            classification=classification,
            confidence=confidence,
            ai_similarity=hyb_cand.ai_similarity,
            explanation=class_res.get("explanation", ""),
            evidence=class_res.get("evidence", {}),
            hard_conflicts=hard_conflicts,
        )

        hybrid_recs.append(shadow_rec)
        hyb_dist[classification] = hyb_dist.get(classification, 0) + 1

        if hyb_cand.is_in_baseline:
            baseline_recs.append(shadow_rec)
            base_dist[classification] = base_dist.get(classification, 0) + 1

        if hyb_cand.origin == "AI_ONLY":
            ai_only_recs.append(shadow_rec)

    latencies["classification"] = (time.perf_counter() - t0_classify) * 1000.0
    total_latency = (time.perf_counter() - t_start) * 1000.0

    delta_dist = {
        cls_name: hyb_dist.get(cls_name, 0) - base_dist.get(cls_name, 0)
        for cls_name in ["SAME", "POTENTIALLY_EQUIVALENT", "DIFFERENT"]
    }

    base_count = len(baseline_recs)
    ai_count = sum(1 for c in hybrid_candidates if c.is_in_ai)
    hyb_count = len(hybrid_recs)
    intersect_count = sum(1 for c in hybrid_candidates if c.is_in_baseline and c.is_in_ai)
    ai_only_count = len(ai_only_recs)
    base_only_count = sum(1 for c in hybrid_candidates if c.is_in_baseline and not c.is_in_ai)

    return ShadowComparisonReport(
        source_material_id=source.id,
        baseline_candidate_count=base_count,
        ai_candidate_count=ai_count,
        hybrid_candidate_count=hyb_count,
        intersection_count=intersect_count,
        ai_only_candidate_count=ai_only_count,
        baseline_only_candidate_count=base_only_count,
        baseline_distribution=base_dist,
        hybrid_distribution=hyb_dist,
        delta_distribution=delta_dist,
        baseline_recommendations=baseline_recs,
        hybrid_recommendations=hybrid_recs,
        ai_only_recommendations=ai_only_recs,
        baseline_retrieval_latency_ms=latencies.get("baseline_retrieval", 0.0),
        ai_retrieval_latency_ms=latencies.get("ai_retrieval", 0.0),
        hybrid_union_latency_ms=latencies.get("hybrid_union", 0.0),
        classification_latency_ms=latencies.get("classification", 0.0),
        total_shadow_latency_ms=total_latency,
    )
