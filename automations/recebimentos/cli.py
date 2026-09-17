"""CLI da conferência diária de recebimentos."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from automations.recebimentos.cmflex_browser import (
    config_from_env as cmflex_config_from_env,
)
from automations.recebimentos.cmflex_browser import run_cmflex_download
from automations.recebimentos.companies import ACTIVE_COMPANIES
from automations.recebimentos.daily_files import (
    find_downloaded_report,
    find_rede_report,
    find_rede_reports,
    previous_report_date,
)
from automations.recebimentos.opera_browser import (
    config_from_env,
    load_environment,
    run_opera_download,
)
from automations.recebimentos.service import run
from automations.recebimentos.workbooks import save_conference_workbooks

LOGGER = logging.getLogger("conferencia-recebimentos")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    load_environment()
    parser = argparse.ArgumentParser(
        prog="python main.py conferencia-recebimentos",
        description="Confere recebimentos entre OPERA, CMFlex e Rede.",
    )
    parser.add_argument("--opera", type=Path, help="Relatório XML ou XLSX do OPERA.")
    parser.add_argument("--cmflex", type=Path, help="Relatório XLSX do CMFlex.")
    parser.add_argument("--rede", type=Path, help="Relatório XLSX da Rede.")
    parser.add_argument(
        "--rede-dir",
        type=Path,
        default=(Path(value) if (value := os.getenv("RECEBIMENTOS_REDE_DIR")) else None),
        help="Pasta onde o setor disponibiliza o relatório da Rede.",
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=Path(
            os.getenv("RECEBIMENTOS_ARCHIVE_ROOT")
            or "output/recebimentos/conferencias"
        ),
        help="Raiz do arquivo mensal/diário das conferências.",
    )
    parser.add_argument(
        "--conferir-baixados",
        action="store_true",
        help=(
            "Localiza os relatórios do dia anterior, baixa OPERA/CMFlex quando "
            "necessário e arquiva a conferência."
        ),
    )
    parser.add_argument(
        "--all-companies",
        action="store_true",
        help="Confere sequencialmente TAIBA, CHARME, CUMBUCO e MAGNA.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Com --all-companies, confere apenas empresas com planilha Rede disponível.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/conferencia_recebimentos.json"),
        help="Arquivo JSON detalhado do resultado.",
    )
    parser.add_argument(
        "--fail-on-divergence",
        action="store_true",
        help="Retorna código 2 quando houver divergências.",
    )
    download_mode = parser.add_mutually_exclusive_group()
    download_mode.add_argument(
        "--baixar-opera",
        action="store_true",
        help="Testa o RPA e baixa somente o relatório Pagamentos Financeiros.",
    )
    download_mode.add_argument(
        "--baixar-cmflex",
        action="store_true",
        help="Baixa somente o relatório Lançamentos de Documentos do CMFlex.",
    )
    parser.add_argument(
        "--hotel",
        default=os.getenv("RECEBIMENTOS_OPERA_HOTEL") or os.getenv("OPERA_HOTEL", ""),
        help="Hotel/resort do OPERA; usa RECEBIMENTOS_OPERA_HOTEL ou OPERA_HOTEL.",
    )
    parser.add_argument(
        "--empresa-cmflex",
        default=os.getenv("RECEBIMENTOS_CMFLEX_COMPANY")
        or os.getenv("CMFLEX_COMPANY", "MAGNA"),
        help="Empresa do CMFlex; usa RECEBIMENTOS_CMFLEX_COMPANY ou MAGNA.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("output/recebimentos"),
        help="Pasta para os relatórios baixados.",
    )
    return parser.parse_args(argv)


def _run_all_companies(args: argparse.Namespace) -> int:
    if args.baixar_opera or args.baixar_cmflex or args.opera or args.cmflex or args.rede:
        raise ValueError(
            "--all-companies não aceita modos de download ou arquivos individuais."
        )
    if args.rede_dir is None:
        raise ValueError("Informe --rede-dir ou RECEBIMENTOS_REDE_DIR.")

    report_date = previous_report_date(date.today())
    rede_reports = find_rede_reports(
        args.rede_dir, report_date, require_all=not args.allow_partial
    )
    companies = [
        company for company in ACTIVE_COMPANIES if company.code in rede_reports
    ]
    if args.allow_partial:
        LOGGER.warning(
            "Teste parcial: conferindo somente %s; demais empresas não serão processadas.",
            ", ".join(company.code for company in companies),
        )
    hotels = {company.code: company.opera_hotel for company in companies}
    missing = [code for code, hotel in hotels.items() if not hotel]
    if missing:
        raise ValueError(
            "Configure RECEBIMENTOS_OPERA_HOTEL_<EMPRESA> para: "
            + ", ".join(missing)
        )
    opera_config = config_from_env()
    opera_config.validate()
    cmflex_config_from_env(companies[0].cmflex_name).validate()

    has_divergence = False
    for company in companies:
        LOGGER.info("Iniciando conferência de recebimentos: %s", company.code)
        download_dir = args.download_dir / company.code.lower()
        try:
            opera = find_downloaded_report(download_dir, "opera", report_date)
        except (FileNotFoundError, NotADirectoryError):
            opera = run_opera_download(opera_config, hotels[company.code], download_dir)
        try:
            cmflex = find_downloaded_report(download_dir, "cmflex", report_date)
        except (FileNotFoundError, NotADirectoryError):
            cmflex = run_cmflex_download(
                cmflex_config_from_env(company.cmflex_name), download_dir
            )
        rede = rede_reports[company.code]
        result = run(opera, cmflex, rede, None)
        destination, _ = save_conference_workbooks(
            opera,
            cmflex,
            rede,
            result,
            args.archive_root,
            report_date,
            company.code,
            company.code,
        )
        LOGGER.info(
            "%s: %d OK, %d divergentes. Arquivo: %s",
            company.code,
            result.matched_count,
            result.divergent_count,
            destination,
        )
        has_divergence |= bool(result.divergent_count)
    return 2 if args.fail_on_divergence and has_divergence else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    archive_request = None
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        if args.allow_partial and not args.all_companies:
            raise ValueError("--allow-partial exige --all-companies.")
        if args.all_companies:
            return _run_all_companies(args)
        if args.baixar_opera:
            if not args.hotel.strip():
                raise ValueError(
                    "Informe --hotel ou RECEBIMENTOS_OPERA_HOTEL para baixar o OPERA."
                )
            downloaded = run_opera_download(
                config_from_env(), args.hotel, args.download_dir
            )
            LOGGER.info("Relatório OPERA baixado: %s", downloaded)
            return 0

        if args.baixar_cmflex:
            downloaded = run_cmflex_download(
                cmflex_config_from_env(args.empresa_cmflex),
                args.download_dir,
            )
            LOGGER.info("Relatório CMFlex baixado: %s", downloaded)
            return 0

        if args.conferir_baixados:
            if args.rede_dir is None:
                raise ValueError("Informe --rede-dir ou RECEBIMENTOS_REDE_DIR.")
            report_date = previous_report_date(date.today())
            try:
                args.opera = find_downloaded_report(
                    args.download_dir, "opera", report_date
                )
            except FileNotFoundError:
                if not args.hotel.strip():
                    raise ValueError(
                        "Informe --hotel ou RECEBIMENTOS_OPERA_HOTEL para baixar o OPERA."
                    ) from None
                LOGGER.info("Relatório OPERA ausente; iniciando download.")
                args.opera = run_opera_download(
                    config_from_env(), args.hotel, args.download_dir
                )

            try:
                args.cmflex = find_downloaded_report(
                    args.download_dir, "cmflex", report_date
                )
            except FileNotFoundError:
                LOGGER.info("Relatório CMFlex ausente; iniciando download.")
                args.cmflex = run_cmflex_download(
                    cmflex_config_from_env(args.empresa_cmflex),
                    args.download_dir,
                )
            args.rede = find_rede_report(args.rede_dir, report_date)
            archive_request = (
                args.archive_root,
                report_date,
                args.hotel or args.empresa_cmflex,
            )

        missing = [
            name
            for name, value in (
                ("--opera", args.opera),
                ("--cmflex", args.cmflex),
                ("--rede", args.rede),
            )
            if value is None
        ]
        if missing:
            raise ValueError(
                "Informe os relatórios para a conferência: " + ", ".join(missing)
            )
        result = run(
            args.opera,
            args.cmflex,
            args.rede,
            None if archive_request is not None else args.output,
        )
        if archive_request is not None:
            destination, _ = save_conference_workbooks(
                args.opera,
                args.cmflex,
                args.rede,
                result,
                *archive_request,
            )
            args.output = destination
    except Exception as error:
        LOGGER.exception("Conferência encerrada: %s", error)
        return 1
    LOGGER.info(
        "Resultado: %d OK, %d divergentes. Detalhes: %s",
        result.matched_count,
        result.divergent_count,
        args.output,
    )
    return 2 if args.fail_on_divergence and result.divergent_count else 0
