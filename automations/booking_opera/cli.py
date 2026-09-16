"""Interface de linha de comando da conciliação Booking × OPERA."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from automations.booking_opera import config_from_env, run

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
    try:
        result = run(
            config_from_env(args.output_dir, args.archive_dir), progress=progress
        )
    except Exception as error:
        LOGGER.exception("Automação encerrada: %s", error)
        return 1

    LOGGER.info(
        "Resultado: %d OK, %d divergentes, %d não conferidas.",
        result.matched_count,
        result.divergent_count,
        result.not_compared_count,
    )
    LOGGER.info("Relatório Excel: %s", result.report_excel)
    if result.archive_excel is not None:
        LOGGER.info("Cópia do relatório Excel: %s", result.archive_excel)
    if args.fail_on_divergence and result.divergent_count:
        return 2
    return 0
