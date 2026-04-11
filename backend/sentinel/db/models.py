import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Bom(Base):
    __tablename__ = "boms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    program: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[str | None] = mapped_column(String(50))
    source_filename: Mapped[str | None] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    component_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_score_overall: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    components: Mapped[list["Component"]] = relationship(back_populates="bom", cascade="all, delete-orphan")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="bom", cascade="all, delete-orphan")


class Component(Base):
    __tablename__ = "components"
    __table_args__ = (
        UniqueConstraint("bom_id", "mpn_normalized", "reference_designator"),
        Index("idx_components_mpn", "mpn_normalized"),
        Index("idx_components_bom", "bom_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="CASCADE"), nullable=False)
    reference_designator: Mapped[str | None] = mapped_column(String(100))
    mpn: Mapped[str] = mapped_column(String(255), nullable=False)
    mpn_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    category: Mapped[str | None] = mapped_column(String(100))
    package: Mapped[str | None] = mapped_column(String(100))
    value: Mapped[str | None] = mapped_column(String(100))
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bom: Mapped["Bom"] = relationship(back_populates="components")
    enrichment_records: Mapped[list["EnrichmentRecord"]] = relationship(back_populates="component", cascade="all, delete-orphan")
    risk_scores: Mapped[list["RiskScoreRecord"]] = relationship(back_populates="component", cascade="all, delete-orphan")


class EnrichmentRecord(Base):
    __tablename__ = "enrichment_records"
    __table_args__ = (
        Index("idx_enrichment_component", "component_id"),
        Index("idx_enrichment_source", "source", "fetched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    lifecycle_status: Mapped[str | None] = mapped_column(String(50))
    yteol: Mapped[float | None] = mapped_column(Float)
    total_inventory: Mapped[int | None] = mapped_column(Integer)
    avg_lead_time_days: Mapped[int | None] = mapped_column(Integer)
    distributor_count: Mapped[int | None] = mapped_column(Integer)
    num_alternates: Mapped[int | None] = mapped_column(Integer)
    country_of_origin: Mapped[str | None] = mapped_column(String(100))
    single_source: Mapped[bool | None] = mapped_column(Boolean)
    rohs_compliant: Mapped[bool | None] = mapped_column(Boolean)
    reach_compliant: Mapped[bool | None] = mapped_column(Boolean)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    component: Mapped["Component"] = relationship(back_populates="enrichment_records")


class RiskScoreRecord(Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        Index("idx_risk_component", "component_id", "scored_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    profile: Mapped[str] = mapped_column(String(50), default="default")
    lifecycle_risk: Mapped[float] = mapped_column(Float, nullable=False)
    supply_risk: Mapped[float] = mapped_column(Float, nullable=False)
    geographic_risk: Mapped[float] = mapped_column(Float, nullable=False)
    supplier_risk: Mapped[float] = mapped_column(Float, nullable=False)
    regulatory_risk: Mapped[float] = mapped_column(Float, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_factors: Mapped[list] = mapped_column(JSONB, default=list)
    recommendation: Mapped[str | None] = mapped_column(Text)

    component: Mapped["Component"] = relationship(back_populates="risk_scores")


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="CASCADE"), nullable=False)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)

    bom: Mapped["Bom"] = relationship(back_populates="snapshots")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    affected_bom_ids: Mapped[list | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    results: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="draft")
