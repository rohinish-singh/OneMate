"""
AI-Assisted Semantic Reranking & Candidate Comparison Service for OneMate.

Phase 3B: Shadow/diagnostic mode reranking that computes semantic relevance scores
for retrieved cross-CPSE candidates while strictly preserving authoritative
deterministic engineering validation and classification semantics.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from app.models import Material
from app.services.ai.embedding import EmbeddingService, cosine_similarity
from app.services.ai.profile import MaterialProfile
from app.services.ai.retrieval import get_material_search_text
from app.services.ai.shadow import HybridCandidate, generate_hybrid_candidates
from app.services.ai.validation import EngineeringKnowledgeEngine
from app.services.matching import classify_match, generate_candidates as baseline_generate_candidates

logger = logging.getLogger(__name__)


@dataclass
class RerankedCandidate:
    """Diagnostic candidate representation with semantic rank, baseline rank, and engineering validation."""
    candidate_id: uuid.UUID
    source_material_code: str
    source_description: str
    category: str
    baseline_position: int
    ai_semantic_score: float
    ai_semantic_rank: int
    rank_movement: int
    retrieval_origin: str
    classification: str
    confidence: float
    is_engineering_compatible: bool
    hard_conflicts: List[str] = field(default_factory=list)
    explanation: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": str(self.candidate_id),
            "source_material_code": self.source_material_code,
            "source_description": self.source_description,
            "category": self.category,
            "baseline_position": self.baseline_position,
            "ai_semantic_score": round(self.ai_semantic_score, 4),
            "ai_semantic_rank": self.ai_semantic_rank,
            "rank_movement": self.rank_movement,
            "retrieval_origin": self.retrieval_origin,
            "classification": self.classification,
            "confidence": round(float(self.confidence), 4),
            "is_engineering_compatible": self.is_engineering_compatible,
            "hard_conflicts": self.hard_conflicts,
            "explanation": self.explanation,
            "evidence": self.evidence,
        }


@dataclass
class SemanticRerankingReport:
    """Side-by-side diagnostic analysis of baseline candidate ordering vs AI semantic reranking."""
    source_material_id: uuid.UUID
    source_description: str
    candidate_count: int
    reranked_candidates: List[RerankedCandidate] = field(default_factory=list)
    baseline_candidates: List[RerankedCandidate] = field(default_factory=list)
    classification_distribution_baseline: Dict[str, int] = field(default_factory=dict)
    classification_distribution_reranked: Dict[str, int] = field(default_factory=dict)
    hard_conflicts_count: int = 0
    reranking_latency_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_material_id": str(self.source_material_id),
            "source_description": self.source_description,
            "candidate_count": self.candidate_count,
            "classification_distribution_baseline": self.classification_distribution_baseline,
            "classification_distribution_reranked": self.classification_distribution_reranked,
            "hard_conflicts_count": self.hard_conflicts_count,
            "reranking_latency_ms": round(self.reranking_latency_ms, 2),
            "error": self.error,
            "reranked_candidates": [c.to_dict() for c in self.reranked_candidates],
            "baseline_candidates": [c.to_dict() for c in self.baseline_candidates],
        }


class MaterialSemanticReranker:
    """
    Reranks a list of retrieved candidates according to dense semantic vector similarity
    computed by the EmbeddingService, while evaluating authoritative engineering constraints.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None) -> None:
        self.embedding_service = embedding_service or EmbeddingService.get_instance()

    def rerank(
        self,
        source: Material,
        candidates: List[Union[HybridCandidate, Material]],
    ) -> Tuple[List[RerankedCandidate], List[RerankedCandidate], float]:
        """
        Calculates semantic similarity scores for all candidates and produces
        both baseline-ordered and reranked-ordered diagnostic candidate lists.
        """
        t0 = time.perf_counter()

        if not candidates:
            return [], [], round((time.perf_counter() - t0) * 1000, 2)

        # 1. Prepare source representation
        src_text = get_material_search_text(source)
        src_profile = MaterialProfile.from_material(source)

        # 2. Extract material models and origin provenance
        norm_candidates: List[Tuple[Material, str]] = []
        for cand in candidates:
            if isinstance(cand, HybridCandidate):
                norm_candidates.append((cand.material, cand.origin))
            elif isinstance(cand, Material):
                norm_candidates.append((cand, "BASELINE"))
            else:
                mat = getattr(cand, "material", cand)
                norm_candidates.append((mat, getattr(cand, "origin", "BASELINE")))

        # 3. Batch compute candidate embeddings with failure isolation
        try:
            src_vector = self.embedding_service.encode_one(src_text)
            cand_texts = [get_material_search_text(m) for m, _ in norm_candidates]
            cand_vectors = self.embedding_service.encode(cand_texts)
        except Exception as e:
            logger.warning(f"Embedding computation failed during reranking: {e}. Falling back to baseline order.")
            src_vector = []
            cand_vectors = [[] for _ in norm_candidates]

        # 4. Evaluate each candidate against classifier & engineering rules
        baseline_items: List[RerankedCandidate] = []
        for idx, ((cand_mat, origin), cand_vec) in enumerate(zip(norm_candidates, cand_vectors)):
            sim_score = float(cosine_similarity(src_vector, cand_vec))

            # Deterministic classifier
            match_res = classify_match(source, cand_mat)

            # Engineering knowledge engine validation
            cand_profile = MaterialProfile.from_material(cand_mat)
            val_res = EngineeringKnowledgeEngine.validate_profiles(src_profile, cand_profile)

            # Combine hard conflicts from both engines
            all_conflicts = list(dict.fromkeys(
                val_res.hard_conflicts +
                [f for f in match_res.get("explanation", "").split("; ") if "conflict" in f.lower()]
            ))

            rc = RerankedCandidate(
                candidate_id=cand_mat.id,
                source_material_code=cand_mat.source_material_code,
                source_description=cand_mat.source_description or "",
                category=cand_mat.category or "UNKNOWN",
                baseline_position=idx + 1,
                ai_semantic_score=sim_score,
                ai_semantic_rank=idx + 1,  # updated after sort
                rank_movement=0,           # updated after sort
                retrieval_origin=origin,
                classification=match_res["classification"],
                confidence=match_res["confidence"],
                is_engineering_compatible=val_res.is_compatible,
                hard_conflicts=all_conflicts,
                explanation=match_res["explanation"],
                evidence=match_res["evidence"],
            )
            baseline_items.append(rc)

        # 5. Semantic sort: descending by semantic score
        # In case of tie, preserve baseline position
        reranked_items = sorted(
            baseline_items,
            key=lambda item: (-item.ai_semantic_score, item.baseline_position)
        )

        # 6. Assign semantic rank and compute rank movement
        # rank_movement = baseline_position - ai_semantic_rank
        # (positive = moved closer to rank 1, negative = dropped, 0 = unchanged)
        final_reranked: List[RerankedCandidate] = []
        for rank_idx, item in enumerate(reranked_items):
            new_rank = rank_idx + 1
            movement = item.baseline_position - new_rank
            updated = RerankedCandidate(
                candidate_id=item.candidate_id,
                source_material_code=item.source_material_code,
                source_description=item.source_description,
                category=item.category,
                baseline_position=item.baseline_position,
                ai_semantic_score=item.ai_semantic_score,
                ai_semantic_rank=new_rank,
                rank_movement=movement,
                retrieval_origin=item.retrieval_origin,
                classification=item.classification,
                confidence=item.confidence,
                is_engineering_compatible=item.is_engineering_compatible,
                hard_conflicts=list(item.hard_conflicts),
                explanation=item.explanation,
                evidence=dict(item.evidence),
            )
            final_reranked.append(updated)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return final_reranked, baseline_items, latency_ms


