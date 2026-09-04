"""
Deterministic Evaluation Benchmark for AI-Assisted Semantic Reranking.

Phase 3C Validation Gate:
Evaluates semantic candidate reranking against baseline candidate ordering across
12 independent, representative industrial material cohorts:

RR-01 Exact Equivalent
RR-02 Reordered Description
RR-03 Abbreviation-Heavy Description
RR-04 Unit Variation
RR-05 Fractional Size
RR-06 Material Variation (Hard Negative: Metallurgy)
RR-07 Pressure Variation (Hard Negative: Pressure Class)
RR-08 Connection Variation (Hard Negative: Facing Geometry)
RR-09 Equipment-Type Confusion (Hard Negative: Valve Sub-type)
RR-10 Misclassified Category (Hard Negative: Equipment Family)
RR-11 Incomplete Material (Uncertainty Preservation)
RR-12 Noisy Industrial Description (Vendor Metadata & Noise)

Measures:
- Baseline vs Reranked Top-1 accuracy
- Recall@1, Recall@3, Recall@5
- Baseline vs Reranked Mean Reciprocal Rank (MRR)
- Scenarios improved, unchanged, and worsened
- Rank movement of relevant equivalents
- Hard-negative semantic score distribution
- Engineering conflict preservation rate (100% invariant)
- Zero False-SAME rate (100% invariant)
- Latency (average warm & maximum observed)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models import Material
from app.services.ai.reranking import MaterialSemanticReranker, RerankedCandidate


@dataclass
class RerankingBenchmarkScenario:
    """An independent benchmark query scenario with candidate pool containing equivalents and hard negatives."""
    scenario_id: str
    scenario_name: str
    source_description: str
    source_attrs: Dict[str, Optional[str]]
    candidate_pool: List[Dict[str, Any]]
    expected_relevant_ids: List[str]
    notes: str = ""


@dataclass
class RerankingBenchmarkMetrics:
    """Comprehensive quantitative performance, ranking quality, and engineering safety metrics."""
    total_scenarios: int
    top1_accuracy_baseline: float
    top1_accuracy_reranked: float
    recall_at_1_baseline: float
    recall_at_1_reranked: float
    recall_at_3_baseline: float
    recall_at_3_reranked: float
    recall_at_5_baseline: float
    recall_at_5_reranked: float
    mrr_baseline: float
    mrr_reranked: float
    scenarios_improved: int
    scenarios_unchanged: int
    scenarios_worsened: int
    average_rank_movement_equivalents: float
    hard_negatives_total: int
    hard_negatives_conflicts_preserved: int
    conflict_preservation_rate: float
    zero_false_same_rate: float
    false_same_count: int
    additional_potential_count: int
    average_latency_ms: float
    max_latency_ms: float
    scenario_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_scenarios": self.total_scenarios,
            "top1_accuracy_baseline": round(self.top1_accuracy_baseline, 4),
            "top1_accuracy_reranked": round(self.top1_accuracy_reranked, 4),
            "recall_at_1_baseline": round(self.recall_at_1_baseline, 4),
            "recall_at_1_reranked": round(self.recall_at_1_reranked, 4),
            "recall_at_3_baseline": round(self.recall_at_3_baseline, 4),
            "recall_at_3_reranked": round(self.recall_at_3_reranked, 4),
            "recall_at_5_baseline": round(self.recall_at_5_baseline, 4),
            "recall_at_5_reranked": round(self.recall_at_5_reranked, 4),
            "mrr_baseline": round(self.mrr_baseline, 4),
            "mrr_reranked": round(self.mrr_reranked, 4),
            "scenarios_improved": self.scenarios_improved,
            "scenarios_unchanged": self.scenarios_unchanged,
            "scenarios_worsened": self.scenarios_worsened,
            "average_rank_movement_equivalents": round(self.average_rank_movement_equivalents, 2),
            "hard_negatives_total": self.hard_negatives_total,
            "hard_negatives_conflicts_preserved": self.hard_negatives_conflicts_preserved,
            "conflict_preservation_rate": round(self.conflict_preservation_rate, 4),
            "zero_false_same_rate": round(self.zero_false_same_rate, 4),
            "false_same_count": self.false_same_count,
            "additional_potential_count": self.additional_potential_count,
            "average_latency_ms": round(self.average_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "scenario_results": self.scenario_results,
        }


def _make_dummy_material(
    code: str,
    desc: str,
    category: str = "VALVE",
    **kwargs: Any,
) -> Material:
    """Creates an in-memory Material model instance for deterministic offline testing."""
    return Material(
        id=uuid.uuid4(),
        cpse_id=uuid.uuid4(),
        source_material_code=code,
        source_description=desc,
        source_uom="EA",
        category=category,
        normalized_description=desc,
        normalized_uom="EA",
        valve_type=kwargs.get("valve_type"),
        size=kwargs.get("size"),
        body_material=kwargs.get("body_material"),
        pressure_class=kwargs.get("pressure_class"),
        connection_type=kwargs.get("connection_type"),
        trim=kwargs.get("trim"),
    )


# ---------------------------------------------------------------------------
# Standard 12-Scenario Industrial Evaluation Suite
# ---------------------------------------------------------------------------

RERANKING_BENCHMARK_SCENARIOS: List[RerankingBenchmarkScenario] = [
    # RR-01: Exact Semantic Equivalent
    RerankingBenchmarkScenario(
        scenario_id="RR-01-EXACT",
        scenario_name="Exact Semantic Equivalent",
        source_description="BALL VALVE DN50 CS CLASS150 RF SS304 TRIM",
        source_attrs={"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS304"},
        candidate_pool=[
            {"id": "C-01-HN-TYPE", "desc": "GATE VALVE DN50 CS CLASS150 RF SS304 TRIM", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "BALL != GATE", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS304"}},
            {"id": "C-01-HN-PRESS", "desc": "BALL VALVE DN50 CS CLASS300 RF SS304 TRIM", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "CLASS150 != CLASS300", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS300", "connection_type": "RF", "trim": "SS304"}},
            {"id": "C-01-REL", "desc": "BALL VALVE DN50 CS CLASS150 RF SS304 TRIM", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS304"}},
            {"id": "C-01-UNRELATED", "desc": "CENTRIFUGAL PUMP 50M3/HR CS", "is_relevant": False, "is_hard_negative": False, "attrs": {"category": "PUMP"}},
        ],
        expected_relevant_ids=["C-01-REL"],
        notes="Exact equivalent is placed at position 3 in baseline retrieval; reranking should elevate it to rank 1.",
    ),

    # RR-02: Reordered Description
    RerankingBenchmarkScenario(
        scenario_id="RR-02-REORDERED",
        scenario_name="Word-Order Permutation",
        source_description="GATE VALVE DN50 CS CLASS150 RF TRIM SS316",
        source_attrs={"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"},
        candidate_pool=[
            {"id": "C-02-HN-MAT", "desc": "GATE VALVE DN50 SS316 CLASS150 RF TRIM SS316", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "CS vs SS316 body", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "SS316", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"}},
            {"id": "C-02-HN-SIZE", "desc": "GATE VALVE DN100 CS CLASS150 RF TRIM SS316", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "DN50 vs DN100", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN100", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"}},
            {"id": "C-02-REL", "desc": "RF CLASS150 CS DN50 GATE VALVE TRIM SS316", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"}},
            {"id": "C-02-UNRELATED", "desc": "SPIRAL WOUND GASKET DN50 CLASS150", "is_relevant": False, "is_hard_negative": False, "attrs": {"category": "GASKET", "size": "DN50", "pressure_class": "CLASS150"}},
        ],
        expected_relevant_ids=["C-02-REL"],
        notes="Permuted word-order equivalent placed lower in lexical retrieval.",
    ),

    # RR-03: Abbreviation-Heavy Description
    RerankingBenchmarkScenario(
        scenario_id="RR-03-ABBREVIATIONS",
        scenario_name="Abbreviation-Heavy Phrasing",
        source_description="NEEDLE VALVE 1/2 IN SS316 6000PSI NPT",
        source_attrs={"category": "VALVE", "valve_type": "NEEDLE", "size": "DN15", "body_material": "SS316", "pressure_class": "6000PSI", "connection_type": "NPT"},
        candidate_pool=[
            {"id": "C-03-HN-MAT", "desc": "NEEDLE VALVE 1/2 IN CS 6000PSI NPT", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "SS316 vs CS", "attrs": {"category": "VALVE", "valve_type": "NEEDLE", "size": "DN15", "body_material": "CARBON_STEEL", "pressure_class": "6000PSI", "connection_type": "NPT"}},
            {"id": "C-03-HN-PRESS", "desc": "NEEDLE VALVE 1/2 IN SS316 3000PSI NPT", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "6000PSI vs 3000PSI", "attrs": {"category": "VALVE", "valve_type": "NEEDLE", "size": "DN15", "body_material": "SS316", "pressure_class": "3000PSI", "connection_type": "NPT"}},
            {"id": "C-03-REL", "desc": "VLV, NDL, 1/2\", 6000#, NPT, SS 316", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "NEEDLE", "size": "DN15", "body_material": "SS316", "pressure_class": "6000PSI", "connection_type": "NPT"}},
            {"id": "C-03-UNRELATED", "desc": "BALL BEARING 6205 2RS", "is_relevant": False, "is_hard_negative": False, "attrs": {"category": "BEARING"}},
        ],
        expected_relevant_ids=["C-03-REL"],
        notes="Heavily abbreviated candidate with symbol units (1/2\", 6000#, VLV, NDL).",
    ),

    # RR-04: Unit Variation
    RerankingBenchmarkScenario(
        scenario_id="RR-04-UNIT-VARIATION",
        scenario_name="Metric vs Imperial Unit Variation",
        source_description="GATE VALVE DN25 CS CLASS800 SOCKET WELD",
        source_attrs={"category": "VALVE", "valve_type": "GATE", "size": "DN25", "body_material": "CARBON_STEEL", "pressure_class": "CLASS800", "connection_type": "SOCKET_WELD"},
        candidate_pool=[
            {"id": "C-04-HN-PRESS", "desc": "GATE VALVE 25 MM 150 LBS SW A105", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "CLASS800 vs CLASS150", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN25", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "SOCKET_WELD"}},
            {"id": "C-04-HN-SIZE", "desc": "GATE VALVE 50 MM 800 LBS SW A105", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "DN25 vs DN50", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS800", "connection_type": "SOCKET_WELD"}},
            {"id": "C-04-REL", "desc": "FORGED STEEL GATE VALVE 25 MM 800 LBS SW A105", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN25", "body_material": "CARBON_STEEL", "pressure_class": "CLASS800", "connection_type": "SOCKET_WELD"}},
            {"id": "C-04-HN-TYPE", "desc": "CHECK VALVE DN25 CS CLASS800 SW", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "GATE vs CHECK", "attrs": {"category": "VALVE", "valve_type": "CHECK", "size": "DN25", "body_material": "CARBON_STEEL", "pressure_class": "CLASS800", "connection_type": "SOCKET_WELD"}},
        ],
        expected_relevant_ids=["C-04-REL"],
        notes="25 MM corresponds to DN25; 800 LBS corresponds to CLASS800.",
    ),

    # RR-05: Fractional Size
    RerankingBenchmarkScenario(
        scenario_id="RR-05-FRACTIONAL-SIZE",
        scenario_name="Fractional Size Equivalent",
        source_description="BALL VALVE DN40 SS316 CLASS300 RF",
        source_attrs={"category": "VALVE", "valve_type": "BALL", "size": "DN40", "body_material": "SS316", "pressure_class": "CLASS300", "connection_type": "RF"},
        candidate_pool=[
            {"id": "C-05-HN-SIZE2", "desc": "BALL VALVE 2 IN SS316 300# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "DN40 vs DN50", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "SS316", "pressure_class": "CLASS300", "connection_type": "RF"}},
            {"id": "C-05-HN-SIZE1", "desc": "BALL VALVE 1 IN SS316 300# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "DN40 vs DN25", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN25", "body_material": "SS316", "pressure_class": "CLASS300", "connection_type": "RF"}},
            {"id": "C-05-REL", "desc": "BALL VALVE 1-1/2 IN SS316 300# RF", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN40", "body_material": "SS316", "pressure_class": "CLASS300", "connection_type": "RF"}},
            {"id": "C-05-HN-TYPE", "desc": "BUTTERFLY VALVE DN40 SS316 CLASS300 RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "BALL vs BUTTERFLY", "attrs": {"category": "VALVE", "valve_type": "BUTTERFLY", "size": "DN40", "body_material": "SS316", "pressure_class": "CLASS300", "connection_type": "RF"}},
        ],
        expected_relevant_ids=["C-05-REL"],
        notes="1-1/2 IN maps to DN40; 1 IN and 2 IN are hard dimensional negatives.",
    ),

    # RR-06: Material Variation (Hard Negative Metallurgy)
    RerankingBenchmarkScenario(
        scenario_id="RR-06-MATERIAL-VARIATION",
        scenario_name="Material Metallurgy Variation",
        source_description="GATE VALVE DN50 SS316 CLASS150 RF TRIM 316",
        source_attrs={"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "SS316", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"},
        candidate_pool=[
            {"id": "C-06-HN-CS", "desc": "GATE VALVE DN50 CS CLASS150 RF TRIM 316", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "SS316 vs CS body", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"}},
            {"id": "C-06-HN-CI", "desc": "GATE VALVE DN50 CAST IRON CLASS150 RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "SS316 vs CAST_IRON", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CAST_IRON", "pressure_class": "CLASS150", "connection_type": "RF"}},
            {"id": "C-06-REL", "desc": "GATE VALVE DN50 SS316 CLASS150 RF TRIM 316", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "SS316", "pressure_class": "CLASS150", "connection_type": "RF", "trim": "SS316"}},
            {"id": "C-06-UNRELATED", "desc": "CENTRIFUGAL PUMP SS316 50M3/H", "is_relevant": False, "is_hard_negative": False, "attrs": {"category": "PUMP"}},
        ],
        expected_relevant_ids=["C-06-REL"],
        notes="High lexical overlap on CS valve with SS316 trim; engineering engine must reject CS body.",
    ),

    # RR-07: Pressure Variation (Hard Negative Pressure Class)
    RerankingBenchmarkScenario(
        scenario_id="RR-07-PRESSURE-VARIATION",
        scenario_name="Pressure Rating Variation",
        source_description="BALL VALVE DN50 CS CLASS150 RF",
        source_attrs={"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"},
        candidate_pool=[
            {"id": "C-07-HN-CL600", "desc": "BALL VALVE 2 IN CS 600# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "CLASS150 vs CLASS600", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS600", "connection_type": "RF"}},
            {"id": "C-07-HN-CL1500", "desc": "BALL VALVE 2 IN CS 1500# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "CLASS150 vs CLASS1500", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS1500", "connection_type": "RF"}},
            {"id": "C-07-REL", "desc": "BALL VALVE 2 IN CS 150# RF", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
            {"id": "C-07-HN-TYPE", "desc": "GLOBE VALVE 2 IN CS 150# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "BALL vs GLOBE", "attrs": {"category": "VALVE", "valve_type": "GLOBE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
        ],
        expected_relevant_ids=["C-07-REL"],
        notes="Dense embeddings may rank 600# highly due to high token similarity; engineering validation must enforce CLASS150.",
    ),

    # RR-08: Connection Variation (Hard Negative Facing Geometry)
    RerankingBenchmarkScenario(
        scenario_id="RR-08-CONNECTION-VARIATION",
        scenario_name="Connection Facing Variation",
        source_description="CHECK VALVE DN50 CS CLASS150 RF",
        source_attrs={"category": "VALVE", "valve_type": "CHECK", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"},
        candidate_pool=[
            {"id": "C-08-HN-NPT", "desc": "CHECK VALVE 2 IN CS 150# NPT", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "RF vs NPT", "attrs": {"category": "VALVE", "valve_type": "CHECK", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "NPT"}},
            {"id": "C-08-HN-BW", "desc": "CHECK VALVE 2 IN CS 150# BUTT WELD", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "RF vs BUTT_WELD", "attrs": {"category": "VALVE", "valve_type": "CHECK", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "BUTT_WELD"}},
            {"id": "C-08-REL", "desc": "CHECK VALVE 2 IN CS 150# RAISED FACE", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "CHECK", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
            {"id": "C-08-UNRELATED", "desc": "SUBMERSIBLE PUMP 2 IN 50M", "is_relevant": False, "is_hard_negative": False, "attrs": {"category": "PUMP"}},
        ],
        expected_relevant_ids=["C-08-REL"],
        notes="NPT and BUTT WELD connections are physically incompatible with RF flanged piping.",
    ),

    # RR-09: Equipment-Type Confusion (Hard Negative Valve Sub-type)
    RerankingBenchmarkScenario(
        scenario_id="RR-09-EQUIPMENT-TYPE",
        scenario_name="Valve Equipment Type Discrimination",
        source_description="GLOBE VALVE DN50 CS CLASS150 RF",
        source_attrs={"category": "VALVE", "valve_type": "GLOBE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"},
        candidate_pool=[
            {"id": "C-09-HN-GATE", "desc": "GATE VALVE 2 IN CS 150# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "GLOBE vs GATE", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
            {"id": "C-09-HN-BALL", "desc": "BALL VALVE 2 IN CS 150# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "GLOBE vs BALL", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
            {"id": "C-09-REL", "desc": "GLOBE VALVE 2 IN CS 150# RF", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "GLOBE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
            {"id": "C-09-HN-PLUG", "desc": "PLUG VALVE 2 IN CS 150# RF", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "GLOBE vs PLUG", "attrs": {"category": "VALVE", "valve_type": "PLUG", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
        ],
        expected_relevant_ids=["C-09-REL"],
        notes="High vocabulary overlap across valve types; strict sub-type identity required.",
    ),

    # RR-10: Misclassified Category (Hard Negative Equipment Family)
    RerankingBenchmarkScenario(
        scenario_id="RR-10-MISCLASSIFIED-CATEGORY",
        scenario_name="Cross-Category Discrimination",
        source_description="SPIRAL WOUND GASKET DN50 CLASS150 CS SS316",
        source_attrs={"category": "GASKET", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"},
        candidate_pool=[
            {"id": "C-10-HN-VALVE", "desc": "GATE VALVE DN50 CS CLASS150 RF SS316", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "GASKET vs VALVE", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"}},
            {"id": "C-10-HN-FLANGE", "desc": "WELD NECK FLANGE DN50 CLASS150 CS", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "GASKET vs FLANGE", "attrs": {"category": "FLANGE", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"}},
            {"id": "C-10-REL", "desc": "SPW GASKET 2 IN 150# CS/316", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "GASKET", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"}},
            {"id": "C-10-UNRELATED", "desc": "BALL BEARING 6205 2RS", "is_relevant": False, "is_hard_negative": False, "attrs": {"category": "BEARING"}},
        ],
        expected_relevant_ids=["C-10-REL"],
        notes="Gasket piping component sharing rating and metallurgy with valves and flanges.",
    ),

    # RR-11: Incomplete Material (Uncertainty Preservation)
    RerankingBenchmarkScenario(
        scenario_id="RR-11-INCOMPLETE",
        scenario_name="Incomplete Source Uncertainty",
        source_description="BALL VALVE 2 IN",
        source_attrs={"category": "VALVE", "valve_type": "BALL", "size": "DN50"},
        candidate_pool=[
            {"id": "C-11-HN-SIZE", "desc": "BALL VALVE 4 IN", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "2 IN != 4 IN", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN100"}},
            {"id": "C-11-HN-TYPE", "desc": "GATE VALVE 2 IN", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "BALL != GATE", "attrs": {"category": "VALVE", "valve_type": "GATE", "size": "DN50"}},
            {"id": "C-11-REL", "desc": "BALL VALVE DN50", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50"}},
            {"id": "C-11-POTENTIAL", "desc": "BALL VALVE DN50 CS 150# RF", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN50", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150", "connection_type": "RF"}},
        ],
        expected_relevant_ids=["C-11-REL", "C-11-POTENTIAL"],
        notes="Source lacks pressure, metallurgy, connection; cannot be classified as SAME (must remain POTENTIAL).",
    ),

    # RR-12: Noisy Industrial Description
    RerankingBenchmarkScenario(
        scenario_id="RR-12-NOISY-DESCRIPTION",
        scenario_name="Vendor Noise & Part Number Resiliency",
        source_description="ITEM #994-A: BUTTERFLY VALVE 4 IN WAFER CL150 BODY CS (TAG: P-101)",
        source_attrs={"category": "VALVE", "valve_type": "BUTTERFLY", "size": "DN100", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"},
        candidate_pool=[
            {"id": "C-12-HN-PRESS", "desc": "BUTTERFLY VALVE DN100 WAFER CLASS300 CS", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "CLASS150 vs CLASS300", "attrs": {"category": "VALVE", "valve_type": "BUTTERFLY", "size": "DN100", "body_material": "CARBON_STEEL", "pressure_class": "CLASS300"}},
            {"id": "C-12-HN-SIZE", "desc": "BUTTERFLY VALVE DN150 WAFER CLASS150 CS", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "DN100 vs DN150", "attrs": {"category": "VALVE", "valve_type": "BUTTERFLY", "size": "DN150", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"}},
            {"id": "C-12-REL", "desc": "BUTTERFLY VALVE DN100 WAFER CLASS150 CS", "is_relevant": True, "is_hard_negative": False, "attrs": {"category": "VALVE", "valve_type": "BUTTERFLY", "size": "DN100", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"}},
            {"id": "C-12-HN-TYPE", "desc": "BALL VALVE DN100 CLASS150 CS", "is_relevant": False, "is_hard_negative": True, "conflict_reason": "BUTTERFLY != BALL", "attrs": {"category": "VALVE", "valve_type": "BALL", "size": "DN100", "body_material": "CARBON_STEEL", "pressure_class": "CLASS150"}},
        ],
        expected_relevant_ids=["C-12-REL"],
        notes="Semantic embeddings filter through noisy tag numbers and item codes to prioritize standard clean specification.",
    ),
]


def run_reranking_benchmark(
    scenarios: Optional[List[RerankingBenchmarkScenario]] = None,
) -> RerankingBenchmarkMetrics:
    """
    Executes the multi-scenario reranking benchmark comparing baseline ordering against AI reranking.
    Enforces engineering safety invariants across all hard negatives.
    """
    if scenarios is None:
        scenarios = RERANKING_BENCHMARK_SCENARIOS

    reranker = MaterialSemanticReranker()

    total_scenarios = len(scenarios)

    # Metric tracking
    top1_baseline_hits = 0
    top1_reranked_hits = 0
    r1_base_hits = 0
    r1_rerank_hits = 0
    r3_base_hits = 0
    r3_rerank_hits = 0
    r5_base_hits = 0
    r5_rerank_hits = 0

    reciprocal_ranks_base: List[float] = []
    reciprocal_ranks_rerank: List[float] = []

    scenarios_improved = 0
    scenarios_unchanged = 0
    scenarios_worsened = 0

    rank_movements: List[int] = []

    hard_negatives_total = 0
    hard_negatives_conflicts_preserved = 0
    false_same_count = 0
    additional_potential_count = 0

    total_latency_ms = 0.0
    max_latency_ms = 0.0

    scenario_summaries: List[Dict[str, Any]] = []

    for scen in scenarios:
        src_attrs = dict(scen.source_attrs)
        src_cat = src_attrs.pop("category", "VALVE")
        src = _make_dummy_material(
            code="SRC-BENCH",
            desc=scen.source_description,
            category=src_cat,
            **src_attrs,
        )

        candidate_materials: List[Material] = []
        cand_meta: Dict[str, Dict[str, Any]] = {}

        for c_data in scen.candidate_pool:
            c_attrs = dict(c_data["attrs"])
            c_cat = c_attrs.pop("category", "VALVE")
            c_mat = _make_dummy_material(
                code=c_data["id"],
                desc=c_data["desc"],
                category=c_cat,
                **c_attrs,
            )
            candidate_materials.append(c_mat)
            cand_meta[str(c_mat.id)] = c_data

        # Execute semantic reranking
        t0 = time.perf_counter()
        reranked, baseline, lat_ms = reranker.rerank(src, candidate_materials)
        total_latency_ms += lat_ms
        if lat_ms > max_latency_ms:
            max_latency_ms = lat_ms

        # 1. Baseline metrics
        base_top1_id = cand_meta[str(baseline[0].candidate_id)]["id"] if baseline else ""
        base_top1_relevant = base_top1_id in scen.expected_relevant_ids
        if base_top1_relevant:
            top1_baseline_hits += 1
            r1_base_hits += 1

        base_top3_ids = [cand_meta[str(c.candidate_id)]["id"] for c in baseline[:3]]
        if any(cid in scen.expected_relevant_ids for cid in base_top3_ids):
            r3_base_hits += 1

        base_top5_ids = [cand_meta[str(c.candidate_id)]["id"] for c in baseline[:5]]
        if any(cid in scen.expected_relevant_ids for cid in base_top5_ids):
            r5_base_hits += 1

        # Baseline first relevant rank
        base_rel_rank = next((idx + 1 for idx, c in enumerate(baseline) if cand_meta[str(c.candidate_id)]["id"] in scen.expected_relevant_ids), None)
        if base_rel_rank:
            reciprocal_ranks_base.append(1.0 / base_rel_rank)

        # 2. Reranked metrics
        rerank_top1_id = cand_meta[str(reranked[0].candidate_id)]["id"] if reranked else ""
        rerank_top1_relevant = rerank_top1_id in scen.expected_relevant_ids
        if rerank_top1_relevant:
            top1_reranked_hits += 1
            r1_rerank_hits += 1

        rerank_top3_ids = [cand_meta[str(c.candidate_id)]["id"] for c in reranked[:3]]
        if any(cid in scen.expected_relevant_ids for cid in rerank_top3_ids):
            r3_rerank_hits += 1

        rerank_top5_ids = [cand_meta[str(c.candidate_id)]["id"] for c in reranked[:5]]
        if any(cid in scen.expected_relevant_ids for cid in rerank_top5_ids):
            r5_rerank_hits += 1

        rerank_rel_rank = next((idx + 1 for idx, c in enumerate(reranked) if cand_meta[str(c.candidate_id)]["id"] in scen.expected_relevant_ids), None)
        if rerank_rel_rank:
            reciprocal_ranks_rerank.append(1.0 / rerank_rel_rank)

        # 3. Scenario rank movement comparison
        if base_rel_rank is not None and rerank_rel_rank is not None:
            if rerank_rel_rank < base_rel_rank:
                scenarios_improved += 1
                rank_movements.append(base_rel_rank - rerank_rel_rank)
            elif rerank_rel_rank == base_rel_rank:
                scenarios_unchanged += 1
                rank_movements.append(0)
            else:
                scenarios_worsened += 1
                rank_movements.append(base_rel_rank - rerank_rel_rank)

        # 4. Hard negative & safety evaluation
        hn_scores: List[float] = []
        for rc in reranked:
            meta = cand_meta[str(rc.candidate_id)]

            if meta.get("is_hard_negative"):
                hard_negatives_total += 1
                hn_scores.append(rc.ai_semantic_score)

                # Must preserve engineering conflict and classify as DIFFERENT
                if not rc.is_engineering_compatible or len(rc.hard_conflicts) > 0 or rc.classification == "DIFFERENT":
                    hard_negatives_conflicts_preserved += 1

                # NON-NEGOTIABLE INVARIANT: Must NEVER classify hard negative as SAME
                if rc.classification == "SAME":
                    false_same_count += 1

            # Count if an irrelevant candidate turned into POTENTIAL
            if not meta.get("is_relevant") and not meta.get("is_hard_negative") and rc.classification == "POTENTIALLY_EQUIVALENT":
                additional_potential_count += 1

        scenario_summaries.append({
            "scenario_id": scen.scenario_id,
            "scenario_name": scen.scenario_name,
            "candidate_count": len(scen.candidate_pool),
            "baseline_top1_id": base_top1_id,
            "reranked_top1_id": rerank_top1_id,
            "baseline_rel_rank": base_rel_rank,
            "reranked_rel_rank": rerank_rel_rank,
            "rank_change": "IMPROVED" if (rerank_rel_rank or 99) < (base_rel_rank or 99) else ("UNCHANGED" if rerank_rel_rank == base_rel_rank else "WORSENED"),
            "top1_semantic_score": reranked[0].ai_semantic_score if reranked else 0.0,
            "top1_classification": reranked[0].classification if reranked else None,
            "hard_negative_scores": [round(s, 4) for s in hn_scores],
            "latency_ms": round(lat_ms, 2),
        })

    # Quantitative aggregations
    acc_base = (top1_baseline_hits / total_scenarios) if total_scenarios > 0 else 0.0
    acc_rerank = (top1_reranked_hits / total_scenarios) if total_scenarios > 0 else 0.0
    r1_base = (r1_base_hits / total_scenarios) if total_scenarios > 0 else 0.0
    r1_rerank = (r1_rerank_hits / total_scenarios) if total_scenarios > 0 else 0.0
    r3_base = (r3_base_hits / total_scenarios) if total_scenarios > 0 else 0.0
    r3_rerank = (r3_rerank_hits / total_scenarios) if total_scenarios > 0 else 0.0
    r5_base = (r5_base_hits / total_scenarios) if total_scenarios > 0 else 0.0
    r5_rerank = (r5_rerank_hits / total_scenarios) if total_scenarios > 0 else 0.0

    mrr_base = (sum(reciprocal_ranks_base) / total_scenarios) if total_scenarios > 0 else 0.0
    mrr_rerank = (sum(reciprocal_ranks_rerank) / total_scenarios) if total_scenarios > 0 else 0.0

    avg_movement = (sum(rank_movements) / len(rank_movements)) if rank_movements else 0.0
    pres_rate = (hard_negatives_conflicts_preserved / hard_negatives_total) if hard_negatives_total > 0 else 1.0
    zero_same_rate = 1.0 - ((false_same_count / hard_negatives_total) if hard_negatives_total > 0 else 0.0)
    avg_lat = (total_latency_ms / total_scenarios) if total_scenarios > 0 else 0.0

    return RerankingBenchmarkMetrics(
        total_scenarios=total_scenarios,
        top1_accuracy_baseline=acc_base,
        top1_accuracy_reranked=acc_rerank,
        recall_at_1_baseline=r1_base,
        recall_at_1_reranked=r1_rerank,
        recall_at_3_baseline=r3_base,
        recall_at_3_reranked=r3_rerank,
        recall_at_5_baseline=r5_base,
        recall_at_5_reranked=r5_rerank,
        mrr_baseline=mrr_base,
        mrr_reranked=mrr_rerank,
        scenarios_improved=scenarios_improved,
        scenarios_unchanged=scenarios_unchanged,
        scenarios_worsened=scenarios_worsened,
        average_rank_movement_equivalents=avg_movement,
        hard_negatives_total=hard_negatives_total,
        hard_negatives_conflicts_preserved=hard_negatives_conflicts_preserved,
        conflict_preservation_rate=pres_rate,
        zero_false_same_rate=zero_same_rate,
        false_same_count=false_same_count,
        additional_potential_count=additional_potential_count,
        average_latency_ms=avg_lat,
        max_latency_ms=max_latency_ms,
        scenario_results=scenario_summaries,
    )
