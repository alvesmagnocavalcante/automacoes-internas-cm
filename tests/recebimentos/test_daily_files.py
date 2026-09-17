from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from automations.recebimentos.daily_files import (
    daily_directory,
    find_downloaded_report,
    find_rede_report,
    find_rede_reports,
    identify_rede_company,
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

    def test_identifies_each_company_and_ignores_central_services(self):
        examples = {
            "Rede Carmel Charme Hospedagem 14.09.xlsx": "CHARME",
            "Rede Carmel Cumbuco 14.09.xlsx": "CUMBUCO",
            "Rede Carmel Icaraizinho 14.09.xlsx": "ICARAIZINHO",
            "Rede Carmel Taíba 14.09.xlsx": "TAIBA",
            "Rede Magna Praia 14.09.xlsx": "MAGNA",
        }
        for filename, company in examples.items():
            with self.subTest(filename=filename):
                self.assertEqual(identify_rede_company(Path(filename)).code, company)
        self.assertIsNone(
            identify_rede_company(Path("Rede CM Central de Serviços 14.09.xlsx"))
        )

    def test_rejects_ambiguous_or_unidentified_rede_file(self):
        for filename in ("Rede 14.09.xlsx", "Rede Magna Charme 14.09.xlsx"):
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ValueError, "ausente ou ambígua"):
                    identify_rede_company(Path(filename))

    def test_preflights_all_rede_reports_and_detects_duplicates(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "Rede Charme 14.09.xlsx",
                "Rede Cumbuco 14.09.xlsx",
                "Rede Icaraizinho 14.09.xlsx",
                "Rede Taíba 14.09.xlsx",
                "Rede Magna 14.09.xlsx",
                "Rede CM Central Serviços 14.09.xlsx",
            ):
                (root / name).touch()
            reports = find_rede_reports(root, date(2026, 9, 14))
            self.assertEqual(set(reports), {"CHARME", "CUMBUCO", "ICARAIZINHO", "TAIBA", "MAGNA"})
            (root / "Rede Magna Praia 14.09.xlsx").touch()
            with self.assertRaisesRegex(RuntimeError, "Mais de um relatório Rede de MAGNA"):
                find_rede_reports(root, date(2026, 9, 14))

    def test_preflight_requires_every_company_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Rede Magna 14.09.xlsx").touch()
            with self.assertRaisesRegex(FileNotFoundError, "CHARME, CUMBUCO, ICARAIZINHO, TAIBA"):
                find_rede_reports(root, date(2026, 9, 14))

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
