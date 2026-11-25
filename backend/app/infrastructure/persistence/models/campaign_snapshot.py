"""Local snapshots of campaigns created through this service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.models.base import Base


class CampaignSnapshot(Base):
    __tablename__ = "campaign_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(40))
    state: Mapped[str | None] = mapped_column(String(40))
    domain_id: Mapped[int | None]
    group_id: Mapped[int | None]
    traffic_source_id: Mapped[int | None]
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), nullable=False
    )
    streams: Mapped[list[StreamSnapshot]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class StreamSnapshot(Base):
    __tablename__ = "stream_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaign_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(40))
    schema: Mapped[str | None] = mapped_column(String(40))
    position: Mapped[int | None]
    state: Mapped[str | None] = mapped_column(String(40))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    campaign: Mapped[CampaignSnapshot] = relationship(back_populates="streams")
    offers: Mapped[list[StreamOfferSnapshot]] = relationship(
        back_populates="stream",
        cascade="all, delete-orphan",
    )


class StreamOfferSnapshot(Base):
    __tablename__ = "stream_offer_snapshots"

    stream_id: Mapped[int] = mapped_column(
        ForeignKey("stream_snapshots.id", ondelete="CASCADE"), primary_key=True
    )
    offer_id: Mapped[int] = mapped_column(primary_key=True)
    share: Mapped[int] = mapped_column(nullable=False)
    state: Mapped[str | None] = mapped_column(String(40))
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False)
    published_share: Mapped[int] = mapped_column(nullable=False)
    published_state: Mapped[str | None] = mapped_column(String(40))
    draft_share: Mapped[int] = mapped_column(nullable=False)
    draft_state: Mapped[str | None] = mapped_column(String(40))
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    stream: Mapped[StreamSnapshot] = relationship(back_populates="offers")
