"""Orquestração da conferência a partir de relatórios já baixados."""

from __future__ import annotations

from pathlib import Path

from automations.recebimentos.domain import reconcile
from automations.recebimentos.models import ReconciliationResult
from automations.recebimentos.parsers import parse_cmflex, parse_opera, parse_rede
from automations.recebimentos.reports import save_json


def run(
    opera_path: Path,
    cmflex_path: Path,
    rede_path: Path,
    output_path: Path | None = None,
) -> ReconciliationResult:
    result = reconcile(
        parse_opera(opera_path),
        parse_cmflex(cmflex_path),
        parse_rede(rede_path),
    )
    if output_path is not None:
        save_json(output_path, result)
    return result
