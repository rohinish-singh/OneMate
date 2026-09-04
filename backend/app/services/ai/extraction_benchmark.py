"""
Empirical Benchmark & Evaluation Dataset for AI Material Attribute Extraction.

Provides standardized industrial test cases across clean, reordered, abbreviated,
noisy, incomplete, and conflicting material descriptions to measure:
- attribute agreement rate
- missing-field detection rate
- false extraction rate
- conflict detection rate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.ai.extraction import PatternMaterialExtractor
from app.services.ai.profile import AttributeState, ProfileAttribute


@dataclass
class ExtractionTestCase:
    """Benchmark test case for material attribute understanding."""
    case_id: str
    case_type: str
    raw_description: str
    source_uom: Optional[str] = "EA"
    category_hint: Optional[str] = None
    expected_attributes: Dict[str, Optional[str]] = field(default_factory=dict)
    expected_conflicts: List[str] = field(default_factory=list)
    expected_missing: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ExtractionBenchmarkMetrics:
    """Quantitative performance metrics across extraction benchmark cohorts."""
    total_cases: int
    total_attribute_slots: int
    correctly_extracted_slots: int
    agreement_rate: float
    missing_fields_total: int
    missing_fields_detected: int
    missing_field_detection_rate: float
    conflicts_total: int
    conflicts_detected: int
    conflict_detection_rate: float
    false_extractions_total: int
    false_extraction_rate: float
    case_summaries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "total_attribute_slots": self.total_attribute_slots,
            "correctly_extracted_slots": self.correctly_extracted_slots,
            "agreement_rate": round(self.agreement_rate, 4),
            "missing_fields_total": self.missing_fields_total,
            "missing_fields_detected": self.missing_fields_detected,
            "missing_field_detection_rate": round(self.missing_field_detection_rate, 4),
            "conflicts_total": self.conflicts_total,
            "conflicts_detected": self.conflicts_detected,
            "conflict_detection_rate": round(self.conflict_detection_rate, 4),
            "false_extractions_total": self.false_extractions_total,
            "false_extraction_rate": round(self.false_extraction_rate, 4),
            "case_summaries": self.case_summaries,
        }


# Standard Industrial Extraction Benchmark Dataset
EXTRACTION_BENCHMARK_CASES: List[ExtractionTestCase] = [
    # 1. Clean description
    ExtractionTestCase(
        case_id="EX-01-CLEAN",
        case_type="CLEAN",
        raw_description="GATE VALVE DN50 CS CLASS150 RF",
        expected_attributes={
            "category": "VALVE",
            "material_type": "GATE",
            "size": "DN50",
            "material_grade": "CARBON_STEEL",
            "pressure_rating": "CLASS150",
            "connection_type": "RF",
        },
        expected_missing=["trim_material"],
        notes="Standard industrial gate valve description in canonical order.",
    ),

    # 2. Reordered description
    ExtractionTestCase(
        case_id="EX-02-REORDERED",
        case_type="REORDERED",
        raw_description="RF CLASS150 CS DN50 GATE VALVE",
        expected_attributes={
            "category": "VALVE",
            "material_type": "GATE",
            "size": "DN50",
            "material_grade": "CARBON_STEEL",
            "pressure_rating": "CLASS150",
            "connection_type": "RF",
        },
        expected_missing=["trim_material"],
        notes="Attributes listed in reverse order (connection, pressure, body, size, type).",
    ),

    # 3. Domain abbreviations and pound rating
    ExtractionTestCase(
        case_id="EX-03-ABBREVIATIONS",
        case_type="ABBREVIATIONS",
        raw_description="VLV, NDL, 1/2\", 6000#, NPT, SS 316",
        expected_attributes={
            "category": "VALVE",
            "material_type": "NEEDLE",
            "size": "DN15",
            "material_grade": "SS316",
            "pressure_rating": "6000PSI",
            "connection_type": "NPT",
        },
        expected_missing=["trim_material"],
        notes="Abbreviated needle valve with 1/2 inch symbol and 6000# rating.",
    ),

    # 4. Unit variation (inch fractions vs millimeters)
    ExtractionTestCase(
        case_id="EX-04-UNIT-VARIATION",
        case_type="UNIT_VARIATION",
        raw_description="FORGED STEEL GATE VALVE 25 MM 800 LBS SOCKET WELD A105",
        expected_attributes={
            "category": "VALVE",
            "material_type": "GATE",
            "size": "DN25",
            "material_grade": "CARBON_STEEL",
            "pressure_rating": "CLASS800",
            "connection_type": "SOCKET_WELD",
        },
        expected_missing=["trim_material"],
        notes="Metric 25 MM size mapping to DN25 and A105 forged steel.",
    ),

    # 5. Noisy description with vendor part code and filler text
    ExtractionTestCase(
        case_id="EX-05-NOISY",
        case_type="NOISY",
        raw_description="ITEM REF #4092-B: BUTTERFLY VALVE 4 INCH WAFER CL300 BODY CI (TAG: UT-902)",
        expected_attributes={
            "category": "VALVE",
            "material_type": "BUTTERFLY",
            "size": "DN100",
            "material_grade": "CAST_IRON",
            "pressure_rating": "CLASS300",
        },
        expected_missing=["connection_type", "trim_material"],
        notes="Embedded metadata tags, item numbers, and parenthetical comments.",
    ),

    # 6. Incomplete description (lacks pressure, connection, and body metallurgy)
    ExtractionTestCase(
        case_id="EX-06-INCOMPLETE",
        case_type="INCOMPLETE",
        raw_description="BALL VALVE 2 IN",
        expected_attributes={
            "category": "VALVE",
            "material_type": "BALL",
            "size": "DN50",
        },
        expected_missing=["pressure_rating", "material_grade", "connection_type", "trim_material"],
        notes="Missing pressure, material, and connection attributes must remain NOT_PRESENT.",
    ),

    # 7. Conflicting description (self-contradictory body metallurgy)
    ExtractionTestCase(
        case_id="EX-07-CONFLICTING-MET",
        case_type="CONFLICTING",
        raw_description="GATE VALVE 2 IN CS BODY ... SS316 BODY CLASS150 RF",
        expected_attributes={
            "category": "VALVE",
            "material_type": "GATE",
            "size": "DN50",
            "pressure_rating": "CLASS150",
            "connection_type": "RF",
        },
        expected_conflicts=["material_grade"],
        notes="Contradictory body materials (CS vs SS316) must trigger CONFLICTING state.",
    ),

    # 8. Conflicting description (contradictory sizes)
    ExtractionTestCase(
        case_id="EX-08-CONFLICTING-SIZE",
        case_type="CONFLICTING",
        raw_description="BALL VALVE 2 IN ... 4 IN CS 150# RF",
        expected_attributes={
            "category": "VALVE",
            "material_type": "BALL",
            "material_grade": "CARBON_STEEL",
            "pressure_rating": "CLASS150",
            "connection_type": "RF",
        },
        expected_conflicts=["size"],
        notes="Multiple conflicting nominal sizes (2 IN vs 4 IN) must trigger CONFLICTING state.",
    ),
]


def run_extraction_benchmark(
    cases: Optional[List[ExtractionTestCase]] = None,
) -> ExtractionBenchmarkMetrics:
    """Executes the extraction benchmark suite and compiles objective accuracy metrics."""
    if cases is None:
        cases = EXTRACTION_BENCHMARK_CASES

    extractor = PatternMaterialExtractor()

    total_cases = len(cases)
    total_slots = 0
    correct_slots = 0
    missing_total = 0
    missing_detected = 0
    conflicts_total = 0
    conflicts_detected = 0
    false_extractions = 0

    case_summaries: List[Dict[str, Any]] = []

    for case in cases:
        profile = extractor.extract(
            text=case.raw_description,
            source_uom=case.source_uom,
            category_hint=case.category_hint,
        )

        case_correct = 0
        case_slots = 0

        # Evaluate expected known attributes
        for slot_name, expected_val in case.expected_attributes.items():
            case_slots += 1
            total_slots += 1
            attr: ProfileAttribute = getattr(profile, slot_name, None)

            if attr and attr.is_known and attr.value == expected_val:
                correct_slots += 1
                case_correct += 1

        # Evaluate expected missing attributes
        for missing_slot in case.expected_missing:
            missing_total += 1
            attr: ProfileAttribute = getattr(profile, missing_slot, None)
            if attr and attr.state == AttributeState.NOT_PRESENT:
                missing_detected += 1
            elif attr and attr.is_known:
                false_extractions += 1

        # Evaluate expected conflicts
        for conflict_slot in case.expected_conflicts:
            conflicts_total += 1
            attr: ProfileAttribute = getattr(profile, conflict_slot, None)
            if attr and attr.state == AttributeState.CONFLICTING:
                conflicts_detected += 1

        case_summaries.append({
            "case_id": case.case_id,
            "case_type": case.case_type,
            "accuracy": round(case_correct / case_slots, 4) if case_slots > 0 else 1.0,
            "extraction_confidence": profile.extraction_confidence,
        })

    agreement_rate = (correct_slots / total_slots) if total_slots > 0 else 0.0
    missing_rate = (missing_detected / missing_total) if missing_total > 0 else 1.0
    conflict_rate = (conflicts_detected / conflicts_total) if conflicts_total > 0 else 1.0
    false_rate = (false_extractions / missing_total) if missing_total > 0 else 0.0

    return ExtractionBenchmarkMetrics(
        total_cases=total_cases,
        total_attribute_slots=total_slots,
        correctly_extracted_slots=correct_slots,
        agreement_rate=agreement_rate,
        missing_fields_total=missing_total,
        missing_fields_detected=missing_detected,
        missing_field_detection_rate=missing_rate,
        conflicts_total=conflicts_total,
        conflicts_detected=conflicts_detected,
        conflict_detection_rate=conflict_rate,
        false_extractions_total=false_extractions,
        false_extraction_rate=false_rate,
        case_summaries=case_summaries,
    )

