from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from openpyxl import Workbook

from automations.recebimentos.daily_files import (
    daily_directory,
    find_downloaded_report,
    find_rede_report,
    find_rede_reports,
    identify_rede_company,
    previous_report_date,
)


class DailyFilesTests(TestCase):
    @staticmethod
    def _write_rede(path: Path, *establishments: str) -> None:
        book = Workbook()
        sheet = book.active
        sheet.append(["nome do estabelecimento"])
        for establishment in establishments:
            sheet.append([establishment])
        book.save(path)
        book.close()

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
            "CARMEL CHARME": "CHARME",
            "CARMEL CUMBUCO": "CUMBUCO",
            "CARMEL WIND": "CUMBUCO",
            "CARMEL ICARAIZINHO": "ICARAIZINHO",
            "CARMEL TAÍBA": "TAIBA",
            "MAGNA PRAIA": "MAGNA",
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (establishment, company) in enumerate(examples.items()):
                with self.subTest(establishment=establishment):
                    path = root / f"Rede_Rel_Vendas_14_09_2026-{index}.xlsx"
                    self._write_rede(path, establishment)
                    self.assertEqual(identify_rede_company(path).code, company)
            central = root / "Rede_Rel_Vendas_14_09_2026-CENTRAL.xlsx"
            self._write_rede(central, "CM CENTRAL SERVIÇOS")
            self.assertIsNone(identify_rede_company(central))

    def test_rejects_ambiguous_or_unidentified_rede_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            mixed = root / "Rede_14_09_2026.xlsx"
            self._write_rede(mixed, "CARMEL CHARME", "MAGNA PRAIA")
            with self.assertRaisesRegex(ValueError, "empresas diferentes"):
                identify_rede_company(mixed)
            mismatched = root / "Rede Magna 14.09.xlsx"
            self._write_rede(mismatched, "CARMEL CHARME")
            with self.assertRaisesRegex(ValueError, "divergem"):
                identify_rede_company(mismatched)
            unknown = root / "Rede_14_09_2026-uuid.xlsx"
            self._write_rede(unknown, "HOTEL DESCONHECIDO")
            with self.assertRaisesRegex(ValueError, "desconhecido"):
                identify_rede_company(unknown)

    def test_preflights_all_rede_reports_and_detects_duplicates(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, company in enumerate(
                ("CHARME", "CUMBUCO", "ICARAIZINHO", "TAIBA", "MAGNA")
            ):
                self._write_rede(
                    root / f"Rede_Rel_Vendas_14_09_2026-{index}.xlsx", company
                )
            self._write_rede(
                root / "Rede_Rel_Vendas_14_09_2026-5.xlsx",
                "CM CENTRAL SERVIÇOS",
            )
            reports = find_rede_reports(root, date(2026, 9, 14))
            self.assertEqual(set(reports), {"CHARME", "CUMBUCO", "TAIBA", "MAGNA"})
            self._write_rede(root / "Rede Magna Praia 14.09.xlsx", "MAGNA PRAIA")
            with self.assertRaisesRegex(RuntimeError, "Mais de um relatório Rede de MAGNA"):
                find_rede_reports(root, date(2026, 9, 14))

    def test_wind_and_cumbuco_reports_for_same_day_are_duplicates(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_rede(root / "Rede_14_09_2026-1.xlsx", "CARMEL WIND")
            self._write_rede(root / "Rede_14_09_2026-2.xlsx", "CARMEL CUMBUCO")
            with self.assertRaisesRegex(RuntimeError, "Mais de um relatório Rede de CUMBUCO"):
                find_rede_reports(root, date(2026, 9, 14), require_all=False)

    def test_preflight_requires_every_company_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_rede(root / "Rede Magna 14.09.xlsx", "MAGNA PRAIA")
            with self.assertRaisesRegex(FileNotFoundError, "CHARME, CUMBUCO, TAIBA"):
                find_rede_reports(root, date(2026, 9, 14))
            reports = find_rede_reports(root, date(2026, 9, 14), require_all=False)
            self.assertEqual(set(reports), {"MAGNA"})

    def test_partial_preflight_does_not_accept_only_inactive_companies(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_rede(
                root / "Rede_14_09_2026-central.xlsx", "CM CENTRAL SERVIÇOS"
            )
            self._write_rede(
                root / "Rede_14_09_2026-icaraizinho.xlsx", "CARMEL ICARAIZINHO"
            )
            with self.assertRaisesRegex(FileNotFoundError, "Nenhum relatório Rede de hotel"):
                find_rede_reports(root, date(2026, 9, 14), require_all=False)

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
