"""
Engineering Knowledge & Validation Engine for OneMate.

Authoritative deterministic gate that diagnoses hard technical conflicts,
validates engineering equivalence rules, and enforces physical safety.
This engine overrides all statistical AI and semantic similarity scores.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.ai.profile import AttributeState, MaterialProfile, ProfileAttribute


@dataclass
class ValidationResult:
    """
    Authoritative evaluation output produced by the Engineering Knowledge & Validation Engine.
    """
    is_compatible: bool
    hard_conflicts: List[str] = field(default_factory=list)
    matching_attributes: List[str] = field(default_factory=list)
    missing_attributes: List[str] = field(default_factory=list)
    asymmetric_attributes: List[str] = field(default_factory=list)
    attribute_matrix: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    explanation: str = ""


class EngineeringKnowledgeEngine:
    """
    Authoritative domain rules engine enforcing industrial piping and equipment standards.
    Diagnoses hard incompatibilities across dimensions, pressure ratings, metallurgy,
    equipment categories, and connection geometries.
    """

    # --- Metallurgy Canonical Equivalence Groups ---
    _METALLURGY_CANONICAL = {
        "CS": "CARBON_STEEL",
        "C.S.": "CARBON_STEEL",
        "CARBON STEEL": "CARBON_STEEL",
        "WCB": "CARBON_STEEL",
        "CAST STEEL": "CARBON_STEEL",
        "A105": "CARBON_STEEL",
        "SS304": "SS304",
        "304SS": "SS304",
        "304 SS": "SS304",
        "SS 304": "SS304",
        "CF8": "SS304",
        "SS316": "SS316",
        "316SS": "SS316",
        "316 SS": "SS316",
        "SS 316": "SS316",
        "CF8M": "SS316",
        "SS316L": "SS316L",
        "316L": "SS316L",
        "CAST IRON": "CAST_IRON",
        "CI": "CAST_IRON",
        "BRASS": "BRASS",
        "BRONZE": "BRONZE",
        "MONEL": "MONEL",
        "INCONEL": "INCONEL",
        "DUPLEX": "DUPLEX_2205",
        "SUPER DUPLEX": "SUPER_DUPLEX_2507",
    }

    # Strict incompatible pairs (A, B) -> conflict
    _INCOMPATIBLE_METALLURGY_PAIRS: Set[Tuple[str, str]] = {
        ("CARBON_STEEL", "SS304"),
        ("CARBON_STEEL", "SS316"),
        ("CARBON_STEEL", "SS316L"),
        ("CARBON_STEEL", "CAST_IRON"),
        ("SS304", "SS316"),
        ("SS304", "SS316L"),
        ("SS316", "CARBON_STEEL"),
        ("SS316", "SS304"),
        ("CAST_IRON", "SS316"),
        ("CAST_IRON", "CARBON_STEEL"),
    }

    # --- Connection Incompatibilities ---
    _INCOMPATIBLE_CONNECTIONS: Set[Tuple[str, str]] = {
        ("NPT", "RF"),
        ("NPT", "FLANGED"),
        ("NPT", "SOCKET_WELD"),
        ("NPT", "BUTT_WELD"),
        ("RF", "SOCKET_WELD"),
        ("RF", "BUTT_WELD"),
        ("RF", "THREADED"),
        ("SOCKET_WELD", "BUTT_WELD"),
        ("FLANGED", "THREADED"),
    }

    @classmethod
    def canonicalize_metallurgy(cls, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        cleaned = raw.strip().upper()
        return cls._METALLURGY_CANONICAL.get(cleaned, cleaned)

    @classmethod
    def canonicalize_size(cls, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        cleaned = raw.strip().upper()
        # Direct DN xx
        m_dn = re.match(r'^DN\s*(\d+)$', cleaned)
        if m_dn:
            return f"DN{m_dn.group(1)}"
        # xx MM
        m_mm = re.match(r'^(\d+)\s*MM$', cleaned)
        if m_mm:
            return f"DN{m_mm.group(1)}"
        # Inch mapping
        inch_map = {
            "0.5 IN": "DN15", "1/2 IN": "DN15", "1/2\"": "DN15", "0.5\"": "DN15", "1/2": "DN15", "0.5": "DN15",
            "0.75 IN": "DN20", "3/4 IN": "DN20", "3/4\"": "DN20", "0.75\"": "DN20", "3/4": "DN20", "0.75": "DN20",
            "1 IN": "DN25", "1\"": "DN25", "1": "DN25",
            "1.5 IN": "DN40", "1-1/2 IN": "DN40", "1 1/2 IN": "DN40", "1.5\"": "DN40", "1.5": "DN40",
            "2 IN": "DN50", "2\"": "DN50", "2": "DN50",
            "3 IN": "DN80", "3\"": "DN80", "3": "DN80",
            "4 IN": "DN100", "4\"": "DN100", "4": "DN100",
            "6 IN": "DN150", "6\"": "DN150", "6": "DN150",
            "8 IN": "DN200", "8\"": "DN200", "8": "DN200",
            "10 IN": "DN250", "10\"": "DN250", "10": "DN250",
            "12 IN": "DN300", "12\"": "DN300", "12": "DN300",
        }
        return inch_map.get(cleaned, cleaned)

    @classmethod
    def canonicalize_pressure(cls, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        cleaned = raw.strip().upper()
        # Handle CLASS/CL/LBS/#
        m_cl = re.match(r'^(?:CLASS|CL)\s*(\d+)$', cleaned)
        if m_cl:
            return f"CLASS{m_cl.group(1)}"
        m_hash = re.match(r'^(\d+)\s*(?:#|LBS|LB)$', cleaned)
        if m_hash:
            return f"CLASS{m_hash.group(1)}"
        # Handle PSI
        m_psi = re.match(r'^(\d+)\s*PSI$', cleaned)
        if m_psi:
            return f"{m_psi.group(1)}PSI"
        # Handle PN
        m_pn = re.match(r'^PN\s*(\d+)$', cleaned)
        if m_pn:
            return f"PN{m_pn.group(1)}"
        return cleaned

    @classmethod
    def validate_profiles(
        cls,
        source: MaterialProfile,
        candidate: MaterialProfile,
    ) -> ValidationResult:
        """
        Authoritatively evaluates compatibility between two structured material profiles.
        Detects hard physical engineering conflicts and asymmetric missing attributes.
        """
        hard_conflicts: List[str] = []
        matches: List[str] = []
        missing: List[str] = []
        asymmetric: List[str] = []
        matrix: Dict[str, Dict[str, Any]] = {}

        # 1. Equipment Category Check
        cat_src = source.category.value if source.category.is_known else None
        cat_cand = candidate.category.value if candidate.category.is_known else None
        if cat_src and cat_cand and cat_src != cat_cand:
            hard_conflicts.append(f"Category mismatch: {cat_src} vs {cat_cand}")
            matrix["category"] = {"source": cat_src, "candidate": cat_cand, "match": False, "conflict": True}
        elif cat_src and cat_cand and cat_src == cat_cand:
            matches.append("category")
            matrix["category"] = {"source": cat_src, "candidate": cat_cand, "match": True, "conflict": False}

        # 2. Material / Component Type Check (e.g. BALL vs GATE)
        type_src = source.material_type.value if source.material_type.is_known else None
        type_cand = candidate.material_type.value if candidate.material_type.is_known else None
        if type_src and type_cand:
            if type_src == type_cand:
                matches.append("material_type")
                matrix["material_type"] = {"source": type_src, "candidate": type_cand, "match": True, "conflict": False}
            else:
                hard_conflicts.append(f"Type conflict: {type_src} vs {type_cand}")
                matrix["material_type"] = {"source": type_src, "candidate": type_cand, "match": False, "conflict": True}
        elif type_src or type_cand:
            asymmetric.append("material_type")
            matrix["material_type"] = {"source": type_src, "candidate": type_cand, "match": None, "conflict": False}
        else:
            missing.append("material_type")

        # 3. Size / Dimension Check
        size_src = cls.canonicalize_size(source.size.value if source.size.is_known else None)
        size_cand = cls.canonicalize_size(candidate.size.value if candidate.size.is_known else None)
        if size_src and size_cand:
            if size_src == size_cand:
                matches.append("size")
                matrix["size"] = {"source": size_src, "candidate": size_cand, "match": True, "conflict": False}
            else:
                hard_conflicts.append(f"Size conflict: {size_src} vs {size_cand}")
                matrix["size"] = {"source": size_src, "candidate": size_cand, "match": False, "conflict": True}
        elif size_src or size_cand:
            asymmetric.append("size")
            matrix["size"] = {"source": size_src, "candidate": size_cand, "match": None, "conflict": False}
        else:
            missing.append("size")

        # 4. Pressure Rating Check
        press_src = cls.canonicalize_pressure(source.pressure_rating.value if source.pressure_rating.is_known else None)
        press_cand = cls.canonicalize_pressure(candidate.pressure_rating.value if candidate.pressure_rating.is_known else None)
        if press_src and press_cand:
            if press_src == press_cand:
                matches.append("pressure_rating")
                matrix["pressure_rating"] = {"source": press_src, "candidate": press_cand, "match": True, "conflict": False}
            else:
                hard_conflicts.append(f"Pressure rating conflict: {press_src} vs {press_cand}")
                matrix["pressure_rating"] = {"source": press_src, "candidate": press_cand, "match": False, "conflict": True}
        elif press_src or press_cand:
            asymmetric.append("pressure_rating")
            matrix["pressure_rating"] = {"source": press_src, "candidate": press_cand, "match": None, "conflict": False}
        else:
            missing.append("pressure_rating")

        # 5. Body Material Metallurgy Check
        body_src = cls.canonicalize_metallurgy(source.material_grade.value if source.material_grade.is_known else None)
        body_cand = cls.canonicalize_metallurgy(candidate.material_grade.value if candidate.material_grade.is_known else None)
        if body_src and body_cand:
            if body_src == body_cand:
                matches.append("material_grade")
                matrix["material_grade"] = {"source": body_src, "candidate": body_cand, "match": True, "conflict": False}
            else:
                hard_conflicts.append(f"Material metallurgy conflict: {body_src} vs {body_cand}")
                matrix["material_grade"] = {"source": body_src, "candidate": body_cand, "match": False, "conflict": True}
        elif body_src or body_cand:
            asymmetric.append("material_grade")
            matrix["material_grade"] = {"source": body_src, "candidate": body_cand, "match": None, "conflict": False}
        else:
            missing.append("material_grade")

        # 6. Connection Type Check
        conn_src = source.connection_type.value if source.connection_type.is_known else None
        conn_cand = candidate.connection_type.value if candidate.connection_type.is_known else None
        if conn_src and conn_cand:
            if conn_src == conn_cand:
                matches.append("connection_type")
                matrix["connection_type"] = {"source": conn_src, "candidate": conn_cand, "match": True, "conflict": False}
            elif (conn_src, conn_cand) in cls._INCOMPATIBLE_CONNECTIONS or (conn_cand, conn_src) in cls._INCOMPATIBLE_CONNECTIONS:
                hard_conflicts.append(f"Connection type conflict: {conn_src} vs {conn_cand}")
                matrix["connection_type"] = {"source": conn_src, "candidate": conn_cand, "match": False, "conflict": True}
            else:
                hard_conflicts.append(f"Connection mismatch: {conn_src} vs {conn_cand}")
                matrix["connection_type"] = {"source": conn_src, "candidate": conn_cand, "match": False, "conflict": True}
        elif conn_src or conn_cand:
            asymmetric.append("connection_type")
            matrix["connection_type"] = {"source": conn_src, "candidate": conn_cand, "match": None, "conflict": False}
        else:
            missing.append("connection_type")

        # 7. Trim Material Metallurgy Check
        trim_src = cls.canonicalize_metallurgy(source.trim_material.value if source.trim_material.is_known else None)
        trim_cand = cls.canonicalize_metallurgy(candidate.trim_material.value if candidate.trim_material.is_known else None)
        if trim_src and trim_cand:
            if trim_src == trim_cand:
                matches.append("trim_material")
                matrix["trim_material"] = {"source": trim_src, "candidate": trim_cand, "match": True, "conflict": False}
            else:
                hard_conflicts.append(f"Trim metallurgy conflict: {trim_src} vs {trim_cand}")
                matrix["trim_material"] = {"source": trim_src, "candidate": trim_cand, "match": False, "conflict": True}
        elif trim_src or trim_cand:
            asymmetric.append("trim_material")
            matrix["trim_material"] = {"source": trim_src, "candidate": trim_cand, "match": None, "conflict": False}
        else:
            missing.append("trim_material")

        # 8. Category-Specific Domain Attributes (e.g. Strainer Mesh)
        mesh_src = source.additional_attributes.get("mesh")
        mesh_cand = candidate.additional_attributes.get("mesh")
        m_src_val = mesh_src.value if mesh_src and mesh_src.is_known else None
        m_cand_val = mesh_cand.value if mesh_cand and mesh_cand.is_known else None

        if m_src_val and m_cand_val:
            if m_src_val == m_cand_val:
                matches.append("mesh")
                matrix["mesh"] = {"source": m_src_val, "candidate": m_cand_val, "match": True, "conflict": False}
            else:
                hard_conflicts.append(f"Mesh conflict: {m_src_val} vs {m_cand_val}")
                matrix["mesh"] = {"source": m_src_val, "candidate": m_cand_val, "match": False, "conflict": True}
        elif m_src_val or m_cand_val:
            if cat_src == "STRAINER" or cat_cand == "STRAINER":
                asymmetric.append("mesh")
                matrix["mesh"] = {"source": m_src_val, "candidate": m_cand_val, "match": None, "conflict": False}
        elif cat_src == "STRAINER" or cat_cand == "STRAINER":
            missing.append("mesh")

        # 9. Seat / Liner Material Check (where applicable)
        seat_src = source.seat_material.value if source.seat_material.is_known else None
        seat_cand = candidate.seat_material.value if candidate.seat_material.is_known else None
        if seat_src and seat_cand:
            if seat_src == seat_cand:
                matches.append("seat_material")
                matrix["seat_material"] = {"source": seat_src, "candidate": seat_cand, "match": True, "conflict": False}
            else:
                hard_conflicts.append(f"Seat material conflict: {seat_src} vs {seat_cand}")
                matrix["seat_material"] = {"source": seat_src, "candidate": seat_cand, "match": False, "conflict": True}
        elif seat_src or seat_cand:
            asymmetric.append("seat_material")
            matrix["seat_material"] = {"source": seat_src, "candidate": seat_cand, "match": None, "conflict": False}

        # Synthesis of compatibility
        is_compatible = (len(hard_conflicts) == 0)

        if hard_conflicts:
            explanation = f"Hard engineering conflicts: {'; '.join(hard_conflicts)}."
        elif asymmetric:
            explanation = f"Compatible attributes ({', '.join(matches)}) with asymmetric missing specifications ({', '.join(asymmetric)})."
        elif matches:
            explanation = f"Confirmed engineering match across: {', '.join(matches)}."
        else:
            explanation = "Insufficient attribute evidence to determine equivalence."

        return ValidationResult(
            is_compatible=is_compatible,
            hard_conflicts=hard_conflicts,
            matching_attributes=matches,
            missing_attributes=missing,
            asymmetric_attributes=asymmetric,
            attribute_matrix=matrix,
            explanation=explanation,
        )

    @classmethod
    def validate_materials(cls, source_material: Any, candidate_material: Any) -> ValidationResult:
        """Helper to validate directly from SQLAlchemy Material model instances."""
        p_src = MaterialProfile.from_material(source_material)
        p_cand = MaterialProfile.from_material(candidate_material)
        return cls.validate_profiles(p_src, p_cand)

