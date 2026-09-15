from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from automations.recebimentos import cli


class RecebimentosCliTests(TestCase):
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
                ]
            )

        self.assertEqual(exit_code, 0)
        download.assert_called_once_with(
            config,
            "MAGNA - Magna Praia Hotel",
            Path("downloads"),
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
            exit_code = cli.main(["--baixar-cmflex", "--download-dir", "downloads"])

        self.assertEqual(exit_code, 0)
        config_factory.assert_called_once_with("MAGNA")
        download.assert_called_once_with(config, Path("downloads"))
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
        opera_rpa.assert_called_once_with(opera_config, "MAGNA", Path("downloads"))
        cmflex_rpa.assert_called_once_with(cmflex_config, Path("downloads"))
