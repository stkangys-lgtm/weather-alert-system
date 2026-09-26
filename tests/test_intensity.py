import unittest

from src.intensity import fmt_number, rain_term, wind_term


class IntensityTests(unittest.TestCase):
    def test_rain_terms_follow_kma_boundaries(self):
        cases = [(None, None), (0.05, None), (0.1, "약한 비"), (2.9, "약한 비"), (3, "비"), (14.9, "비"),
                 (15, "강한 비"), (29.9, "강한 비"), (30, "매우 강한 비"), (31, "매우 강한 비")]
        for mm, expected in cases:
            with self.subTest(mm=mm):
                self.assertEqual(expected, rain_term(mm))

    def test_wind_terms_only_from_four_meters(self):
        cases = [(None, None), (3.9, None), (4, "약간 강한 바람"), (8.9, "약간 강한 바람"), (9, "강한 바람"),
                 (13.9, "강한 바람"), (14, "매우 강한 바람")]
        for ms, expected in cases:
            with self.subTest(ms=ms):
                self.assertEqual(expected, wind_term(ms))

    def test_fmt_number(self):
        self.assertEqual("31", fmt_number(31.0))
        self.assertEqual("2.5", fmt_number(2.5))
        self.assertEqual("0.5", fmt_number(0.46))
        self.assertEqual("-", fmt_number(None))


if __name__ == "__main__":
    unittest.main()
