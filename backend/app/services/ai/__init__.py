"""
OneMate AI Material Intelligence Subsystem.

Provides:
- Structured Material Profile (4-state attribute representation)
- Semantic Embedding Service (all-MiniLM-L6-v2 + fallback)
- Authoritative Engineering Knowledge & Validation Engine
- Semantic Candidate Retrieval & Hybrid Shadow Union
- AI Attribute Extraction & Linguistic Understanding
- Semantic Reranking & Comparison Engine
"""

from app.services.ai.profile import (
    AttributeState,
    MaterialProfile,
    ProfileAttribute,
)
from app.services.ai.embedding import (
    EmbeddingModel,
    EmbeddingService,
    DeterministicFallbackEmbeddingModel,
    SentenceTransformerEmbeddingModel,
    cosine_similarity,
)
from app.services.ai.validation import (
    EngineeringKnowledgeEngine,
    ValidationResult,
)
from app.services.ai.retrieval import (
    CandidateComparisonResult,
    SemanticCandidate,
    compare_candidate_retrieval,
    generate_semantic_candidates,
    get_material_search_text,
)
from app.services.ai.shadow import (
    HybridCandidate,
    ShadowClassificationResult,
    ShadowComparisonReport,
    generate_hybrid_candidates,
    run_shadow_matching_analysis,
)
from app.services.ai.extraction import (
    MaterialAttributeExtractor,
    PatternMaterialExtractor,
    ProfileComparisonReport,
    compare_material_profiles,
)
from app.services.ai.extraction_benchmark import (
    EXTRACTION_BENCHMARK_CASES,
    ExtractionBenchmarkMetrics,
    ExtractionTestCase,
    run_extraction_benchmark,
)
from app.services.ai.reranking import (
    MaterialSemanticReranker,
    RerankedCandidate,
    SemanticRerankingReport,
    rerank_candidates_shadow,
)
from app.services.ai.reranking_benchmark import (
    RerankingBenchmarkMetrics,
    RerankingBenchmarkScenario,
    RERANKING_BENCHMARK_SCENARIOS,
    run_reranking_benchmark,
)
from app.services.ai.explainability import (
    AttributeComparisonItem,
    EngineeringConflictItem,
    MaterialExplanationService,
    RecommendationExplanation,
    SemanticEvidence,
)

__all__ = [
    "AttributeState",
    "MaterialProfile",
    "ProfileAttribute",
    "EmbeddingModel",
    "EmbeddingService",
    "DeterministicFallbackEmbeddingModel",
    "SentenceTransformerEmbeddingModel",
    "cosine_similarity",
    "EngineeringKnowledgeEngine",
    "ValidationResult",
    "SemanticCandidate",
    "CandidateComparisonResult",
    "generate_semantic_candidates",
    "compare_candidate_retrieval",
    "get_material_search_text",
    "HybridCandidate",
    "ShadowClassificationResult",
    "ShadowComparisonReport",
    "generate_hybrid_candidates",
    "run_shadow_matching_analysis",
    "MaterialAttributeExtractor",
    "PatternMaterialExtractor",
    "ProfileComparisonReport",
    "compare_material_profiles",
    "ExtractionTestCase",
    "ExtractionBenchmarkMetrics",
    "EXTRACTION_BENCHMARK_CASES",
    "run_extraction_benchmark",
    "MaterialSemanticReranker",
    "RerankedCandidate",
    "SemanticRerankingReport",
    "rerank_candidates_shadow",
    "RerankingBenchmarkScenario",
    "RerankingBenchmarkMetrics",
    "RERANKING_BENCHMARK_SCENARIOS",
    "run_reranking_benchmark",
    "AttributeComparisonItem",
    "EngineeringConflictItem",
    "MaterialExplanationService",
    "RecommendationExplanation",
    "SemanticEvidence",
]
