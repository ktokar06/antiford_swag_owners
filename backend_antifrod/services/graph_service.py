from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.models.graph import GraphCluster, GraphClusterMember, GraphClusterRegion
from core.models.subscriber import PhoneNumber
from core.schemas.graph import ClusterListOut, ClusterOut
from core.utils.pagination import page, resolve_offset

SORTS = {
    "number_count": GraphCluster.number_count,
    "target_count": GraphCluster.target_count,
    "overlap_share": GraphCluster.overlap_share,
    "id": GraphCluster.id,
}


def _to_out(db: Session, cluster: GraphCluster) -> ClusterOut:
    numbers = db.execute(
        select(PhoneNumber.number)
        .join(GraphClusterMember, GraphClusterMember.phone_number_id == PhoneNumber.id)
        .where(GraphClusterMember.cluster_id == cluster.id)
        .order_by(PhoneNumber.number)
    ).scalars().all()
    regions = db.execute(
        select(GraphClusterRegion.region_code).where(GraphClusterRegion.cluster_id == cluster.id)
        .order_by(GraphClusterRegion.region_code)
    ).scalars().all()
    return ClusterOut(
        id=cluster.id,
        label=cluster.label,
        pattern=cluster.pattern,
        risk_level=cluster.risk_level,
        template=cluster.template,
        number_count=cluster.number_count,
        target_count=cluster.target_count,
        overlap_share=float(cluster.overlap_share or 0),
        numbers=[n.strip() for n in numbers],
        regions=list(regions),
    )


def list_clusters(db: Session, f: dict) -> ClusterListOut:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    sort = f.get("sort") or "-number_count"
    col = SORTS.get(sort.lstrip("-"), GraphCluster.number_count)
    stmt = select(GraphCluster)
    if f.get("label"):
        stmt = stmt.where(GraphCluster.label == f["label"])
    if f.get("risk_level"):
        stmt = stmt.where(GraphCluster.risk_level == f["risk_level"])
    stmt = stmt.order_by(col.desc() if sort.startswith("-") else col.asc(), GraphCluster.id).offset(offset)
    rows, next_cursor, has_more = page(db.execute(stmt.limit(limit + 1)).scalars().all(), limit, offset)
    return ClusterListOut(items=[_to_out(db, c) for c in rows], next_cursor=next_cursor,
                          has_more=has_more, offset=offset)


def count_clusters(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(GraphCluster)) or 0)


def get_cluster(db: Session, cluster_id: int) -> ClusterOut:
    cluster = db.get(GraphCluster, cluster_id)
    if cluster is None:
        raise HTTPException(404, "Кластер не найден")
    return _to_out(db, cluster)
