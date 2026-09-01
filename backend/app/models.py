import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def utc_now() -> datetime:
    """Returns current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class CPSE(Base):
    __tablename__ = "cpse"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    materials = relationship("Material", back_populates="cpse")


class Material(Base):
    __tablename__ = "material"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpse_id = Column(UUID(as_uuid=True), ForeignKey("cpse.id", ondelete="RESTRICT"), nullable=False)

    source_material_code = Column(String(100), nullable=False)
    source_description = Column(Text, nullable=False)
    source_uom = Column(String(50), nullable=False)
    source_specifications = Column(Text, nullable=True)
    raw_source_data = Column(JSONB, nullable=True)

    category = Column(String(50), nullable=True)

    valve_type = Column(String(100), nullable=True)
    size = Column(String(100), nullable=True)
    body_material = Column(String(100), nullable=True)
    pressure_class = Column(String(100), nullable=True)
    connection_type = Column(String(100), nullable=True)
    trim = Column(String(100), nullable=True)

    normalized_uom = Column(String(50), nullable=True)
    normalized_description = Column(Text, nullable=True)
    normalized_attributes = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    cpse = relationship("CPSE", back_populates="materials")
    mappings = relationship("MaterialNationalMapping", back_populates="material")

    __table_args__ = (
        UniqueConstraint("cpse_id", "source_material_code", name="uq_material_cpse_source_code"),
        CheckConstraint("category IS NULL OR category IN ('VALVE', 'PUMP', 'GASKET', 'FLANGE', 'BEARING', 'FASTENER')", name="chk_material_category_valid"),
        Index("ix_material_cpse_id", "cpse_id"),
        Index("ix_material_category", "category"),
    )


class NationalMaterial(Base):
    __tablename__ = "national_material"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    national_code = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=False)
    canonical_description = Column(Text, nullable=False)

    valve_type = Column(String(100), nullable=False)
    size = Column(String(100), nullable=False)
    body_material = Column(String(100), nullable=False)
    pressure_class = Column(String(100), nullable=False)
    connection_type = Column(String(100), nullable=False)
    trim = Column(String(100), nullable=False)
    normalized_uom = Column(String(50), nullable=False)

    identity_key = Column(String(500), unique=True, nullable=False)
    status = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    mappings = relationship("MaterialNationalMapping", back_populates="national_material")

    __table_args__ = (
        CheckConstraint("category = 'VALVE'", name="chk_national_material_category_valve"),
    )


class MatchRecommendation(Base):
    __tablename__ = "match_recommendation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_material_id = Column(UUID(as_uuid=True), ForeignKey("material.id", ondelete="RESTRICT"), nullable=False)
    candidate_material_id = Column(UUID(as_uuid=True), ForeignKey("material.id", ondelete="RESTRICT"), nullable=False)
    classification = Column(String(50), nullable=False)
    confidence = Column(Numeric, nullable=True)
    evidence = Column(JSONB, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("source_material_id != candidate_material_id", name="chk_recommendation_not_self"),
        CheckConstraint("classification IN ('SAME', 'POTENTIALLY_EQUIVALENT', 'DIFFERENT')", name="chk_recommendation_classification"),
        Index("ix_match_rec_source_candidate", "source_material_id", "candidate_material_id"),
        Index("ix_match_rec_source", "source_material_id"),
        Index("ix_match_rec_candidate", "candidate_material_id"),
        Index("ix_match_rec_classification", "classification"),
    )


class MaterialNationalMapping(Base):
    __tablename__ = "material_national_mapping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("material.id", ondelete="RESTRICT"), nullable=False)
    national_material_id = Column(UUID(as_uuid=True), ForeignKey("national_material.id", ondelete="RESTRICT"), nullable=False)
    basis = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("match_recommendation.id", ondelete="RESTRICT"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    material = relationship("Material", back_populates="mappings")
    national_material = relationship("NationalMaterial", back_populates="mappings")

    __table_args__ = (
        CheckConstraint("basis IN ('AUTO_SAME', 'HUMAN_CONFIRMED_SAME', 'HUMAN_OVERRIDE')", name="chk_mapping_basis"),
        CheckConstraint("status IN ('ACTIVE', 'SUPERSEDED', 'INACTIVE')", name="chk_mapping_status"),
        Index("idx_unique_active_mapping", "material_id", unique=True, postgresql_where=text("status = 'ACTIVE'")),
        Index("ix_mapping_material_id", "material_id"),
        Index("ix_mapping_national_material_id", "national_material_id"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    before_state = Column(JSONB, nullable=True)
    after_state = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created_at", "created_at"),
    )
