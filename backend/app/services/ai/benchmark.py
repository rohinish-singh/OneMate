"""
Empirical AI Retrieval Benchmark Harness for OneMate.

Provides quantitative evaluation of candidate discovery comparing
baseline deterministic retrieval against AI semantic retrieval across
representative industrial material cohorts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import CPSE, Material
from app.services.ai.retrieval import generate_semantic_candidates
from app.services.matching import generate_candidates as baseline_generate_candidates


@dataclass
class BenchmarkCandidateSpec:
    """Specification of a candidate material in a benchmark scenario."""
    code: str
    desc: str
    is_relevant: bool
    hard_conflicts: List[str] = field(default_factory=list)
    category: str = "VALVE"
    valve_type: Optional[str] = None
    size: Optional[str] = None
    body_material: Optional[str] = None
    pressure_class: Optional[str] = None
    connection_type: Optional[str] = None
    trim: Optional[str] = None


@dataclass
class BenchmarkCase:
    """A single evaluation scenario with ground-truth relevance."""
    case_id: str
    case_type: str
    source_code: str
    source_desc: str
    source_category: str
    source_attrs: Dict[str, Any]
    candidates: List[BenchmarkCandidateSpec]
    notes: str = ""


@dataclass
class CaseRetrievalResult:
    """Metrics for a single evaluation case."""
    case_id: str
    case_type: str
    source_desc: str
    known_relevant_codes: List[str]
    baseline_retrieved_codes: List[str]
    ai_retrieved_codes: List[str]
    intersection_codes: List[str]
    ai_only_codes: List[str]
    baseline_only_codes: List[str]
    baseline_recall_at_k: Dict[int, float]
    ai_recall_at_k: Dict[int, float]
    baseline_latency_ms: float
    ai_latency_ms: float
    hard_negatives_in_baseline: List[str]
    hard_negatives_in_ai: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_type": self.case_type,
            "source_desc": self.source_desc,
            "known_relevant_codes": self.known_relevant_codes,
            "baseline_count": len(self.baseline_retrieved_codes),
            "ai_count": len(self.ai_retrieved_codes),
            "intersection_count": len(self.intersection_codes),
            "ai_only_count": len(self.ai_only_codes),
            "baseline_only_count": len(self.baseline_only_codes),
            "baseline_recall": {f"K={k}": round(v, 4) for k, v in self.baseline_recall_at_k.items()},
            "ai_recall": {f"K={k}": round(v, 4) for k, v in self.ai_recall_at_k.items()},
            "baseline_latency_ms": round(self.baseline_latency_ms, 2),
            "ai_latency_ms": round(self.ai_latency_ms, 2),
            "hard_negatives_in_baseline": self.hard_negatives_in_baseline,
            "hard_negatives_in_ai": self.hard_negatives_in_ai,
        }


def calculate_recall_at_k(
    retrieved_codes: List[str],
    relevant_codes: List[str],
    k: int,
) -> float:
    """
    Computes Recall@K: proportion of known relevant candidates present in top-K retrieved items.
    """
    if not relevant_codes:
        return 1.0
    if k <= 0:
        return 0.0

    top_k_retrieved = set(retrieved_codes[:k])
    found = top_k_retrieved.intersection(set(relevant_codes))
    return round(len(found) / len(relevant_codes), 4)


def evaluate_retrieval_case(
    db: Session,
    cpse_source: CPSE,
    cpse_candidate: CPSE,
    case: BenchmarkCase,
    k_values: Optional[List[int]] = None,
    threshold: float = 0.50,
) -> CaseRetrievalResult:
    """
    Seeds an isolated evaluation case into the database, executes both
    baseline and AI retrieval, and computes objective retrieval metrics.
    """
    if k_values is None:
        k_values = [5, 10, 15, 25]

    max_k = max(k_values) if k_values else 25

    run_id = uuid.uuid4().hex[:6]
    actual_to_spec: Dict[str, str] = {}

    # 1. Create source material
    src_attrs = case.source_attrs
    src_code = f"{case.source_code}-{run_id}"
    source = Material(
        id=uuid.uuid4(),
        cpse_id=cpse_source.id,
        source_material_code=src_code,
        source_description=case.source_desc,
        source_uom="EA",
        category=case.source_category,
        normalized_description=case.source_desc,
        valve_type=src_attrs.get("valve_type"),
        size=src_attrs.get("size"),
        body_material=src_attrs.get("body_material"),
        pressure_class=src_attrs.get("pressure_class"),
        connection_type=src_attrs.get("connection_type"),
        trim=src_attrs.get("trim"),
    )
    db.add(source)

    # 2. Create candidate materials in candidate CPSE
    mat_map: Dict[str, Material] = {}
    known_relevant: List[str] = []
    hard_negatives: Dict[str, List[str]] = {}

    for cand_spec in case.candidates:
        unique_cand_code = f"{cand_spec.code}-{run_id}"
        actual_to_spec[unique_cand_code] = cand_spec.code

        cand_mat = Material(
            id=uuid.uuid4(),
            cpse_id=cpse_candidate.id,
            source_material_code=unique_cand_code,
            source_description=cand_spec.desc,
            source_uom="EA",
            category=cand_spec.category,
            normalized_description=cand_spec.desc,
            valve_type=cand_spec.valve_type,
            size=cand_spec.size,
            body_material=cand_spec.body_material,
            pressure_class=cand_spec.pressure_class,
            connection_type=cand_spec.connection_type,
            trim=cand_spec.trim,
        )
        db.add(cand_mat)
        mat_map[cand_spec.code] = cand_mat

        if cand_spec.is_relevant:
            known_relevant.append(cand_spec.code)
        if cand_spec.hard_conflicts:
            hard_negatives[cand_spec.code] = cand_spec.hard_conflicts

    db.commit()
    db.refresh(source)

    # 3. Execute baseline deterministic candidate retrieval (isolated to candidate CPSE)
    t0_base = time.perf_counter()
    all_baseline_records: List[Material] = baseline_generate_candidates(db, source)
    baseline_records = [c for c in all_baseline_records if c.cpse_id == cpse_candidate.id]
    baseline_latency = (time.perf_counter() - t0_base) * 1000.0
    baseline_codes = [actual_to_spec.get(c.source_material_code, c.source_material_code) for c in baseline_records]

    # 4. Execute AI semantic candidate retrieval (isolated to candidate CPSE)
    t0_ai = time.perf_counter()
    ai_candidates = generate_semantic_candidates(
        db=db,
        source=source,
        top_k=max_k,
        min_similarity=threshold,
        category_filter=False,  # Test discovery across categories
        candidate_cpse_id=cpse_candidate.id,
    )
    ai_latency = (time.perf_counter() - t0_ai) * 1000.0
    ai_codes = [actual_to_spec.get(c.material.source_material_code, c.material.source_material_code) for c in ai_candidates]

    # 5. Compute set differences
    intersection = list(set(baseline_codes).intersection(set(ai_codes)))
    ai_only = list(set(ai_codes).difference(set(baseline_codes)))
    baseline_only = list(set(baseline_codes).difference(set(ai_codes)))

    # 6. Compute Recall@K for each K
    base_recalls = {k: calculate_recall_at_k(baseline_codes, known_relevant, k) for k in k_values}
    ai_recalls = {k: calculate_recall_at_k(ai_codes, known_relevant, k) for k in k_values}

    # 7. Identify hard negatives captured in retrieval
    hn_in_base = [c for c in baseline_codes if c in hard_negatives]
    hn_in_ai = [c for c in ai_codes if c in hard_negatives]

    return CaseRetrievalResult(
        case_id=case.case_id,
        case_type=case.case_type,
        source_desc=case.source_desc,
        known_relevant_codes=known_relevant,
        baseline_retrieved_codes=baseline_codes,
        ai_retrieved_codes=ai_codes,
        intersection_codes=intersection,
        ai_only_codes=ai_only,
        baseline_only_codes=baseline_only,
        baseline_recall_at_k=base_recalls,
        ai_recall_at_k=ai_recalls,
        baseline_latency_ms=baseline_latency,
        ai_latency_ms=ai_latency,
        hard_negatives_in_baseline=hn_in_base,
        hard_negatives_in_ai=hn_in_ai,
    )


# --- Deterministic Evaluation Dataset Specification ---
STANDARD_BENCHMARK_CASES: List[BenchmarkCase] = [
    # Cohort A: Exact Semantic Equivalent
    BenchmarkCase(
        case_id="BM-01-EXACT",
        case_type="EXACT_EQUIVALENT",
        source_code="SRC-BM-01",
        source_desc="BALL VALVE DN50 CS CLASS150 RF SS304",
        source_category="VALVE",
        source_attrs={"valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS304"},
        candidates=[
            BenchmarkCandidateSpec("CAND-01-REL", "BALL VALVE DN50 CS CLASS150 RF SS304", is_relevant=True, valve_type="BALL", size="DN50"),
            BenchmarkCandidateSpec("CAND-01-HN-PRESS", "BALL VALVE DN50 CS CLASS300 RF SS304", is_relevant=False, hard_conflicts=["CLASS150 != CLASS300"], valve_type="BALL", size="DN50"),
            BenchmarkCandidateSpec("CAND-01-HN-TYPE", "GATE VALVE DN50 CS CLASS150 RF SS304", is_relevant=False, hard_conflicts=["BALL != GATE"], valve_type="GATE", size="DN50"),
            BenchmarkCandidateSpec("CAND-01-UNRELATED", "CENTRIFUGAL PUMP 50M3/HR CS", is_relevant=False, category="PUMP"),
        ],
        notes="Evaluates retrieval on exact equivalent with identical phrasing.",
    ),

    # Cohort B: Word-Order Permutation & Domain Abbreviations
    BenchmarkCase(
        case_id="BM-02-PERMUTED-ABBR",
        case_type="WORD_ORDER_ABBREVIATION",
        source_code="SRC-BM-02",
        source_desc="VALVE, NEEDLE, 1/2 INCH, SS316, 6000PSI, NPT",
        source_category="VALVE",
        source_attrs={"valve_type": "NEEDLE", "size": "DN15", "body_material": "SS316", "pressure_class": "6000PSI", "connection_type": "NPT"},
        candidates=[
            BenchmarkCandidateSpec("CAND-02-REL", "NEEDLE VALVE 1/2 IN SS316 6000# NPT", is_relevant=True, valve_type="NEEDLE", size="DN15"),
            BenchmarkCandidateSpec("CAND-02-HN-MET", "NEEDLE VALVE 1/2 IN CS 6000PSI NPT", is_relevant=False, hard_conflicts=["SS316 != CARBON_STEEL"], valve_type="NEEDLE", size="DN15"),
            BenchmarkCandidateSpec("CAND-02-HN-PRESS", "NEEDLE VALVE 1/2 IN SS316 150# NPT", is_relevant=False, hard_conflicts=["6000PSI != CLASS150"], valve_type="NEEDLE", size="DN15"),
            BenchmarkCandidateSpec("CAND-02-UNRELATED", "SPIRAL WOUND GASKET DN50 CL150", is_relevant=False, category="GASKET"),
        ],
        notes="Evaluates needle valve with comma structure and 6000# vs 6000PSI abbreviation.",
    ),

    # Cohort C: Size Formats (Imperial 2 IN vs Metric DN50)
    BenchmarkCase(
        case_id="BM-03-SIZE-CONV",
        case_type="SIZE_CONVERSION",
        source_code="SRC-BM-03",
        source_desc="BALL VALVE 2 IN CS 150# RF TRIM SS316",
        source_category="VALVE",
        source_attrs={"valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"},
        candidates=[
            BenchmarkCandidateSpec("CAND-03-REL", "VALVE, BALL, DN50, CS, CLASS150, RF, 316SS", is_relevant=True, valve_type="BALL", size="DN50"),
            BenchmarkCandidateSpec("CAND-03-HN-SIZE", "BALL VALVE 4 IN CS 150# RF TRIM SS316", is_relevant=False, hard_conflicts=["2 IN (DN50) != 4 IN (DN100)"], valve_type="BALL", size="DN100"),
            BenchmarkCandidateSpec("CAND-03-HN-TRIM", "BALL VALVE 2 IN CS 150# RF TRIM SS304", is_relevant=False, hard_conflicts=["SS316 != SS304"], valve_type="BALL", size="DN50"),
        ],
        notes="Evaluates imperial inch size matching metric DN50.",
    ),

    # Cohort D: Connection Variations (Socket Weld vs NPT)
    BenchmarkCase(
        case_id="BM-04-CONN-SW",
        case_type="CONNECTION_VARIATION",
        source_code="SRC-BM-04",
        source_desc="GATE VALVE DN25 CLASS800 SW A105",
        source_category="VALVE",
        source_attrs={"valve_type": "GATE", "size": "DN25", "body_material": "CARBON_STEEL", "pressure_class": "CLASS800", "connection_type": "SOCKET_WELD"},
        candidates=[
            BenchmarkCandidateSpec("CAND-04-REL", "FORGED STEEL GATE VALVE 1 IN 800# SOCKET WELD CS", is_relevant=True, valve_type="GATE", size="DN25"),
            BenchmarkCandidateSpec("CAND-04-HN-CONN", "FORGED STEEL GATE VALVE 1 IN 800# NPT CS", is_relevant=False, hard_conflicts=["SOCKET_WELD != NPT"], valve_type="GATE", size="DN25"),
        ],
        notes="Evaluates socket weld terminology and 800# rating.",
    ),

    # Cohort E: Equipment Category Boundary (Pumps vs Bearings)
    BenchmarkCase(
        case_id="BM-05-EQUIP-PUMP",
        case_type="EQUIPMENT_CATEGORY",
        source_code="SRC-BM-05",
        source_desc="CENTRIFUGAL PUMP 100 M3/HR HEAD 50M CS",
        source_category="PUMP",
        source_attrs={},
        candidates=[
            BenchmarkCandidateSpec("CAND-05-REL", "PUMP, CENTRIFUGAL, 100M3/H, 50M HEAD, CS", is_relevant=True, category="PUMP"),
            BenchmarkCandidateSpec("CAND-05-UNRELATED", "BALL BEARING 6205 2RS", is_relevant=False, category="BEARING"),
        ],
        notes="Evaluates equipment boundary between pumps and unrelated bearings.",
    ),

    # Cohort F: Incomplete / Ambiguous Source Description
    BenchmarkCase(
        case_id="BM-06-AMBIGUOUS",
        case_type="AMBIGUOUS_INCOMPLETE",
        source_code="SRC-BM-06",
        source_desc="BALL VALVE 2 IN",
        source_category="VALVE",
        source_attrs={"valve_type": "BALL", "size": "DN50"},
        candidates=[
            BenchmarkCandidateSpec("CAND-06-REL-1", "BALL VALVE 2 IN CS 150# RF", is_relevant=True, valve_type="BALL", size="DN50"),
            BenchmarkCandidateSpec("CAND-06-REL-2", "BALL VALVE 2 IN SS316 300# RF", is_relevant=True, valve_type="BALL", size="DN50"),
            BenchmarkCandidateSpec("CAND-06-HN-SIZE", "BALL VALVE 6 IN CS 150# RF", is_relevant=False, hard_conflicts=["2 IN != 6 IN"], valve_type="BALL", size="DN150"),
        ],
        notes="Source lacks pressure, material, and connection. Evaluates plausibility retrieval under incomplete attributes.",
    ),
]

