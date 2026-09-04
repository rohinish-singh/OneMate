"""
AI Semantic Candidate Retrieval Service for OneMate.

Provides parallel, additive cross-CPSE candidate retrieval using dense semantic embeddings.
Enforces strict cross-CPSE isolation and self-match prohibition.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Material
from app.services.ai.embedding import EmbeddingService, cosine_similarity
from app.services.ai.profile import MaterialProfile

logger = logging.getLogger(__name__)


@dataclass
class SemanticCandidate:
    """
    A single cross-CPSE candidate discovered through dense semantic embedding similarity.
    """
    material_id: uuid.UUID
    material: Material
    similarity_score: float
    canonical_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": str(self.material_id),
            "source_material_code": self.material.source_material_code,
            "source_description": self.material.source_description,
            "category": self.material.category,
            "similarity_score": round(self.similarity_score, 4),
            "canonical_text": self.canonical_text,
        }


@dataclass
class CandidateComparisonResult:
    """
    Diagnostic result comparing baseline deterministic retrieval vs AI semantic retrieval.
    """
    source_material_id: uuid.UUID
    baseline_candidate_count: int
    ai_candidate_count: int
    intersection_count: int
    ai_only_count: int
    baseline_only_count: int
    overlap_ratio: float
    ai_candidates: List[Dict[str, Any]] = field(default_factory=list)
    baseline_candidates: List[Dict[str, Any]] = field(default_factory=list)
    baseline_latency_ms: float = 0.0
    ai_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_material_id": str(self.source_material_id),
            "baseline_candidate_count": self.baseline_candidate_count,
            "ai_candidate_count": self.ai_candidate_count,
            "intersection_count": self.intersection_count,
            "ai_only_count": self.ai_only_count,
            "baseline_only_count": self.baseline_only_count,
            "overlap_ratio": round(self.overlap_ratio, 4),
            "baseline_latency_ms": round(self.baseline_latency_ms, 2),
            "ai_latency_ms": round(self.ai_latency_ms, 2),
            "ai_candidates": self.ai_candidates,
            "baseline_candidates": self.baseline_candidates,
        }


def get_material_search_text(material: Material) -> str:
    """
    Constructs the canonical text used for semantic embedding.
    Combines structured profile canonical string with cleaned source description.
    """
    try:
        profile = MaterialProfile.from_material(material)
        canonical = profile.to_canonical_string()
        if canonical:
            return canonical
    except Exception as e:
        logger.debug(f"Failed to generate canonical text from profile for material {material.id}: {e}")

    return material.normalized_description or material.source_description or ""


def generate_semantic_candidates(
    db: Session,
    source: Material,
    top_k: Optional[int] = None,
    min_similarity: Optional[float] = None,
    category_filter: bool = True,
    candidate_cpse_id: Optional[uuid.UUID] = None,
) -> List[SemanticCandidate]:
    """
    Generates cross-CPSE candidates using dense vector embedding similarity.

    Guarantees:
    - candidate.id != source.id (self-match excluded)
    - candidate.cpse_id != source.cpse_id (same-CPSE excluded)
    - Returns at most top_k candidates (default: settings.candidate_retrieval_top_k)
    - Filters by similarity >= min_similarity (default: settings.candidate_similarity_threshold)
    - Pure retrieval query: does NOT mutate mappings or create recommendations
    """
    if not source or source.cpse_id is None:
        return []

    effective_top_k = top_k if top_k is not None else getattr(settings, "candidate_retrieval_top_k", 15)
    effective_threshold = min_similarity if min_similarity is not None else getattr(settings, "candidate_similarity_threshold", 0.60)

    try:
        embedding_service = EmbeddingService.get_instance()
    except Exception as e:
        logger.warning(f"EmbeddingService unavailable for semantic retrieval: {e}")
        return []

    # 1. Generate embedding for source material
    source_text = get_material_search_text(source)
    if not source_text.strip():
        return []

    try:
        source_vector = embedding_service.encode_one(source_text)
    except Exception as e:
        logger.warning(f"Failed to compute embedding for source material {source.id}: {e}")
        return []

    # 2. Query potential candidates from other CPSEs (cross-CPSE isolation enforced at DB level)
    query = db.query(Material).filter(
        Material.id != source.id,
        Material.cpse_id != source.cpse_id,
    )

    if candidate_cpse_id is not None:
        query = query.filter(Material.cpse_id == candidate_cpse_id)

    src_cat = source.category or (source.normalized_attributes.get("category") if isinstance(source.normalized_attributes, dict) else None)
    if category_filter and src_cat:
        query = query.filter(
            (Material.category == src_cat) |
            (Material.normalized_attributes["category"].astext == src_cat)
        )

    candidate_records: List[Material] = query.all()
    if not candidate_records:
        return []

    # Extra invariant guard: double check in Python memory
    filtered_records = [
        c for c in candidate_records
        if c.id != source.id and c.cpse_id != source.cpse_id and (
            not (category_filter and src_cat) or
            (c.category == src_cat or (isinstance(c.normalized_attributes, dict) and c.normalized_attributes.get("category") == src_cat))
        )
    ]
    if not filtered_records:
        return []

    # 3. Batch encode candidate texts
    candidate_texts = [get_material_search_text(c) for c in filtered_records]

    try:
        candidate_vectors = embedding_service.encode(candidate_texts)
    except Exception as e:
        logger.warning(f"Failed to batch-encode candidate vectors: {e}")
        return []

    # 4. Compute cosine similarities and filter
    scored_candidates: List[SemanticCandidate] = []
    for cand_record, cand_text, cand_vec in zip(filtered_records, candidate_texts, candidate_vectors):
        sim = cosine_similarity(source_vector, cand_vec)
        if sim >= effective_threshold:
            scored_candidates.append(
                SemanticCandidate(
                    material_id=cand_record.id,
                    material=cand_record,
                    similarity_score=sim,
                    canonical_text=cand_text,
                )
            )

    # 5. Sort descending by similarity score and truncate to Top-K
    scored_candidates.sort(key=lambda x: x.similarity_score, reverse=True)
    return scored_candidates[:effective_top_k]


def compare_candidate_retrieval(
    db: Session,
    source: Material,
    top_k: Optional[int] = None,
    min_similarity: Optional[float] = None,
) -> CandidateComparisonResult:
    """
    Executes baseline deterministic retrieval and AI semantic retrieval in parallel.
    Produces comprehensive diagnostic metrics for comparison and evaluation.
    """
    from app.services.matching import generate_candidates as baseline_generate_candidates

    # 1. Baseline deterministic retrieval
    t0_baseline = time.perf_counter()
    baseline_records: List[Material] = baseline_generate_candidates(db, source)
    baseline_latency = (time.perf_counter() - t0_baseline) * 1000.0

    # 2. AI semantic retrieval
    t0_ai = time.perf_counter()
    ai_candidates: List[SemanticCandidate] = generate_semantic_candidates(
        db=db,
        source=source,
        top_k=top_k,
        min_similarity=min_similarity,
    )
    ai_latency = (time.perf_counter() - t0_ai) * 1000.0

    # 3. Compare sets
    baseline_ids: Set[uuid.UUID] = {c.id for c in baseline_records}
    ai_ids: Set[uuid.UUID] = {c.material_id for c in ai_candidates}

    intersection = baseline_ids.intersection(ai_ids)
    ai_only = ai_ids.difference(baseline_ids)
    baseline_only = baseline_ids.difference(ai_ids)

    total_unique = len(baseline_ids.union(ai_ids))
    overlap_ratio = (len(intersection) / total_unique) if total_unique > 0 else 1.0

    baseline_data = [
        {
            "candidate_id": str(c.id),
            "source_material_code": c.source_material_code,
            "source_description": c.source_description,
            "category": c.category,
        }
        for c in baseline_records
    ]

    ai_data = [c.to_dict() for c in ai_candidates]

    return CandidateComparisonResult(
        source_material_id=source.id,
        baseline_candidate_count=len(baseline_records),
        ai_candidate_count=len(ai_candidates),
        intersection_count=len(intersection),
        ai_only_count=len(ai_only),
        baseline_only_count=len(baseline_only),
        overlap_ratio=overlap_ratio,
        ai_candidates=ai_data,
        baseline_candidates=baseline_data,
        baseline_latency_ms=baseline_latency,
        ai_latency_ms=ai_latency,
    )

