from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class GraphCluster(Base):
    __tablename__ = "graph_cluster"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    pattern: Mapped[str] = mapped_column(String(40), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), default="low", nullable=False)
    template: Mapped[str | None] = mapped_column(String)
    number_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overlap_share: Mapped[float] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GraphClusterMember(Base):
    __tablename__ = "graph_cluster_member"
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("graph_cluster.id", ondelete="CASCADE"), primary_key=True
    )
    phone_number_id: Mapped[int] = mapped_column(
        ForeignKey("phone_number.id", ondelete="CASCADE"), primary_key=True
    )


class GraphClusterTarget(Base):
    __tablename__ = "graph_cluster_target"
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("graph_cluster.id", ondelete="CASCADE"), primary_key=True
    )
    target_number_id: Mapped[int] = mapped_column(
        ForeignKey("phone_number.id", ondelete="CASCADE"), primary_key=True
    )


class GraphClusterRegion(Base):
    __tablename__ = "graph_cluster_region"
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("graph_cluster.id", ondelete="CASCADE"), primary_key=True
    )
    region_code: Mapped[str] = mapped_column(String(10), primary_key=True)