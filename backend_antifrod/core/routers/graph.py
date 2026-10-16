from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from core.schemas.graph import ClusterListOut, ClusterOut
from services import graph_service

router = APIRouter(prefix="/graph", tags=["graph"], dependencies=[Depends(get_current_user)])


@router.get("/clusters", response_model=ClusterListOut)
def list_clusters(
        label: str | None = Query(None, max_length=120),
        risk_level: str | None = Query(None, pattern="^(low|medium|high)$"),
        sort: str = "-number_count",
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return graph_service.list_clusters(db, {"label": label, "risk_level": risk_level, "sort": sort,
                                            "limit": limit, "offset": offset, "cursor": cursor})


@router.get("/clusters/count")
def count_clusters(db: Session = Depends(get_db_dep)) -> int:
    return graph_service.count_clusters(db)


@router.get("/clusters/{cluster_id}", response_model=ClusterOut)
def get_cluster(cluster_id: int, db: Session = Depends(get_db_dep)):
    return graph_service.get_cluster(db, cluster_id)
