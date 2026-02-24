import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Sport(Base):
    __tablename__ = "app_sports_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OrgType(str, Enum):
    COUNTRY = "country"
    CLUB = "club"


class Org(Base):
    __tablename__ = "app_orgs_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    type: Mapped[OrgType] = mapped_column(String(16), nullable=False)
    parent_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_orgs_registry.id", ondelete="CASCADE"),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OrgSportPresence(Base):
    __tablename__ = "app_org_sport_presence"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "sport_id", name="uq__app_org_sport_presence__org__sport"
        ),
    )

    # fields
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sport_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_sports_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # local ID on the sport-specific DB
    # TODO. the sport-specific DB should have a reference to the primary key of this table as well (1:1)
    sport_local_ref: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_orgs_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # relationships
    sport = relationship(Sport, lazy="joined")
    org = relationship(Org, lazy="joined")
