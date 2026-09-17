"""Empresas atendidas pela conferência e seus nomes nos sistemas de origem."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    code: str
    cmflex_name: str
    rede_names: tuple[str, ...]
    active: bool = True

    @property
    def opera_hotel(self) -> str:
        value = os.getenv(f"RECEBIMENTOS_OPERA_HOTEL_{self.code}", "").strip()
        if self.code == "MAGNA" and not value:
            value = os.getenv("RECEBIMENTOS_OPERA_HOTEL", "").strip()
        return value


COMPANIES = (
    Company("CHARME", "CARMEL CHARME HOSPEDAGEM", ("charme",)),
    Company("CUMBUCO", "CARMEL CUMBUCO", ("cumbuco", "wind")),
    Company(
        "ICARAIZINHO", "CARMEL ICARAIZINHO",
        ("icaraizinho", "acarizinho"), active=False,
    ),
    Company("TAIBA", "CARMEL TAÍBA", ("taiba",)),
    Company("MAGNA", "MAGNA PRAIA", ("magna",)),
)

ACTIVE_COMPANIES = tuple(company for company in COMPANIES if company.active)


def get_company(code: str) -> Company:
    for company in COMPANIES:
        if company.code == code.upper():
            return company
    raise ValueError(f"Empresa de recebimentos não suportada: {code}.")
