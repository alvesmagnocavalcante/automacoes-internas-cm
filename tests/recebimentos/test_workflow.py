from pathlib import Path
from unittest import TestCase

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "conferencia-recebimentos.yml"
)


class RecebimentosWorkflowTests(TestCase):
    def test_uses_only_recebimentos_secrets_for_credentials_and_paths(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        names = (
            "RECEBIMENTOS_OPERA_USERNAME",
            "RECEBIMENTOS_OPERA_PASSWORD",
            "RECEBIMENTOS_OPERA_HOTEL",
            "RECEBIMENTOS_CMFLEX_USERNAME",
            "RECEBIMENTOS_CMFLEX_PASSWORD",
            "RECEBIMENTOS_REDE_DIR",
            "RECEBIMENTOS_ARCHIVE_ROOT",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIn(f"{name}: ${{{{ secrets.{name} }}}}", workflow)

        self.assertNotIn("secrets.OPERA_USERNAME", workflow)
        self.assertNotIn("secrets.OPERA_PASSWORD", workflow)
        self.assertNotIn("secrets.CMFLEX_USERNAME", workflow)
        self.assertNotIn("secrets.CMFLEX_PASSWORD", workflow)

    def test_conference_step_is_not_silently_skipped(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('"conferencia-recebimentos", "--all-companies"', workflow)
        self.assertIn('$arguments += "--allow-partial"', workflow)
        self.assertIn('$arguments += @("--data", $env:REPORT_DATE)', workflow)
        self.assertNotIn("if: ${{ vars.RECEBIMENTOS_REDE_DIR != '' }}", workflow)

    def test_maps_every_opera_hotel_to_the_runner(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for company in ("CHARME", "CUMBUCO", "TAIBA", "MAGNA"):
            with self.subTest(company=company):
                self.assertIn(f"RECEBIMENTOS_OPERA_HOTEL_{company}:", workflow)
        self.assertNotIn("RECEBIMENTOS_OPERA_HOTEL_ICARAIZINHO:", workflow)
