"""
Structured Material Profile representation for OneMate AI.

Implements the 4-state attribute representation (KNOWN_VALUE, UNKNOWN, NOT_PRESENT, CONFLICTING)
and canonical data structures for material intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AttributeState(str, Enum):
    """
    Four-state discriminator for engineering attributes.
    Preserves the distinction between missing, explicitly unknown, conflicting, and known values.
    """
    KNOWN_VALUE = "KNOWN_VALUE"
    UNKNOWN = "UNKNOWN"
    NOT_PRESENT = "NOT_PRESENT"
    CONFLICTING = "CONFLICTING"


@dataclass
class ProfileAttribute:
    """
    Represents a single extracted engineering attribute with provenance and certainty.
    """
    value: Optional[str] = None
    raw_token: Optional[str] = None
    state: AttributeState = AttributeState.NOT_PRESENT
    confidence: float = 0.0

    @classmethod
    def known(cls, value: str, raw_token: Optional[str] = None, confidence: float = 1.0) -> ProfileAttribute:
        """Factory for a confirmed attribute."""
        return cls(
            value=value.strip().upper() if value else None,
            raw_token=raw_token,
            state=AttributeState.KNOWN_VALUE,
            confidence=confidence,
        )

    @classmethod
    def unknown(cls, raw_token: Optional[str] = None) -> ProfileAttribute:
        """Factory for an attribute explicitly mentioned as unknown or unspecified."""
        return cls(
            value=None,
            raw_token=raw_token,
            state=AttributeState.UNKNOWN,
            confidence=0.0,
        )

    @classmethod
    def not_present(cls) -> ProfileAttribute:
        """Factory for an attribute completely omitted from the source text."""
        return cls(
            value=None,
            raw_token=None,
            state=AttributeState.NOT_PRESENT,
            confidence=0.0,
        )

    @classmethod
    def conflicting(cls, raw_token: Optional[str] = None) -> ProfileAttribute:
        """Factory for self-contradictory mentions within the same text."""
        return cls(
            value=None,
            raw_token=raw_token,
            state=AttributeState.CONFLICTING,
            confidence=0.0,
        )

    @property
    def is_known(self) -> bool:
        return self.state == AttributeState.KNOWN_VALUE and self.value is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "raw_token": self.raw_token,
            "state": self.state.value,
            "confidence": round(self.confidence, 4),
        }

    @classmethod
    def from_dict(cls, data: Optional[Any]) -> ProfileAttribute:
        if data is None:
            return cls.not_present()
        if isinstance(data, str):
            if not data or data.strip() == "":
                return cls.not_present()
            if data.strip().upper() == "UNKNOWN":
                return cls.unknown()
            return cls.known(data)
        if not isinstance(data, dict):
            return cls.not_present()
        state_str = data.get("state", AttributeState.NOT_PRESENT.value)
        try:
            state = AttributeState(state_str)
        except ValueError:
            state = AttributeState.UNKNOWN if data.get("value") == "UNKNOWN" else AttributeState.NOT_PRESENT

        return cls(
            value=data.get("value"),
            raw_token=data.get("raw_token"),
            state=state,
            confidence=float(data.get("confidence", 0.0)),
        )


@dataclass
class MaterialProfile:
    """
    Canonical, structured engineering profile for a material record.
    Provides lossless translation to/from Material.normalized_attributes JSONB.
    """
    category: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    material_type: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    component_type: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    size: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    pressure_rating: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    material_grade: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    connection_type: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    trim_material: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    seat_material: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    normalized_uom: ProfileAttribute = field(default_factory=ProfileAttribute.not_present)
    additional_attributes: Dict[str, ProfileAttribute] = field(default_factory=dict)
    extraction_confidence: float = 0.0
    provenance_tokens: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes profile to a dictionary for JSONB storage."""
        return {
            "schema_version": "2.0",
            "category": self.category.to_dict(),
            "material_type": self.material_type.to_dict(),
            "component_type": self.component_type.to_dict(),
            "size": self.size.to_dict(),
            "pressure_rating": self.pressure_rating.to_dict(),
            "material_grade": self.material_grade.to_dict(),
            "connection_type": self.connection_type.to_dict(),
            "trim_material": self.trim_material.to_dict(),
            "seat_material": self.seat_material.to_dict(),
            "normalized_uom": self.normalized_uom.to_dict(),
            "additional_attributes": {k: v.to_dict() for k, v in self.additional_attributes.items()},
            "extraction_confidence": round(self.extraction_confidence, 4),
            "provenance_tokens": list(self.provenance_tokens),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> MaterialProfile:
        """Constructs profile from JSONB dictionary."""
        if not data or not isinstance(data, dict):
            return cls()

        extra = {}
        for k, v in data.get("additional_attributes", {}).items():
            extra[k] = ProfileAttribute.from_dict(v)

        # Handle both MaterialProfile to_dict format and flat normalized_attributes format
        category = ProfileAttribute.from_dict(data.get("category"))
        material_type = ProfileAttribute.from_dict(data.get("material_type") or data.get("valve_type") or data.get("type"))
        size = ProfileAttribute.from_dict(data.get("size"))
        pressure_rating = ProfileAttribute.from_dict(data.get("pressure_rating") or data.get("pressure_class"))
        material_grade = ProfileAttribute.from_dict(data.get("material_grade") or data.get("body_material"))
        connection_type = ProfileAttribute.from_dict(data.get("connection_type") or data.get("facing_connection"))
        trim_material = ProfileAttribute.from_dict(data.get("trim_material") or data.get("trim"))
        seat_material = ProfileAttribute.from_dict(data.get("seat_material") or data.get("liner_material"))
        normalized_uom = ProfileAttribute.from_dict(data.get("normalized_uom"))

        # Also populate additional_attributes from any extra keys in flat normalized_attributes
        known_keys = {
            "schema_version", "category", "material_type", "valve_type", "type",
            "size", "pressure_rating", "pressure_class", "material_grade", "body_material",
            "connection_type", "facing_connection", "trim_material", "trim", "seat_material",
            "liner_material", "normalized_uom", "additional_attributes", "extraction_confidence",
            "provenance_tokens", "component_type"
        }
        for k, v in data.items():
            if k not in known_keys and k not in extra:
                extra[k] = ProfileAttribute.from_dict(v)

        component_type = ProfileAttribute.from_dict(data.get("component_type"))
        if not component_type.is_known:
            comp_type_val = None
            if category.value == "VALVE" and material_type.value:
                comp_type_val = f"{material_type.value} VALVE"
            elif category.value:
                comp_type_val = category.value
            if comp_type_val:
                component_type = ProfileAttribute.known(comp_type_val)

        return cls(
            category=category,
            material_type=material_type,
            component_type=component_type,
            size=size,
            pressure_rating=pressure_rating,
            material_grade=material_grade,
            connection_type=connection_type,
            trim_material=trim_material,
            seat_material=seat_material,
            normalized_uom=normalized_uom,
            additional_attributes=extra,
            extraction_confidence=float(data.get("extraction_confidence", 0.8 if any([category.is_known, size.is_known]) else 0.0)),
            provenance_tokens=list(data.get("provenance_tokens", [])),
        )

    @classmethod
    def from_material(cls, material: Any) -> MaterialProfile:
        """
        Builds a MaterialProfile from an existing SQLAlchemy Material model.
        Seamlessly uses normalized_attributes if populated, or maps from direct columns.
        """
        raw_attrs = getattr(material, "normalized_attributes", None)
        if raw_attrs and isinstance(raw_attrs, dict):
            profile = cls.from_dict(raw_attrs)
            # Overlay table columns if profile attribute is not present
            if not profile.category.is_known and getattr(material, "category", None):
                profile.category = ProfileAttribute.known(material.category)
            if not profile.size.is_known and getattr(material, "size", None):
                profile.size = ProfileAttribute.known(material.size)
            if not profile.pressure_rating.is_known and getattr(material, "pressure_class", None):
                profile.pressure_rating = ProfileAttribute.known(material.pressure_class)
            if not profile.material_grade.is_known and getattr(material, "body_material", None):
                profile.material_grade = ProfileAttribute.known(material.body_material)
            if not profile.connection_type.is_known and getattr(material, "connection_type", None):
                profile.connection_type = ProfileAttribute.known(material.connection_type)
            if not profile.trim_material.is_known and getattr(material, "trim", None):
                profile.trim_material = ProfileAttribute.known(material.trim)
            if not profile.material_type.is_known and getattr(material, "valve_type", None):
                profile.material_type = ProfileAttribute.known(material.valve_type)
            if not profile.normalized_uom.is_known and getattr(material, "normalized_uom", None):
                profile.normalized_uom = ProfileAttribute.known(material.normalized_uom)
            return profile

        # Fall back to mapping directly from Material table columns
        def col_attr(val: Optional[str]) -> ProfileAttribute:
            if not val:
                return ProfileAttribute.not_present()
            if val.upper() == "UNKNOWN":
                return ProfileAttribute.unknown()
            return ProfileAttribute.known(val)

        cat = col_attr(getattr(material, "category", None))
        m_type = col_attr(getattr(material, "valve_type", None))
        size = col_attr(getattr(material, "size", None))
        press = col_attr(getattr(material, "pressure_class", None))
        body = col_attr(getattr(material, "body_material", None))
        conn = col_attr(getattr(material, "connection_type", None))
        trim = col_attr(getattr(material, "trim", None))
        uom = col_attr(getattr(material, "normalized_uom", None))

        comp_type_val = None
        if cat.value == "VALVE" and m_type.value:
            comp_type_val = f"{m_type.value} VALVE"
        elif cat.value:
            comp_type_val = cat.value
        comp = col_attr(comp_type_val)

        return cls(
            category=cat,
            material_type=m_type,
            component_type=comp,
            size=size,
            pressure_rating=press,
            material_grade=body,
            connection_type=conn,
            trim_material=trim,
            normalized_uom=uom,
            extraction_confidence=0.8 if any([cat.is_known, size.is_known]) else 0.0,
        )

    def to_canonical_string(self) -> str:
        """
        Constructs a structured, standardized canonical representation
        for input into the semantic embedding model.
        """
        parts = []
        if self.category.is_known:
            parts.append(self.category.value)
        if self.material_type.is_known and self.material_type.value != self.category.value:
            parts.append(self.material_type.value)
        if self.size.is_known:
            parts.append(self.size.value)
        if self.material_grade.is_known:
            parts.append(self.material_grade.value)
        if self.pressure_rating.is_known:
            parts.append(self.pressure_rating.value)
        if self.connection_type.is_known:
            parts.append(self.connection_type.value)
        if self.trim_material.is_known:
            parts.append(f"TRIM {self.trim_material.value}")
        if self.seat_material.is_known:
            parts.append(f"SEAT {self.seat_material.value}")
        return " ".join(parts).strip()

    def get_missing_attributes(self, required_slots: Optional[List[str]] = None) -> List[str]:
        """Returns slot names that are not known values."""
        if required_slots is None:
            required_slots = [
                "category",
                "material_type",
                "size",
                "pressure_rating",
                "material_grade",
                "connection_type",
                "trim_material",
            ]
        missing = []
        for slot in required_slots:
            attr: ProfileAttribute = getattr(self, slot, None)
            if not attr or not attr.is_known:
                missing.append(slot)
        return missing

    def has_complete_identity(self, required_slots: Optional[List[str]] = None) -> bool:
        """Returns True only if all required slots have confirmed KNOWN_VALUE state."""
        return len(self.get_missing_attributes(required_slots)) == 0

