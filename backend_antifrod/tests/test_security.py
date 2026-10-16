import time
import unittest

from tests import _env  # noqa: F401
from jose import jwt
from pydantic import ValidationError

from core.config import Settings, settings
from core.utils import security


class SecurityTest(unittest.TestCase):
    def test_token_roundtrip(self):
        token = security.create_access_token("42", {"role": "operator"})
        payload = security.decode_token(token)
        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["type"], "access")
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)

    def test_extra_cannot_override_claims(self):
        token = security.create_access_token("1", {"sub": "999", "exp": 1})
        self.assertEqual(security.decode_token(token)["sub"], "1")

    def test_wrong_secret_rejected(self):
        token = jwt.encode({"sub": "1", "exp": int(time.time()) + 60, "iat": int(time.time()), "type": "access"},
                           "another-secret-" + "y" * 40, algorithm="HS256")
        with self.assertRaises(security.JWTError):
            security.decode_token(token)

    def test_expired_rejected(self):
        now = int(time.time())
        token = jwt.encode({"sub": "1", "exp": now - 10, "iat": now - 100, "type": "access"},
                           settings.jwt_secret, algorithm="HS256")
        with self.assertRaises(security.JWTError):
            security.decode_token(token)

    def test_missing_exp_and_wrong_type_rejected(self):
        no_exp = jwt.encode({"sub": "1", "iat": int(time.time()), "type": "access"},
                            settings.jwt_secret, algorithm="HS256")
        with self.assertRaises(security.JWTError):
            security.decode_token(no_exp)
        refresh = jwt.encode({"sub": "1", "exp": int(time.time()) + 60, "iat": int(time.time()), "type": "refresh"},
                             settings.jwt_secret, algorithm="HS256")
        with self.assertRaises(security.JWTError):
            security.decode_token(refresh)

    def test_alg_none_rejected(self):
        token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIn0."
        with self.assertRaises(security.JWTError):
            security.decode_token(token)

    def test_password_hash(self):
        h = security.hash_password("correct horse")
        self.assertTrue(security.verify_password("correct horse", h))
        self.assertFalse(security.verify_password("wrong", h))
        self.assertFalse(security.verify_password("x", "not-a-hash"))
        with self.assertRaises(ValueError):
            security.hash_password("я" * 40)

    def test_reset_token_hash(self):
        self.assertEqual(len(security.hash_token("abc")), 64)
        self.assertNotEqual(security.hash_token("abc"), "abc")

    def test_weak_jwt_secret_rejected(self):
        for bad in ("change-me-please-use-a-long-random-string", "short"):
            with self.assertRaises(ValidationError):
                Settings(DATABASE_URL="postgresql://x", JWT_SECRET=bad, _env_file=None)
        with self.assertRaises(ValidationError):
            Settings(DATABASE_URL="postgresql://x", JWT_SECRET="z" * 40, JWT_ALGORITHM="none", _env_file=None)


if __name__ == "__main__":
    unittest.main()
