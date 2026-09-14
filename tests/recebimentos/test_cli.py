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
