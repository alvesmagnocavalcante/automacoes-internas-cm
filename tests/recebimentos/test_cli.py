from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from automations.recebimentos import cli


class RecebimentosCliTests(TestCase):
    def test_monday_processes_each_date_before_advancing(self):
        report_dates = (
            cli.date(2026, 9, 18),
            cli.date(2026, 9, 19),
            cli.date(2026, 9, 20),
        )
        reports = [
            {"CHARME": Path(f"entrada/rede-charme-{report_date:%d-%m}.xlsx")}
            for report_date in report_dates
        ]
        config = SimpleNamespace(validate=lambda: None)
        result = SimpleNamespace(matched_count=1, divergent_count=0)

        with (
            patch.object(cli, "load_environment"),
            patch.dict(
                "os.environ",
                {"RECEBIMENTOS_OPERA_HOTEL_CHARME": "CHARME"},
                clear=True,
            ),
            patch.object(
                cli, "report_dates_for_execution", return_value=report_dates
            ),
            patch.object(
                cli, "find_rede_reports", side_effect=reports
            ) as find_rede,
            patch.object(cli, "config_from_env", return_value=config),
            patch.object(cli, "cmflex_config_from_env", return_value=config),
            patch.object(
                cli,
                "find_downloaded_report",
                side_effect=lambda directory, system, report_date: directory
                / f"{system}_{report_date:%Y-%m-%d}.xlsx",
            ),
            patch.object(cli, "run", return_value=result),
            patch.object(
                cli,
                "save_conference_workbooks",
                return_value=(Path("arquivo"), {}),
            ) as archive,
        ):
            code = cli.main(
                ["--all-companies", "--allow-partial", "--rede-dir", "entrada"]
            )

        self.assertEqual(code, 0)
        self.assertEqual(
            [item.args[1] for item in find_rede.call_args_list],
            list(report_dates),
        )
        self.assertEqual(
            [item.args[5] for item in archive.call_args_list],
            list(report_dates),
        )

    def test_partial_mode_runs_only_companies_with_rede_files(self):
        reports = {
            "CHARME": Path("entrada/rede-charme.xlsx"),
            "MAGNA": Path("entrada/rede-magna.xlsx"),
        }
        config = SimpleNamespace(validate=lambda: None)
        result = SimpleNamespace(matched_count=1, divergent_count=0)
        with (
            patch.object(cli, "load_environment"),
            patch.dict(
                "os.environ",
                {
                    "RECEBIMENTOS_OPERA_HOTEL_CHARME": "CHARME",
                    "RECEBIMENTOS_OPERA_HOTEL_MAGNA": "MAGNA",
                },
                clear=True,
            ),
            patch.object(cli, "find_rede_reports", return_value=reports) as find_rede,
            patch.object(cli, "config_from_env", return_value=config),
            patch.object(
                cli,
                "cmflex_config_from_env",
                side_effect=lambda company: SimpleNamespace(
                    company=company, validate=lambda: None
                ),
            ),
            patch.object(cli, "find_downloaded_report", side_effect=FileNotFoundError),
            patch.object(
                cli,
                "run_opera_download",
                side_effect=lambda _, hotel, directory, **_kwargs: directory
                / "opera.xml",
            ) as opera_download,
            patch.object(
                cli,
                "run_cmflex_download",
                side_effect=lambda _, directory, **_kwargs: directory / "cmflex.xlsx",
            ) as cmflex_download,
            patch.object(cli, "run", return_value=result),
            patch.object(
                cli, "save_conference_workbooks", return_value=(Path("arquivo"), {})
            ) as archive,
        ):
            code = cli.main(
                [
                    "--all-companies",
                    "--allow-partial",
                    "--rede-dir",
                    "entrada",
                    "--data",
                    "14/09/2026",
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(find_rede.call_args.kwargs, {"require_all": False})
        self.assertEqual(opera_download.call_count, 2)
        self.assertEqual(cmflex_download.call_count, 2)
        self.assertEqual(archive.call_count, 2)

    def test_all_companies_runs_sequentially_with_isolated_files(self):
        from automations.recebimentos.companies import ACTIVE_COMPANIES

        self.assertEqual(
            tuple(company.code for company in ACTIVE_COMPANIES),
            ("TAIBA", "CHARME", "CUMBUCO", "MAGNA"),
        )
        reports = {
            company.code: Path(f"entrada/rede {company.code}.xlsx")
            for company in ACTIVE_COMPANIES
        }
        env = {
            f"RECEBIMENTOS_OPERA_HOTEL_{company.code}": company.code
            for company in ACTIVE_COMPANIES
        }
        config = SimpleNamespace(validate=lambda: None)
        result = SimpleNamespace(matched_count=1, divergent_count=0)
        events = []

        def download_opera(_config, hotel, directory, *, report_date):
            self.assertEqual(report_date, cli.date(2026, 9, 14))
            events.append(("opera", hotel))
            return directory / "opera.xml"

        def download_cmflex(company_config, directory, *, report_date):
            self.assertEqual(report_date, cli.date(2026, 9, 14))
            events.append(("cmflex", company_config.company))
            return directory / "cmflex.xlsx"

        def reconcile(opera, cmflex, rede, output):
            events.append(("reconcile", rede.name))
            self.assertEqual(opera.parent, cmflex.parent)
            self.assertIsNone(output)
            return result

        with (
            patch.object(cli, "load_environment"),
            patch.dict("os.environ", env, clear=True),
            patch.object(cli, "find_rede_reports", return_value=reports),
            patch.object(cli, "config_from_env", return_value=config),
            patch.object(cli, "cmflex_config_from_env", side_effect=lambda company: SimpleNamespace(company=company, validate=lambda: None)),
            patch.object(cli, "find_downloaded_report", side_effect=FileNotFoundError),
            patch.object(cli, "run_opera_download", side_effect=download_opera),
            patch.object(cli, "run_cmflex_download", side_effect=download_cmflex),
            patch.object(cli, "run", side_effect=reconcile),
            patch.object(cli, "save_conference_workbooks", side_effect=lambda *args: (Path("arquivo") / args[-1], {})) as archive,
        ):
            code = cli.main(
                [
                    "--all-companies",
                    "--rede-dir",
                    "entrada",
                    "--data",
                    "14/09/2026",
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(archive.call_count, 4)
        for index, company in enumerate(ACTIVE_COMPANIES):
            self.assertEqual(
                events[index * 3:index * 3 + 3],
                [("opera", company.code), ("cmflex", company.cmflex_name),
                 ("reconcile", reports[company.code].name)],
            )

    def test_uses_existing_opera_hotel_from_environment(self):
        with (
            patch.object(cli, "load_environment"),
            patch.dict("os.environ", {"OPERA_HOTEL": "MAGNA"}, clear=True),
        ):
            args = cli.parse_args(["--baixar-opera"])

        self.assertEqual(args.hotel, "MAGNA")

    def test_returns_two_when_requested_and_result_has_divergences(self):
        result = SimpleNamespace(matched_count=10, divergent_count=2)
        args = [
            "--opera",
            "opera.xml",
            "--cmflex",
            "cmflex.xlsx",
            "--rede",
            "rede.xlsx",
            "--fail-on-divergence",
        ]
        with patch.object(cli, "run", return_value=result) as mocked_run:
            exit_code = cli.main(args)

        self.assertEqual(exit_code, 2)
        mocked_run.assert_called_once_with(
            Path("opera.xml"),
            Path("cmflex.xlsx"),
            Path("rede.xlsx"),
            Path("output/conferencia_recebimentos.json"),
        )

    def test_download_opera_mode_does_not_require_other_reports(self):
        config = object()
        with (
            patch.object(cli, "config_from_env", return_value=config),
            patch.object(
                cli,
                "run_opera_download",
                return_value=Path("output/recebimentos/opera.xml"),
            ) as download,
            patch.object(cli, "run") as reconcile,
        ):
            exit_code = cli.main(
                [
                    "--baixar-opera",
                    "--hotel",
                    "MAGNA - Magna Praia Hotel",
                    "--download-dir",
                    "downloads",
                    "--data",
                    "14/09/2026",
                ]
            )

        self.assertEqual(exit_code, 0)
        download.assert_called_once_with(
            config,
            "MAGNA - Magna Praia Hotel",
            Path("downloads"),
            report_date=cli.date(2026, 9, 14),
        )
        reconcile.assert_not_called()

    def test_download_cmflex_mode_does_not_require_other_reports(self):
        config = object()
        with (
            patch.object(
                cli, "cmflex_config_from_env", return_value=config
            ) as config_factory,
            patch.object(
                cli,
                "run_cmflex_download",
                return_value=Path("downloads/cmflex.xlsx"),
            ) as download,
            patch.object(cli, "run") as reconcile,
        ):
            exit_code = cli.main(
                [
                    "--baixar-cmflex",
                    "--download-dir",
                    "downloads",
                    "--data",
                    "14/09/2026",
                ]
            )

        self.assertEqual(exit_code, 0)
        config_factory.assert_called_once_with("MAGNA")
        download.assert_called_once_with(
            config,
            Path("downloads"),
            report_date=cli.date(2026, 9, 14),
        )
        reconcile.assert_not_called()

    def test_conference_finds_previous_day_files_and_archives_after_run(self):
        report_date = cli.date(2026, 9, 14)
        opera = Path("downloads/opera.xml")
        cmflex = Path("downloads/cmflex.xlsx")
        rede = Path("entrada/rede magna 14.09.xlsx")
        result = SimpleNamespace(matched_count=3, divergent_count=0)
        with (
            patch.object(cli, "previous_report_date", return_value=report_date),
            patch.object(
                cli, "find_downloaded_report", side_effect=[opera, cmflex]
            ),
            patch.object(cli, "find_rede_report", return_value=rede),
            patch.object(cli, "run", return_value=result) as reconcile,
            patch.object(
                cli,
                "save_conference_workbooks",
                return_value=(Path("arquivo/09 - SETEMBRO/14"), {}),
            ) as archive,
        ):
            exit_code = cli.main(
                [
                    "--conferir-baixados",
                    "--rede-dir",
                    "entrada",
                    "--download-dir",
                    "downloads",
                    "--archive-root",
                    "arquivo",
                    "--hotel",
                    "MAGNA - Magna Praia Hotel",
                ]
            )

        self.assertEqual(exit_code, 0)
        reconcile.assert_called_once_with(opera, cmflex, rede, None)
        archive.assert_called_once_with(
            opera,
            cmflex,
            rede,
            result,
            Path("arquivo"),
            report_date,
            "MAGNA - Magna Praia Hotel",
        )

    def test_conference_downloads_missing_opera_and_cmflex(self):
        report_date = cli.date(2026, 9, 14)
        opera = Path("downloads/opera.xml")
        cmflex = Path("downloads/cmflex.xlsx")
        rede = Path("entrada/rede magna 14.09.xlsx")
        result = SimpleNamespace(matched_count=3, divergent_count=0)
        opera_config = object()
        cmflex_config = object()
        with (
            patch.object(cli, "previous_report_date", return_value=report_date),
            patch.object(cli, "find_downloaded_report", side_effect=FileNotFoundError),
            patch.object(cli, "find_rede_report", return_value=rede),
            patch.object(cli, "config_from_env", return_value=opera_config),
            patch.object(
                cli, "cmflex_config_from_env", return_value=cmflex_config
            ),
            patch.object(cli, "run_opera_download", return_value=opera) as opera_rpa,
            patch.object(
                cli, "run_cmflex_download", return_value=cmflex
            ) as cmflex_rpa,
            patch.object(cli, "run", return_value=result),
            patch.object(
                cli,
                "save_conference_workbooks",
                return_value=(Path("output/recebimentos/conferencias"), {}),
            ),
        ):
            exit_code = cli.main(
                [
                    "--conferir-baixados",
                    "--rede-dir",
                    "entrada",
                    "--download-dir",
                    "downloads",
                    "--hotel",
                    "MAGNA",
                ]
            )

        self.assertEqual(exit_code, 0)
        opera_rpa.assert_called_once_with(
            opera_config,
            "MAGNA",
            Path("downloads"),
            report_date=report_date,
        )
        cmflex_rpa.assert_called_once_with(
            cmflex_config,
            Path("downloads"),
            report_date=report_date,
        )
