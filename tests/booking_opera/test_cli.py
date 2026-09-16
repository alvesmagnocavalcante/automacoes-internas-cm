from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from automations.booking_opera import cli


class BookingOperaCliTests(TestCase):
    def test_all_companies_validate_all_configs_before_starting(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(cli, "run") as run,
        ):
            exit_code = cli.main(["--all-companies"])

        self.assertEqual(exit_code, 1)
        run.assert_not_called()

    def test_all_companies_stop_after_first_failed_run(self):
        configs = [
            SimpleNamespace(hotel_name=name, validate=lambda: None)
            for name in ("MAGNA", "CHARME", "WIND")
        ]
        with (
            patch.object(cli, "company_config_from_env", side_effect=configs),
            patch.object(cli, "run", side_effect=RuntimeError("falha")) as run,
        ):
            exit_code = cli.main(["--all-companies"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(run.call_count, 1)

    def test_all_companies_run_sequentially_in_fixed_order(self):
        result = SimpleNamespace(
            matched_count=1,
            divergent_count=0,
            not_compared_count=0,
            report_excel=Path("output/report.xlsx"),
            archive_excel=None,
        )
        events = []

        def run_company(config, **_kwargs):
            events.append(config.hotel_name)
            return result

        with (
            patch.dict(
                "os.environ",
                {
                    "OPERA_USERNAME": "opera",
                    "OPERA_PASSWORD": "senha",
                    **{
                        f"BOOKING_{name}_{field}": f"{name}-{field}"
                        for name in ("MAGNA", "CHARME", "WIND")
                        for field in ("USERNAME", "PASSWORD")
                    },
                    **{
                        f"OPERA_HOTEL_{name}": name
                        for name in ("MAGNA", "CHARME", "WIND")
                    },
                },
                clear=True,
            ),
            patch.object(cli, "run", side_effect=run_company),
        ):
            exit_code = cli.main(["--all-companies"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(events, ["MAGNA", "CHARME", "WIND"])

    def test_returns_two_when_requested_and_result_has_divergences(self):
        result = SimpleNamespace(
            matched_count=2,
            divergent_count=1,
            not_compared_count=3,
            report_excel=Path("output/report.xlsx"),
            archive_excel=None,
        )
        with patch.object(cli, "run", return_value=result):
            exit_code = cli.main(["--fail-on-divergence"])

        self.assertEqual(exit_code, 2)

    def test_returns_one_when_configuration_is_invalid(self):
        with patch.object(cli, "run", side_effect=ValueError("credencial ausente")):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 1)

    def test_returns_zero_when_run_succeeds(self):
        result = SimpleNamespace(
            matched_count=2,
            divergent_count=0,
            not_compared_count=0,
            report_excel=Path("output/report.xlsx"),
            archive_excel=None,
        )
        with patch.object(cli, "run", return_value=result):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 0)
