"""
Поиск «вееров» в графе связей.

Кандидаты (SQL): номера с большим числом коротких исходящих вызовов на много разных адресатов.
Группировка (Python): кандидаты объединяются, если их списки целей похожи (Jaccard).
Для каждой группы считаются пересечение списков целей и регионы обзвона.

Запуск: python -m etl.refresh_graph
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models.graph import GraphCluster

MIN_SOURCE_CALLS = 5
MIN_TARGETS = 20
SHORT_CALL_SEC = 10
MIN_SHORT_SHARE = 0.60
MIN_JACCARD = 0.20
MIN_GROUP_SIZE = 3

CANDIDATES_SQL = """
SELECT caller_number, avg((duration_sec <= :short)::int) AS short_share
FROM call_record WHERE is_valid
GROUP BY caller_number
HAVING count(*) >= :min_calls
   AND count(DISTINCT callee_number) >= :min_targets
   AND avg((duration_sec <= :short)::int) >= :min_short
"""

PAIRS_SQL = f"""
SELECT c.caller_number, c.callee_number
FROM call_record c
JOIN ({CANDIDATES_SQL}) k ON k.caller_number = c.caller_number
WHERE c.is_valid
GROUP BY c.caller_number, c.callee_number
"""

PARAMS = {
    "short": SHORT_CALL_SEC, "min_calls": MIN_SOURCE_CALLS,
    "min_targets": MIN_TARGETS, "min_short": MIN_SHORT_SHARE,
}


def find_fans(sources: list[tuple[str, set[str], float]]) -> list[dict]:
    """sources: (номер, множество целей, доля коротких). Возвращает группы-веера."""
    fans: list[dict] = []
    used: set[str] = set()
    for num_a, targets_a, share_a in sources:
        if num_a in used:
            continue
        members = [num_a]
        sizes = [len(targets_a)]
        union = set(targets_a)
        shares = [share_a]
        for num_b, targets_b, share_b in sources:
            if num_b in used or num_b == num_a or num_b in members:
                continue
            inter = len(targets_a & targets_b)
            jaccard = inter / len(targets_a | targets_b) if (targets_a or targets_b) else 0
            if jaccard < MIN_JACCARD:
                continue
            members.append(num_b)
            sizes.append(len(targets_b))
            union |= targets_b
            shares.append(share_b)
        if len(members) < MIN_GROUP_SIZE:
            continue
        used.update(members)
        total = sum(sizes)
        fans.append({
            "members": members,
            "targets": sorted(union),
            "short_share": sum(shares) / len(shares),
            "overlap_share": (total - len(union)) / total if total else 0.0,
            "regions": sorted({t[:3] for t in union}),
        })
    return fans


def load_sources(db: Session) -> list[tuple[str, set[str], float]]:
    shares = {num: float(share) for num, share in db.execute(text(CANDIDATES_SQL), PARAMS).all()}
    targets: dict[str, set[str]] = {}
    for a, b in db.execute(text(PAIRS_SQL), PARAMS).all():
        targets.setdefault(a, set()).add(b)
    return [(num, targets.get(num, set()), share) for num, share in sorted(shares.items())]


def persist_clusters(db: Session, fans: list[dict]) -> int:
    db.execute(text("DELETE FROM graph_cluster"))
    db.execute(text(
        "UPDATE number_feature SET has_fan_pattern = FALSE, fan_group = NULL "
        "WHERE has_fan_pattern OR fan_group IS NOT NULL"
    ))

    for idx, fan in enumerate(fans, 1):
        share = round(fan["short_share"], 4)
        cluster = GraphCluster(
            label=f"Веер #{idx}",
            pattern="fan",
            risk_level="low",
            template=(
                f"Группа из {len(fan['members'])} номеров, доля коротких вызовов {share:.0%}, "
                f"целей обзвона {len(fan['targets'])}, регионов {len(fan['regions'])}."
            ),
            number_count=len(fan["members"]),
            target_count=len(fan["targets"]),
            overlap_share=round(fan["overlap_share"], 4),
        )
        db.add(cluster)
        db.flush()

        db.execute(
            text("INSERT INTO graph_cluster_member (cluster_id, phone_number_id) "
                 "SELECT :cid, id FROM phone_number WHERE number = :n ON CONFLICT DO NOTHING"),
            [{"cid": cluster.id, "n": n} for n in fan["members"]],
        )
        db.execute(
            text("INSERT INTO graph_cluster_target (cluster_id, target_number_id) "
                 "SELECT :cid, id FROM phone_number WHERE number = :n ON CONFLICT DO NOTHING"),
            [{"cid": cluster.id, "n": n} for n in fan["targets"]],
        )
        if fan["regions"]:
            db.execute(
                text("INSERT INTO graph_cluster_region (cluster_id, region_code) VALUES (:cid, :r) "
                     "ON CONFLICT DO NOTHING"),
                [{"cid": cluster.id, "r": r} for r in fan["regions"]],
            )
        db.execute(
            text("UPDATE number_feature nf SET has_fan_pattern = TRUE, fan_group = :label "
                 "FROM graph_cluster_member m "
                 "WHERE m.cluster_id = :cid AND nf.phone_number_id = m.phone_number_id"),
            {"cid": cluster.id, "label": cluster.label},
        )
    return len(fans)


def refresh_graph(db: Session) -> dict:
    sources = load_sources(db)
    fans = find_fans(sources)
    saved = persist_clusters(db, fans)
    db.execute(text("""
        UPDATE graph_cluster g SET risk_level = CASE WHEN scores.score >= p.auto_block_threshold THEN 'high'
          WHEN scores.score >= p.review_threshold THEN 'medium' ELSE 'low' END
        FROM (SELECT m.cluster_id, max(nf.max_risk_score) score FROM graph_cluster_member m
              JOIN number_feature nf ON nf.phone_number_id=m.phone_number_id GROUP BY m.cluster_id) scores,
             blocking_policy p
        WHERE scores.cluster_id=g.id AND p.is_active
    """))
    return {"fan_candidates": len(sources), "clusters": saved}


def main():
    db = SessionLocal()
    try:
        print(refresh_graph(db))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
