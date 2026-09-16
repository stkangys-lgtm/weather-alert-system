import os
import tempfile
import unittest

from openpyxl import Workbook

from src.weekly_work_importer import parse_weekly_work


class WeeklyWorkImporterTests(unittest.TestCase):
    def _workbook(self):
        book = Workbook()
        sheet = book.active
        sheet.title = "(건축)주요현장"
        sheet["A3"], sheet["B3"] = "순번", "현장명"
        sheet["J3"] = "주요공정 - 금주\n(26.09.07. ~ 26.09.13.)"
        sheet["K3"] = "주요공정 - 금주\n(26.09.14. ~ 26.09.20.)"
        sheet["A4"], sheet["B4"] = 1, "양산\n부산대병원"
        sheet["J4"], sheet["K4"] = "지난 공정", "- 토공 및 가시설 공사"
        sheet["A7"], sheet["B7"] = 2, "시흥거모\nLH 아파트"
        sheet["K7"] = "- 가설사무실 공사"
        return book

    def test_extracts_latest_week_and_only_active_aliases(self):
        book = self._workbook()
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        try:
            book.save(path)
            sites = [{"site_name": "양산 부산대병원"}, {"site_name": "산솔면 하수처리장"}]
            result = parse_weekly_work(path, sites)
        finally:
            os.unlink(path)

        self.assertEqual([["양산 부산대병원", "- 토공 및 가시설 공사"]], result["rows"])
        self.assertEqual("2026-09-14", str(result["period"][0]))
        self.assertEqual(["산솔면 하수처리장"], result["missing_active_sites"])
        self.assertEqual(["시흥거모\nLH 아파트"], result["unmatched_source_sites"])


if __name__ == "__main__":
    unittest.main()
