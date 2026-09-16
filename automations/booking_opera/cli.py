"""Interface de linha de comando da conciliação Booking × OPERA."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from automations.booking_opera import (
    ACTIVE_COMPANIES,
    SUPPORTED_COMPANIES,
    company_config_from_env,
    config_from_env,
    run,
)

LOGGER = logging.getLogger("booking-opera")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python main.py booking-opera",
        description="Concilia reservas da Booking com o OPERA.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Diretório dos relatórios (padrão: BOOKING_OUTPUT_DIR ou output).",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help="Pasta opcional para copiar o Excel final (ou BOOKING_ARCHIVE_DIR).",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--company",
        type=str.upper,
        choices=SUPPORTED_COMPANIES,
        help="Executa somente a empresa indicada.",
    )
    selection.add_argument(
        "--all-companies",
        action="store_true",
        help="Executa Charme, Wind e Magna em sequência.",
    )
    parser.add_argument(
        "--fail-on-divergence",
        action="store_true",
        help="Retorna código 2 quando houver divergências ou erros por reserva.",
    )
    return parser.parse_args(argv)


def progress(message: str, value: float) -> None:
    LOGGER.info("[%3d%%] %s", round(value * 100), message)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    companies = ACTIVE_COMPANIES if args.all_companies else (args.company,)
    try:
        configs = [
            (
                company,
                company_config_from_env(company, args.output_dir, args.archive_dir)
                if company
                else config_from_env(args.output_dir, args.archive_dir),
            )
            for company in companies
        ]
        if args.all_companies:
            for company, config in configs:
                try:
                    config.validate()
                except ValueError as error:
                    raise ValueError(f"{company}: {error}") from error

        has_divergence = False
        for company, config in configs:
            if company:
                LOGGER.info("Iniciando conferência Booking × OPERA: %s", company)
            result = run(config, progress=progress)
            LOGGER.info(
                "Resultado %s: %d OK, %d divergentes, %d não conferidas.",
                company or "Booking × OPERA",
                result.matched_count,
                result.divergent_count,
                result.not_compared_count,
            )
            LOGGER.info("Relatório Excel: %s", result.report_excel)
            if result.archive_excel is not None:
                LOGGER.info("Cópia do relatório Excel: %s", result.archive_excel)
            has_divergence = has_divergence or result.divergent_count > 0
        return 2 if args.fail_on_divergence and has_divergence else 0
    except Exception as error:
        LOGGER.exception("Automação encerrada: %s", error)
        return 1
