"""Public facade and composition root for Booking × OPERA reconciliation."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from threading import Event

from automations.booking_opera import browser
from automations.booking_opera.models import (
    BOOKING_URL,
    OPERA_URL,
    BookingConfig,
    BookingDependencies,
    BookingResult,
    Progress,
)
from automations.booking_opera.service import BookingReconciliationService

ACTIVE_COMPANIES = ("MAGNA", "CHARME", "WIND")
SUPPORTED_COMPANIES = (*ACTIVE_COMPANIES, "ACARIZINHO")

__all__ = [
    "BookingConfig",
    "BookingDependencies",
    "BookingResult",
    "ACTIVE_COMPANIES",
    "SUPPORTED_COMPANIES",
    "company_config_from_env",
    "config_from_env",
    "default_dependencies",
    "run",
]


def default_dependencies() -> BookingDependencies:
    return BookingDependencies(
        browser_factory=browser.create_browser,
        booking_login=browser.login_booking,
        table_reader=browser.booking_table,
        opera_login=browser.login_opera,
        reservations_opener=browser.open_reservations,
        total_reader=browser.opera_total,
        hotel_selector=browser.select_hotel,
    )


def run(
    config: BookingConfig,
    progress: Progress | None = None,
    cancel: Event | None = None,
    dependencies: BookingDependencies | None = None,
) -> BookingResult:
    service = BookingReconciliationService(dependencies or default_dependencies())
    return service.run(config, progress, cancel)


def config_from_env(
    output_dir: Path | None = None, archive_dir: Path | None = None
) -> BookingConfig:
    configured_archive = os.getenv("BOOKING_ARCHIVE_DIR", "").strip()
    return BookingConfig(
        os.getenv("BOOKING_USERNAME", ""),
        os.getenv("BOOKING_PASSWORD", ""),
        os.getenv("OPERA_USERNAME", ""),
        os.getenv("OPERA_PASSWORD", ""),
        output_dir=output_dir
        or Path(os.getenv("BOOKING_OUTPUT_DIR", os.getenv("PLUTO_OUTPUT_DIR", "output"))),
        hotel_name=os.getenv("OPERA_HOTEL", ""),
        booking_url=os.getenv("BOOKING_URL", BOOKING_URL),
        opera_url=os.getenv("OPERA_URL", OPERA_URL),
        archive_dir=archive_dir
        or (Path(configured_archive) if configured_archive else None),
    )


def company_config_from_env(
    company: str,
    output_dir: Path | None = None,
    archive_dir: Path | None = None,
) -> BookingConfig:
    company = company.upper()
    if company not in SUPPORTED_COMPANIES:
        raise ValueError(f"Empresa Booking não suportada: {company}")

    shared = config_from_env(output_dir, archive_dir)
    username = os.getenv(f"BOOKING_{company}_USERNAME", "")
    password = os.getenv(f"BOOKING_{company}_PASSWORD", "")
    if company == "MAGNA" and not (username or password):
        username, password = shared.booking_username, shared.booking_password

    hotel = os.getenv(f"OPERA_HOTEL_{company}", "").strip()
    if company == "MAGNA" and not hotel:
        hotel = shared.hotel_name

    folder = company.lower()
    return replace(
        shared,
        booking_username=username,
        booking_password=password,
        hotel_name=hotel,
        output_dir=shared.output_dir / folder,
        archive_dir=shared.archive_dir / folder if shared.archive_dir else None,
    )
