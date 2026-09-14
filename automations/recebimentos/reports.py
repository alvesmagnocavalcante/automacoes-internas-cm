"""Persistência do resultado da conferência em formato auditável."""

from __future__ import annotations

import json
from pathlib import Path

from automations.recebimentos.models import ReconciliationResult


def save_json(path: Path, result: ReconciliationResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
