from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from automations.booking_opera import cli


class BookingOperaCliTests(TestCase):
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
