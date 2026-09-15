from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from automations.recebimentos.daily_files import (
    daily_directory,
    find_downloaded_report,
    find_rede_report,
    previous_report_date,
)


class DailyFilesTests(TestCase):
    def test_uses_previous_day_across_month_boundary(self):
        self.assertEqual(previous_report_date(date(2026, 9, 1)), date(2026, 8, 31))

    def test_builds_portuguese_month_and_day_structure(self):
        self.assertEqual(
            daily_directory(Path("arquivo"), date(2026, 8, 1)),
            Path("arquivo/08 - AGOSTO/01"),
        )

    def test_finds_rede_by_report_date(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "rede magna 14.09.xlsx"
            expected.touch()
            (root / "rede magna 13.09.xlsx").touch()

            result = find_rede_report(root, date(2026, 9, 14))

        self.assertEqual(result, expected)

    def test_finds_rede_inside_month_and_day_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            daily = root / "09 - SETEMBRO/14"
            daily.mkdir(parents=True)
            expected = daily / "Rede Magna 14.09.xlsx"
            expected.touch()

            result = find_rede_report(root, date(2026, 9, 14))

        self.assertEqual(result, expected)

    def test_prefers_root_input_over_generated_daily_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "rede magna 14.09.xlsx"
            source.touch()
            daily = root / "09 - SETEMBRO/14"
            daily.mkdir(parents=True)
            (daily / "Rede Magna 14.09.xlsx").touch()

            result = find_rede_report(root, date(2026, 9, 14))

        self.assertEqual(result, source)

    def test_finds_downloaded_reports(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / "downloads"
            downloads.mkdir()
            opera = downloads / "opera_recebimentos_2026-09-14.xml"
            cmflex = downloads / "cmflex_recebimentos_2026-09-14.xlsx"
            rede = downloads / "rede magna 14.09.xlsx"
            for path in (opera, cmflex, rede):
                path.write_text(path.name, encoding="utf-8")
            opera.write_text(
                "<FINPAYMENTS><G_TRANSACTION /></FINPAYMENTS>", encoding="utf-8"
            )

            self.assertEqual(
                find_downloaded_report(downloads, "opera", date(2026, 9, 14)),
                opera,
            )

    def test_prefers_latest_repeated_browser_download(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "opera_recebimentos_2026-09-14.XML"
            latest = root / "opera_recebimentos_2026-09-14_1.XML"
            old.write_text("<FINPAYMENTS />", encoding="utf-8")
            latest.write_text(
                "<FINPAYMENTS><G_TRANSACTION /></FINPAYMENTS>", encoding="utf-8"
            )

            result = find_downloaded_report(root, "opera", date(2026, 9, 14))

        self.assertEqual(result, latest)