def rerank_candidates_shadow(
    db: Session,
    source: Material,
    candidates: Optional[List[Union[HybridCandidate, Material]]] = None,
    top_k: int = 15,
) -> SemanticRerankingReport:
    """
    Executes shadow semantic reranking for a source material.

    If candidates is None, retrieves candidates via hybrid retrieval (or baseline if hybrid disabled).
    Computes side-by-side diagnostic report with zero production state mutation.
    """
    try:
        if candidates is None:
            hybrid_cands, _ = generate_hybrid_candidates(
                db=db,
                source=source,
                top_k=top_k,
                category_filter=True,
            )
            candidates = hybrid_cands

        reranker = MaterialSemanticReranker()
        reranked_list, baseline_list, latency_ms = reranker.rerank(source, candidates)

        def count_distributions(items: List[RerankedCandidate]) -> Dict[str, int]:
            dist = {"SAME": 0, "POTENTIALLY_EQUIVALENT": 0, "DIFFERENT": 0}
            for it in items:
                dist[it.classification] = dist.get(it.classification, 0) + 1
            return dist

        dist_base = count_distributions(baseline_list)
        dist_rerank = count_distributions(reranked_list)
        conflict_count = sum(1 for c in reranked_list if not c.is_engineering_compatible or c.hard_conflicts)

        return SemanticRerankingReport(
            source_material_id=source.id,
            source_description=source.source_description or source.normalized_description or "",
            candidate_count=len(reranked_list),
            reranked_candidates=reranked_list,
            baseline_candidates=baseline_list,
            classification_distribution_baseline=dist_base,
            classification_distribution_reranked=dist_rerank,
            hard_conflicts_count=conflict_count,
            reranking_latency_ms=latency_ms,
        )
    except Exception as e:
        logger.warning(f"Semantic reranking shadow analysis failed for material {source.id}: {e}")
        # Safe fallback: return empty report with error note rather than crashing
        return SemanticRerankingReport(
            source_material_id=source.id,
            source_description=source.source_description or "",
            candidate_count=0,
            error=str(e),
        )
