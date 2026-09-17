"""Descoberta e arquivamento dos arquivos da conferência diária."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from automations.recebimentos.companies import COMPANIES, Company
from automations.recebimentos.parsers import opera_xml_has_transactions

MONTH_NAMES = (
    "",
    "JANEIRO",
    "FEVEREIRO",
    "MARÇO",
    "ABRIL",
    "MAIO",
    "JUNHO",
    "JULHO",
    "AGOSTO",
    "SETEMBRO",
    "OUTUBRO",
    "NOVEMBRO",
    "DEZEMBRO",
)


def previous_report_date(execution_date: date | None = None) -> date:
    return (execution_date or date.today()) - timedelta(days=1)


def daily_directory(root: Path, report_date: date) -> Path:
    return root / f"{report_date:%m} - {MONTH_NAMES[report_date.month]}" / f"{report_date:%d}"


def _date_tokens(report_date: date) -> tuple[str, ...]:
    return (
        report_date.strftime("%d.%m"),
        report_date.strftime("%d-%m"),
        report_date.strftime("%d_%m"),
        report_date.isoformat(),
    )


def find_rede_report(directory: Path, report_date: date) -> Path:
    if not directory.is_dir():
        raise FileNotFoundError(f"Pasta da Rede não encontrada: {directory}")
    tokens = _date_tokens(report_date)
    daily = daily_directory(directory, report_date)
    matches = _rede_matches(directory, tokens)
    if not matches and daily.is_dir():
        matches = _rede_matches(daily, tokens)
    if not matches:
        raise FileNotFoundError(
            f"Relatório Rede de {report_date:%d/%m/%Y} não encontrado em {directory}."
        )
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise RuntimeError(f"Mais de um relatório Rede encontrado: {names}")
    return matches[0]


def identify_rede_company(path: Path) -> Company | None:
    """Identifica a empresa pelo nome; rejeita nomes ambíguos ou sem empresa."""
    normalized = unicodedata.normalize("NFKD", path.stem)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    words = set(re.findall(r"[a-z]+", normalized.casefold()))
    matches = [
        company
        for company in COMPANIES
        if any(alias in words for alias in company.rede_names)
    ]
    if {"central", "servicos"} <= words or {"cm", "central"} <= words:
        if matches:
            raise ValueError(f"Arquivo Rede mistura CM CENTRAL e hotel: {path.name!r}.")
        return None
    if len(matches) != 1:
        raise ValueError(
            f"Empresa da Rede ausente ou ambígua no arquivo {path.name!r}; "
            "use CHARME, CUMBUCO, ICARAIZINHO, TAIBA ou MAGNA no nome."
        )
    return matches[0]


def find_rede_reports(directory: Path, report_date: date) -> dict[str, Path]:
    """Confere todos os arquivos do dia antes de iniciar os RPAs."""
    if not directory.is_dir():
        raise FileNotFoundError(f"Pasta da Rede não encontrada: {directory}")
    daily = daily_directory(directory, report_date)
    matches = _rede_matches(directory, _date_tokens(report_date))
    if not matches and daily.is_dir():
        matches = _rede_matches(daily, _date_tokens(report_date))
    reports: dict[str, Path] = {}
    for path in matches:
        company = identify_rede_company(path)
        if company is None:
            continue
        if company.code in reports:
            raise RuntimeError(
                f"Mais de um relatório Rede de {company.code}: "
                f"{reports[company.code].name}, {path.name}"
            )
        reports[company.code] = path
    missing = [company.code for company in COMPANIES if company.code not in reports]
    if missing:
        raise FileNotFoundError(
            f"Relatórios Rede de {report_date:%d/%m/%Y} ausentes em {directory}: "
            + ", ".join(missing)
        )
    return reports


def _rede_matches(directory: Path, tokens: tuple[str, ...]) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.casefold() in {".xlsx", ".xlsm"}
        and "rede" in path.name.casefold()
        and any(token in path.stem.casefold() for token in tokens)
    )


def find_downloaded_report(directory: Path, system: str, report_date: date) -> Path:
    prefix = f"{system.casefold()}_recebimentos_{report_date.isoformat()}"
    matches = sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.stem.casefold().startswith(prefix)
        and _is_usable_download(path, system)
    )
    if not matches:
        raise FileNotFoundError(
            f"Esperado um relatório {system} de {report_date:%d/%m/%Y} em {directory}; "
            "encontrados: 0."
        )
    return max(matches, key=lambda path: path.stat().st_mtime_ns)


def _is_usable_download(path: Path, system: str) -> bool:
    if system.casefold() != "opera" or path.suffix.casefold() != ".xml":
        return True
    return opera_xml_has_transactions(path)
