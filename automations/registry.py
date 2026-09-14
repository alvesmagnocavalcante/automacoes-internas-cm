"""Registro central das automações disponíveis."""

from __future__ import annotations

from collections.abc import Sequence

from automations.base import Automation


def run_booking_opera(argv: Sequence[str] | None = None) -> int:
    """Importa a automação somente quando ela for selecionada."""
    from automations.booking_opera.cli import main

    return main(argv)

AUTOMATIONS: dict[str, Automation] = {
    "booking-opera": Automation(
        slug="booking-opera",
        description="Conciliação de reservas da Booking com o OPERA.",
        execute=run_booking_opera,
    ),
}


def get_automation(slug: str) -> Automation:
    try:
        return AUTOMATIONS[slug]
    except KeyError as error:
        available = ", ".join(sorted(AUTOMATIONS))
        raise ValueError(
            f"Automação desconhecida: {slug}. Disponíveis: {available}"
        ) from error
