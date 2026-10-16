import unittest
from types import SimpleNamespace

from tests import _env  # noqa: F401
from core import telecom
from core.utils.pagination import decode_cursor, digits_only, encode_cursor, page, resolve_offset
from etl.refresh_graph import find_fans
from services.number_service import mask_imsi
from services.scoring_service import decide


class PaginationTest(unittest.TestCase):
    def test_cursor_offset(self):
        rows, cursor, more = page(list(range(11)), 10, 20)
        self.assertEqual(len(rows), 10)
        self.assertTrue(more)
        self.assertEqual(resolve_offset(cursor, None), 30)
        self.assertEqual(page(list(range(5)), 10, 0)[1:], (None, False))

    def test_bad_cursor(self):
        self.assertEqual(decode_cursor("!!!"), {})
        self.assertEqual(resolve_offset(encode_cursor({"offset": "x"}), None), 0)
        self.assertEqual(resolve_offset(encode_cursor({"offset": -5}), None), 0)

    def test_digits_only(self):
        self.assertEqual(digits_only("+7 (842) 12-34"), "78421234")
        self.assertEqual(digits_only("%' OR 1=1 --"), "11")
        self.assertEqual(digits_only(None), "")


class ScoringTest(unittest.TestCase):
    def test_decision(self):
        pol = SimpleNamespace(auto_block_enabled=True, auto_block_threshold=70, review_threshold=40)
        self.assertEqual(decide(70, pol), "auto_blocked")
        self.assertEqual(decide(40, pol), "review")
        self.assertEqual(decide(39, pol), "allow")
        pol.auto_block_enabled = False
        self.assertEqual(decide(95, pol), "review")


class GraphTest(unittest.TestCase):
    def test_fans_grouped(self):
        shared = {f"02500000{i:02d}" for i in range(30)}
        sources = [(f"77700000{i:02d}", shared | {f"0260000{i:03d}"}, 0.9) for i in range(4)]
        sources.append(("8421111111", {f"89900000{i:02d}" for i in range(25)}, 0.7))
        fans = find_fans(sources)
        self.assertEqual(len(fans), 1)
        self.assertEqual(len(fans[0]["members"]), 4)
        self.assertGreater(fans[0]["overlap_share"], 0.5)
        self.assertEqual(fans[0]["regions"], ["025", "026"])

    def test_small_groups_ignored(self):
        self.assertEqual(find_fans([("1", {"a"}, 1.0), ("2", {"b"}, 1.0)]), [])


class MiscTest(unittest.TestCase):
    def test_telecom(self):
        self.assertTrue(telecom.is_home_number("8421234567"))
        self.assertFalse(telecom.is_home_number("7771234567"))
        self.assertEqual(telecom.operator_group("0261234567"), "alpha")
        self.assertEqual(telecom.region_name("499"), "Москва 499")

    def test_mask_imsi(self):
        self.assertEqual(mask_imsi("250011234567890"), "IMSI •••7890")
        self.assertIsNone(mask_imsi(None))


if __name__ == "__main__":
    unittest.main()
