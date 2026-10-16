import unittest
from datetime import datetime

from tests import _env  # noqa: F401
from etl import cdr_parser as p

VALID_01 = "01;;8421234567;0251234567;20241014114200;6;"
VALID_02 = "02;250011234567890;0261234567;8991234567;20241014020000;0;"
VALID_03 = "03;;2101234567;4991234567;20241014180000;45;0251112233"


class ParseLineTest(unittest.TestCase):
    def test_valid_records(self):
        for line in (VALID_01, VALID_02, VALID_03):
            self.assertIsInstance(p.parse_line(line), p.CdrRecord, line)

    def test_blank_line_skipped(self):
        self.assertIsNone(p.parse_line("   \n"))

    def test_enrichment(self):
        r = p.parse_line(VALID_02)
        self.assertEqual(r.direction, "incoming")
        self.assertEqual(r.time_bucket, "night")
        self.assertTrue(r.hung_up_first_second)
        self.assertEqual(r.connection_type, "mobile")
        self.assertFalse(r.foreign_origin)
        self.assertEqual(r.started_at, datetime(2024, 10, 14, 2, 0, 0))

    def test_foreign_origin(self):
        r = p.parse_line("01;;7771234567;0251234567;20241014114200;6;")
        self.assertTrue(r.foreign_origin)
        self.assertEqual(r.source_country, "ZZ")
        self.assertEqual(r.connection_type, "sip_gateway")

    def test_city_is_pstn(self):
        self.assertEqual(p.parse_line(VALID_01).connection_type, "pstn")

    def assertError(self, line, code):
        res = p.parse_line(line)
        self.assertIsInstance(res, p.CdrError, line)
        self.assertEqual(res.code, code, line)
        self.assertTrue(res.reason)
        self.assertLessEqual(len(res.reason), 200)

    def test_errors(self):
        self.assertError("01;;8421234567;0251234567;20241014114200;6", p.E_FIELD_COUNT)
        self.assertError("09;;8421234567;0251234567;20241014114200;6;", p.E_TYPE)
        self.assertError("01;;8421234567;0251234567;20241399114200;6;", p.E_DATE)
        self.assertError("01;;8421234567;0251234567;2024101411420;6;", p.E_DATE)
        self.assertError("01;;8421234567;0251234567;20241014114200;-1;", p.E_DURATION)
        self.assertError("01;;8421234567;0251234567;20241014114200;86401;", p.E_DURATION)
        self.assertError("01;;842123456;0251234567;20241014114200;6;", p.E_NUM_A)
        self.assertError("01;;8421234567;02512345AB;20241014114200;6;", p.E_NUM_B)
        self.assertError("03;;8421234567;0251234567;20241014114200;6;123", p.E_NUM_C)
        self.assertError("01;;8421234567;8421234567;20241014114200;6;", p.E_SAME_NUMBER)
        self.assertError("01;250011234567890;8421234567;0251234567;20241014114200;6;", p.E_IMSI_FORBIDDEN)
        self.assertError("02;;8421234567;0251234567;20241014114200;6;", p.E_IMSI_MISSING)
        self.assertError("02;2500112345;8421234567;0251234567;20241014114200;6;", p.E_IMSI)
        self.assertError("01;;8421234567;０２５1234567;20241014114200;6;", p.E_NUM_B)
        self.assertError("01;;84212�4567;0251234567;20241014114200;6;", p.E_ENCODING)

    def test_row_hash_stable_and_distinct(self):
        a, b = p.parse_line(VALID_01), p.parse_line(VALID_01 + "\r\n")
        self.assertEqual(a.row_hash(), b.row_hash())
        self.assertEqual(len(a.row_hash()), 64)
        self.assertNotEqual(a.row_hash(), p.parse_line(VALID_01.replace(";6;", ";7;")).row_hash())

    def test_row_hash_canonical_format(self):
        import hashlib
        r = p.parse_line(VALID_01)
        expected = hashlib.sha256(b"01||8421234567|0251234567|20241014114200|6|").hexdigest()
        self.assertEqual(r.row_hash(), expected)


if __name__ == "__main__":
    unittest.main()
