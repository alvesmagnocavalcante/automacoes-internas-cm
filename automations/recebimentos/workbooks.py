"""Geração dos três relatórios Excel marcados pela conferência."""

from __future__ import annotations

import os
import shutil
import subprocess
import warnings
from copy import copy
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from automations.recebimentos.models import ReconciliationResult
from automations.recebimentos.normalization import normalize

YELLOW = "FFFF00"
GROUP_COLORS = ("FF99CC", "CC66FF", "99CCFF", "99FF99", "FFCC99")

def _reset_inherited_permissions(path: Path) -> None:
    """Faz o arquivo herdar a ACL já administrada na pasta de destino."""
    if os.name == "nt":
        subprocess.run(
            ["icacls", str(path), "/reset", "/Q"],
            check=True,
            capture_output=True,
        )
    else:
        os.chmod(path, 0o644)


def _copy_with_permissions(src: Path, dst: Path) -> None:
    """Copia o conteúdo e restaura a herança da pasta de destino."""
    shutil.copyfile(src, dst)
    _reset_inherited_permissions(dst)

CMFLEX_COLUMNS = (
    "Cliente",
    "Numero",
    "SistemaLancamento",
    "Valor",
    "ValorOutraMoeda",
    "Saldo",
    "ValorAlteradores",
    "ValorLiquido",
    "DataEmissao",
)

OPERA_COLUMNS = (
    "GRP_FIRST",
    "TRX_NO",
    "TRX_DESC",
    "FULL_NAME",
    "FOLIO_NO",
    "GUEST_ACCOUNT_CREDIT",
    "RESV_NAME_ID",
    "ROOM",
    "REMARK",
    "APPROVAL_CODE",
    "CONFIRMATION_NO",
    "CASHIER_ID",
    "USER_NAME",
    "CASH_ID_USER_NAME",
    "CS_TRX_AMT_SECOND",
    "CS_TRX_AMOUNT_FIRST",
    "CS_TRX_AMOUNT_REP",
    "LOGO",
)


