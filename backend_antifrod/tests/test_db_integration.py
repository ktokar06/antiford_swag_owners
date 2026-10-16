"""
Сквозной тест CDR_OUT → БД → API-сервисы на реальном PostgreSQL.
Запускается, только если задан TEST_DATABASE_URL (отдельная, ОЧИЩАЕМАЯ база!):
    TEST_DATABASE_URL=postgresql+psycopg://antifraud:...@localhost:5432/antifraud_test python -m unittest
"""
import os
import unittest

TEST_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_URL:
    os.environ["DATABASE_URL"] = TEST_URL
from tests import _env

def _lines():
    out = []
    for s in range(4):
        for t in range(25):
            out.append(f"01;;77700000{s:02d};02500000{t:02d};2024101402{t:02d}00;1;")
    out.append("02;250011234567890;0261234567;8991234567;20241014120000;120;")
    out.append("02;250011234567890;0261234567;8991234567;20241014120000;120;")
    out += ["bad;line", "01;;8421234567;0251234567;20241399114200;6;", "02;;8421234567;0251234567;20241014114200;6;"]
    return out


@unittest.skipUnless(TEST_URL, "TEST_DATABASE_URL не задан")
class PipelineIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        from sqlalchemy import text
        from core.database import engine
        with engine.begin() as c:
            c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
            root = Path(__file__).resolve().parents[1] / "db"
            for name in ("001_schema.sql", "002_reference.sql"):
                c.exec_driver_sql((root / name).read_text())

    def test_full_flow(self):
        from core.database import SessionLocal
        from etl import load_cdr
        from etl.load_features import compute_number_features
        from etl.refresh_graph import refresh_graph
        from services import blocks_service, call_service, cdr_service, scoring_service, stats_api_service, stats_service

        data = ("\n".join(_lines()) + "\n").encode()
        with SessionLocal() as db:
            res = load_cdr.load_bytes(db, "CDR_test.cdr", data)
            db.commit()
            self.assertEqual((res.rows_valid, res.rows_duplicate, res.rows_invalid), (101, 1, 3))
            again = load_cdr.load_bytes(db, "CDR_test_copy.cdr", data)
            self.assertEqual(again.status, load_cdr.STATUS_SKIPPED)
            other = load_cdr.load_bytes(db, "CDR_test2.cdr", (_lines()[0] + "\n").encode())
            db.commit()
            self.assertEqual((other.rows_valid, other.rows_duplicate), (0, 1))  # дубликат между файлами

            compute_number_features(db); db.commit()
            scoring_service.score_calls(db); db.commit()
            graph = refresh_graph(db); db.commit()
            self.assertEqual(graph["clusters"], 1)
            stats_service.refresh_all(db); db.commit()

            summary = stats_api_service.summary(db)
            self.assertEqual(summary["calls_total"], 101)
            self.assertEqual(summary["rows_invalid"], 3)
            self.assertEqual(summary["calls_unscored"], 0)

            calls = call_service.list_calls(db, {"sort": "-risk_score", "limit": 10})
            self.assertTrue(calls.has_more)
            self.assertGreaterEqual(calls.items[0].risk_score, calls.items[-1].risk_score)
            self.assertIsNotNone(calls.items[0].probability)
            self.assertTrue(calls.items[0].model_version)
            detail = call_service.get_call(db, calls.items[0].id)
            self.assertEqual(len(detail.explanation["factors"]), 44)
            import math
            explanation = detail.explanation
            log_odds = explanation["base_log_odds"] + sum(f["contribution"] for f in explanation["factors"])
            self.assertAlmostEqual(1 / (1 + math.exp(-log_odds)), detail.probability, places=8)
            self.assertEqual(detail.risk_score, round(100 * detail.probability))
            from services.ml_service import score_envelope
            from sqlalchemy import text
            latest = db.execute(text("SELECT id FROM call_record WHERE caller_number='7770000000' ORDER BY started_at DESC LIMIT 1")).scalar_one()
            online = score_envelope(db, _lines()[24], True)
            saved = call_service.get_call(db, latest)
            self.assertAlmostEqual(online["probability"], saved.probability, places=8)
            nxt = call_service.list_calls(db, {"sort": "-risk_score", "limit": 10, "cursor": calls.next_cursor})
            self.assertFalse({c.id for c in calls.items} & {c.id for c in nxt.items})

            invalid = cdr_service.list_invalid(db, {"limit": 50})
            self.assertEqual(invalid["total"], 3)
            self.assertTrue(all(i["reason"] and i["error_code"] for i in invalid["items"]))
            blocked = blocks_service.blocked_numbers(db, {"limit": 50})
            self.assertGreaterEqual(blocked.total, 0)

    def test_model_failure_preserves_previous_decisions(self):
        from unittest.mock import patch
        from sqlalchemy import text
        from core.database import SessionLocal
        from services.scoring_service import score_calls
        with SessionLocal() as db:
            before = db.execute(text("SELECT call_id, risk_score FROM call_decision ORDER BY call_id")).all()
            with patch("services.scoring_service.get_predictor", side_effect=ValueError("bad model")):
                with self.assertRaises(ValueError):
                    score_calls(db)
            db.rollback()
            after = db.execute(text("SELECT call_id, risk_score FROM call_decision ORDER BY call_id")).all()
            self.assertEqual(before, after)

    def test_csv_labels_are_not_predictions(self):
        from core.database import SessionLocal
        from etl.load_cdr import load_bytes
        from sqlalchemy import text
        data = ("type;imsi;phone_a;phone_b;time;duration;phone_c;is_fraud\n"
                "2;250020582732825.0;8109392353;2001413931;2026-10-01 00:00:00;3;;1\n").encode()
        with SessionLocal() as db:
            result = load_bytes(db, "labeled.csv", data)
            self.assertEqual(result.rows_valid, 1)
            cid = db.scalar(text("SELECT id FROM call_record WHERE cdr_file_id=:id"), {"id":result.file_id})
            self.assertIsNone(db.scalar(text("SELECT risk_score FROM call_decision WHERE call_id=:id"), {"id":cid}))
            db.rollback()

    def test_scenario_reference_matches_organizers(self):
        from sqlalchemy import select
        from core.database import SessionLocal
        from core.models.labeling import FraudScenario, FalsePositiveLabel
        from etl.load_labels import ensure_reference
        with SessionLocal() as db:
            ensure_reference(db)
            db.commit()
            names = {r.code: r.name for r in db.execute(select(FraudScenario)).scalars()}
            legitimate = {r.code: r.name for r in db.execute(select(FalsePositiveLabel)).scalars()}
            self.assertEqual(names["S2"], "Массовый обзвон (робот)")
            self.assertEqual(names["S7"], "Вишинг со спуфингом")
            self.assertEqual(legitimate["D4"], "Горячая линия")
            self.assertEqual(len(legitimate), 5)

    def test_schema_defaults_to_operator_and_rejects_other_roles(self):
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        from core.database import engine

        with engine.begin() as connection:
            user_id = connection.execute(text("""
                INSERT INTO app_user(email, password_hash, full_name)
                VALUES ('schema@example.com', 'unchanged-hash', 'Existing User') RETURNING id
            """)).scalar_one()
            row = connection.execute(text("SELECT role, password_hash, full_name FROM app_user WHERE id=:id"),
                                     {"id": user_id}).one()
            self.assertEqual(tuple(row), ("operator", "unchanged-hash", "Existing User"))
        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text("UPDATE app_user SET role='other' WHERE id=:id"), {"id": user_id})


if __name__ == "__main__":
    unittest.main()
