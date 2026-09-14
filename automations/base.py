"""Contrato compartilhado pelo executor de automações."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Automation:
    """Metadados e ponto de entrada de uma automação."""

    slug: str
    description: str
    execute: Callable[[Sequence[str] | None], int]