def save_conference_workbooks(
    opera_path: Path,
    cmflex_path: Path,
    rede_path: Path,
    result: ReconciliationResult,
    root: Path,
    report_date: date,
    hotel: str,
    company_code: str | None = None,
) -> tuple[Path, dict[str, Path]]:
    """Cria a pasta diária contendo somente OPERA, CMFlex e Rede em XLSX."""
    from automations.recebimentos.daily_files import daily_directory

    destination = daily_directory(root, report_date)
    if company_code is not None:
        destination /= company_code
    destination.parent.mkdir(parents=True, exist_ok=True)
    label = hotel.split(" - ", 1)[0].strip().title()
    names = {
        "Opera": f"Opera {label} {report_date:%d.%m}.xlsx",
        "CmFlex": f"CmFlex {label} {report_date:%d.%m}.xlsx",
        "Rede": f"Rede {label} {report_date:%d.%m}.xlsx",
    }
    colors = _matched_colors(result)
    with TemporaryDirectory(prefix=".conferencia-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        _save_opera(opera_path, staging / names["Opera"], colors["opera"])
        _save_cmflex(cmflex_path, staging / names["CmFlex"], colors["cmflex"])
        _save_rede(rede_path, staging / names["Rede"], colors["rede"])

        destination.mkdir(parents=True, exist_ok=True)
        for existing in destination.iterdir():
            if existing.is_file():
                existing.unlink()
            elif existing.is_dir():
                shutil.rmtree(existing)
        for name in names.values():
            _copy_with_permissions(staging / name, destination / name)

    paths = {system: destination / name for system, name in names.items()}
    return destination, paths


def _matched_colors(
    result: ReconciliationResult,
) -> dict[str, dict[str, str]]:
    colors: dict[str, dict[str, str]] = {
        "opera": {},
        "cmflex": {},
        "rede": {},
    }
    group_index = 0
    for item in result.items:
        if item.status != "OK":
            continue
        color = YELLOW
        if item.comparison == "Rede x OPERA" and (
            len(item.external_ids) > 1 or len(item.opera_ids) > 1
        ):
            color = GROUP_COLORS[group_index % len(GROUP_COLORS)]
            group_index += 1
        for transaction_id in item.opera_ids:
            colors["opera"][transaction_id] = color
        target = "rede" if item.comparison == "Rede x OPERA" else "cmflex"
        for external_id in item.external_ids:
            colors[target][external_id] = color
    return colors


def _load(path: Path):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Workbook contains no default style")
        return load_workbook(path)


def _header_map(sheet, row: int = 1) -> dict[str, int]:
    return {
        normalize(sheet.cell(row, column).value): column
        for column in range(1, sheet.max_column + 1)
        if sheet.cell(row, column).value is not None
    }


def _fill(cell, color: str) -> None:
    cell.fill = PatternFill(fill_type="solid", fgColor=color)


def _save_cmflex(source_path: Path, target_path: Path, colors: dict[str, str]) -> None:
    source_book = _load(source_path)
    source = source_book.active
    headers = _header_map(source)
    missing = [name for name in CMFLEX_COLUMNS if normalize(name) not in headers]
    if missing:
        source_book.close()
        raise ValueError("Colunas do CMFlex ausentes: " + ", ".join(missing))

    target_book = Workbook()
    target = target_book.active
    target.title = source.title
    source_columns = [headers[normalize(name)] for name in CMFLEX_COLUMNS]
    for target_column, source_column in enumerate(source_columns, start=1):
        source_letter = source.cell(1, source_column).column_letter
        target_letter = target.cell(1, target_column).column_letter
        target.column_dimensions[target_letter].width = source.column_dimensions[
            source_letter
        ].width
        for row in range(1, source.max_row + 1):
            _copy_cell(source.cell(row, source_column), target.cell(row, target_column))
    for row, height in source.row_dimensions.items():
        target.row_dimensions[row].height = height.height

    document_column = headers[normalize("Numero")]
    for row in range(2, source.max_row + 1):
        document = str(source.cell(row, document_column).value or "").strip()
        if color := colors.get(document):
            _fill(target.cell(row, 4), color)
    target.auto_filter.ref = f"A1:I{source.max_row}"
    target_book.save(target_path)
    target_book.close()
    source_book.close()


def _copy_cell(source, target) -> None:
    target.value = source.value
    if source.has_style:
        # StyleArray guarda IDs do workbook de origem. Copiar `_style`
        # diretamente entre workbooks pode gerar referências inválidas em
        # xl/styles.xml; os atributos públicos registram cada estilo no destino.
        target.font = copy(source.font)
        target.fill = copy(source.fill)
        target.border = copy(source.border)
        target.alignment = copy(source.alignment)
        target.protection = copy(source.protection)
        target.number_format = source.number_format


def _save_opera(source_path: Path, target_path: Path, colors: dict[str, str]) -> None:
    if source_path.suffix.casefold() == ".xml":
        book = _opera_xml_workbook(source_path)
    else:
        book = _load(source_path)
    sheet = book.active
    headers = _header_map(sheet)
    transaction_column = headers.get("trx_no")
    amount_column = headers.get("guest_account_credit")
    if transaction_column is None or amount_column is None:
        book.close()
        raise ValueError("Colunas TRX_NO/GUEST_ACCOUNT_CREDIT ausentes no OPERA.")
    for row in range(2, sheet.max_row + 1):
        transaction = str(sheet.cell(row, transaction_column).value or "").strip()
        if color := colors.get(transaction):
            _fill(sheet.cell(row, amount_column), color)
    book.save(target_path)
    book.close()


def _opera_xml_workbook(path: Path):
    root = ElementTree.parse(path).getroot()
    rows = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "G_TRANSACTION":
            continue
        record = {child.tag.rsplit("}", 1)[-1].upper(): child.text for child in node}
        rows.append([_opera_value(record, column) for column in OPERA_COLUMNS])
    if not rows:
        raise ValueError(f"Nenhuma transação encontrada no XML do OPERA: {path}")

    book = Workbook()
    sheet = book.active
    sheet.title = "Planilha1"
    sheet.append(OPERA_COLUMNS)
    for row in rows:
        sheet.append(row)
    table = Table(displayName="Tabela1", ref=f"A1:R{sheet.max_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    sheet.add_table(table)
    for column in (6, 15, 16, 17):
        for row in range(2, sheet.max_row + 1):
            sheet.cell(row, column).number_format = '[$R$-pt-BR] #,##0.00'
    return book


def _opera_value(record: dict[str, str | None], column: str) -> object:
    source = "TRX_CODE" if column == "GRP_FIRST" else column
    value = record.get(column) or record.get(source) or ""
    if column in {
        "GRP_FIRST",
        "TRX_NO",
        "GUEST_ACCOUNT_CREDIT",
        "RESV_NAME_ID",
        "CONFIRMATION_NO",
        "CASHIER_ID",
        "CS_TRX_AMT_SECOND",
        "CS_TRX_AMOUNT_FIRST",
        "CS_TRX_AMOUNT_REP",
    }:
        try:
            number = Decimal(value)
            return int(number) if number == number.to_integral() else float(number)
        except InvalidOperation:
            pass
    return value


def _save_rede(source_path: Path, target_path: Path, colors: dict[str, str]) -> None:
    book = _load(source_path)
    sheet = book.active
    header_row = _find_header_row(sheet, "nsu/cv")
    headers = _header_map(sheet, header_row)
    nsu_column = headers["nsu/cv"]
    amount_column = headers.get("valor da venda original")
    if amount_column is None:
        book.close()
        raise ValueError("Coluna 'valor da venda original' ausente na Rede.")
    for row in range(header_row + 1, sheet.max_row + 1):
        nsu = str(sheet.cell(row, nsu_column).value or "").strip()
        if color := colors.get(nsu):
            _fill(sheet.cell(row, amount_column), color)
    book.save(target_path)
    book.close()


def _find_header_row(sheet, required: str) -> int:
    for row in range(1, min(sheet.max_row, 20) + 1):
        if required in _header_map(sheet, row):
            return row
    raise ValueError(f"Cabeçalho {required!r} não encontrado em {sheet.title}.")
