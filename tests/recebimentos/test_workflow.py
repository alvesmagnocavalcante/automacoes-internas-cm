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
        self.assertIn("run: uv run python main.py conferencia-recebimentos --conferir-baixados", workflow)
        self.assertNotIn("if: ${{ vars.RECEBIMENTOS_REDE_DIR != '' }}", workflow)
