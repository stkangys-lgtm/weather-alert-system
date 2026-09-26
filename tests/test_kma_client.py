import unittest
from datetime import datetime
from unittest import mock

from src import kma_client


class ForecastCodeTests(unittest.TestCase):
    def test_shower_code_is_named(self):
        items = [{"fcstDate": "20260926", "fcstTime": "1500", "category": "PTY", "fcstValue": "4"},
                 {"fcstDate": "20260926", "fcstTime": "1500", "category": "SKY", "fcstValue": "3"}]
        with mock.patch.object(kma_client, "_request", return_value=items):
            rows = kma_client.get_forecast("key", 60, 127, now=datetime(2026, 9, 26, 14, 20))
        self.assertEqual(("소나기", "구름많음"), (rows[0]["PTY"], rows[0]["SKY"]))


if __name__ == "__main__":
    unittest.main()
