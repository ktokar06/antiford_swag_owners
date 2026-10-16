"""HTTP-уровень без БД: авторизация и валидация. Нужен httpx."""
import unittest

from tests import _env  # noqa: F401

try:
    from fastapi.testclient import TestClient
except Exception:  # httpx не установлен
    TestClient = None


@unittest.skipIf(TestClient is None, "httpx не установлен (pip install httpx)")
class ApiAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.deps import get_db_dep
        from core.main import app

        class FakeDB:
            def get(self, model, pk):
                return None

        app.dependency_overrides[get_db_dep] = lambda: FakeDB()
        cls.app = app
        cls.client = TestClient(app)  # без контекстного менеджера: lifespan (БД) не запускается

    @classmethod
    def tearDownClass(cls):
        cls.app.dependency_overrides.clear()

    def test_health(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")

    def test_protected_without_token(self):
        for path in ("/api/calls", "/api/stats/summary", "/api/cdr/invalid", "/api/blocks/numbers"):
            self.assertEqual(self.client.get(path).status_code, 401, path)

    def test_garbage_token(self):
        r = self.client.get("/api/calls", headers={"Authorization": "Bearer abc.def.ghi"})
        self.assertEqual(r.status_code, 401)

    def test_valid_token_unknown_user(self):
        from core.utils.security import create_access_token
        r = self.client.get("/api/calls", headers={"Authorization": f"Bearer {create_access_token('1')}"})
        self.assertEqual(r.status_code, 401)

    def test_mutations_still_require_login(self):
        for path, body in (("/api/rescore", None), ("/api/cdr/import", None),
                           ("/api/ml/score", {"cdr_line": "bad"})):
            self.assertEqual(self.client.post(path, json=body).status_code, 401, path)

    def test_operator_can_run_former_privileged_actions(self):
        from unittest.mock import patch
        from core.deps import get_current_user
        from core.models.user import AppUser
        self.app.dependency_overrides[get_current_user] = lambda: AppUser(
            id=1, email="operator@example.com", role="operator", is_active=True)
        try:
            with patch("core.routers.rules.pipeline.start_background", return_value=True):
                self.assertEqual(self.client.post("/api/rescore").status_code, 202)
            with patch("core.routers.cdr.pipeline.start_background", return_value=True):
                self.assertEqual(self.client.post("/api/cdr/import").status_code, 202)
            self.assertEqual(self.client.post("/api/ml/score", json={"cdr_line": "bad"}).status_code, 422)
        finally:
            self.app.dependency_overrides.pop(get_current_user)


if __name__ == "__main__":
    unittest.main()
