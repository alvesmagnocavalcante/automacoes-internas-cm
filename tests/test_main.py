from io import StringIO
from unittest import TestCase
from unittest.mock import patch

import main


class MainTests(TestCase):
    def test_runs_booking_opera_by_explicit_name(self):
        automation = main.AUTOMATIONS["booking-opera"]
        replacement = type(automation)(
            automation.slug, automation.description, lambda args: 7
        )
        with patch.dict(main.AUTOMATIONS, {"booking-opera": replacement}, clear=True):
            exit_code = main.main(["booking-opera", "--output-dir", "reports"])

        self.assertEqual(exit_code, 7)

    def test_requires_an_explicit_automation(self):
        errors = StringIO()
        with patch("sys.stderr", errors):
            exit_code = main.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Informe qual automação", errors.getvalue())

    def test_lists_registered_automations(self):
        output = StringIO()
        with patch("sys.stdout", output):
            exit_code = main.main(["--list"])

        self.assertEqual(exit_code, 0)
        self.assertIn("booking-opera", output.getvalue())
        self.assertIn("conferencia-recebimentos", output.getvalue())

    def test_unknown_automation_returns_two(self):
        errors = StringIO()
        with patch("sys.stderr", errors):
            exit_code = main.main(["nao-existe"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Automação desconhecida", errors.getvalue())
