"""Regras de conciliação independentes de arquivos e automação de navegador."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from decimal import Decimal
from itertools import combinations

from automations.recebimentos.models import (
    CmflexPayment,
    OperaPayment,
    ReconciliationItem,
    ReconciliationResult,
    RedePayment,
)
from automations.recebimentos.normalization import normalize

TOLERANCE = Decimal("0.01")


def classify_opera(payment: OperaPayment) -> str | None:
    description = normalize(payment.description)
    if payment.transaction_code == "9086" or "dinheiro" in description:
        return "DINHEIRO"
    if payment.transaction_code == "9087" or "pix" in description:
        return "PIX"
    if payment.transaction_code == "9090" or "faturar" in description:
        return "A FATURAR"
    if "deposit" in description:
        return "DEPÓSITO"
    if description.startswith("rede ") or payment.transaction_code.startswith("93"):
        return "CARTÃO"
    return None


def classify_cmflex(payment: CmflexPayment) -> str | None:
    if payment.amount == 0:
        return None
    customer = normalize(payment.customer)
    document_type = normalize(payment.document_type)
    if customer == "dinheiro" or "movimento de caixa" in document_type:
        return "DINHEIRO"
    if "nota fiscal" in document_type:
        return "A FATURAR"
    if customer == "deposito" and document_type == "deposito":
        return "PIX"
    if customer == "deposito" and "estorno" in document_type:
        return "ESTORNO"
    if customer == "deposito" and "extrato bancario" in document_type:
        return "DEPÓSITO"
    return None


def reconcile(
    opera: list[OperaPayment],
    cmflex: list[CmflexPayment],
    rede: list[RedePayment],
) -> ReconciliationResult:
    items = [
        *_reconcile_cards(opera, rede),
        *_reconcile_cmflex(opera, cmflex, "DINHEIRO"),
        *_reconcile_cmflex(opera, cmflex, "PIX"),
        *_reconcile_cmflex(opera, cmflex, "A FATURAR"),
        *_reconcile_deposits(opera, cmflex),
    ]
    relevant_opera = sum(classify_opera(payment) is not None for payment in opera)
    relevant_cmflex = sum(classify_cmflex(payment) is not None for payment in cmflex)
    relevant_rede = sum(_is_rede_card(payment) for payment in rede)
    return ReconciliationResult(
        items=tuple(sorted(items, key=lambda item: (item.category, item.key))),
        ignored_opera_count=len(opera) - relevant_opera,
        ignored_cmflex_count=len(cmflex) - relevant_cmflex,
        ignored_rede_count=len(rede) - relevant_rede,
    )


def _is_rede_card(payment: RedePayment) -> bool:
    return normalize(payment.status) == "aprovada" and normalize(payment.modality) in {
        "credito",
        "debito",
    }


def _reconcile_cards(
    opera: list[OperaPayment], rede: list[RedePayment]
) -> list[ReconciliationItem]:
    remaining_opera = [
        payment for payment in opera if classify_opera(payment) == "CARTÃO"
    ]
    remaining_rede = [payment for payment in rede if _is_rede_card(payment)]
    items = []

    for rede_row in list(remaining_rede):
        match = next(
            (
                opera_row
                for opera_row in remaining_opera
                if _cards_compatible(opera_row, rede_row)
                and abs(opera_row.amount - rede_row.amount) <= TOLERANCE
            ),
            None,
        )
        if match is None:
            continue
        remaining_rede.remove(rede_row)
        remaining_opera.remove(match)
        items.append(_card_item((rede_row,), (match,)))

    for rede_row in list(remaining_rede):
        matches = _amount_subset(
            remaining_opera,
            rede_row.amount,
            lambda row: row.amount,
            lambda row: _cards_compatible(row, rede_row),
        )
        if not matches:
            continue
        remaining_rede.remove(rede_row)
        for match in matches:
            remaining_opera.remove(match)
        items.append(_card_item((rede_row,), matches))

    for opera_row in list(remaining_opera):
        matches = _amount_subset(
            remaining_rede,
            opera_row.amount,
            lambda row: row.amount,
            lambda row: _cards_compatible(opera_row, row),
        )
        if not matches:
            continue
        remaining_opera.remove(opera_row)
        for match in matches:
            remaining_rede.remove(match)
        items.append(_card_item(matches, (opera_row,)))

    items.extend(_card_item((row,), ()) for row in remaining_rede)
    items.extend(_card_item((), (row,)) for row in remaining_opera)
    return items


def _cards_compatible(opera: OperaPayment, rede: RedePayment) -> bool:
    return (
        not opera.card_last_four
        or not rede.card_last_four
        or opera.card_last_four == rede.card_last_four
    )


def _amount_subset[T](
    rows: list[T],
    target: Decimal,
    amount: Callable[[T], Decimal],
    compatible: Callable[[T], bool],
) -> tuple[T, ...]:
    candidates = [
        row
        for row in rows
        if compatible(row) and Decimal("0") < amount(row) <= target + TOLERANCE
    ]
    for size in range(2, min(4, len(candidates)) + 1):
        for selected in combinations(candidates, size):
            if abs(sum((amount(row) for row in selected), Decimal("0")) - target) <= TOLERANCE:
                return selected
    return ()


def _card_item(
    rede_rows: tuple[RedePayment, ...], opera_rows: tuple[OperaPayment, ...]
) -> ReconciliationItem:
    expected = sum((row.amount for row in rede_rows), Decimal("0"))
    opera_amount = sum((row.amount for row in opera_rows), Decimal("0"))
    key_parts = [*(row.nsu for row in rede_rows), *(row.transaction_id for row in opera_rows)]
    return _item(
        category="CARTÃO",
        comparison="Rede x OPERA",
        key=" / ".join(filter(None, key_parts)) or "não informado",
        external_ids=tuple(row.nsu for row in rede_rows),
        opera_ids=tuple(row.transaction_id for row in opera_rows),
        expected=expected,
        opera_amount=opera_amount,
        observation=(
            "Correspondência por soma de lançamentos."
            if len(rede_rows) > 1 or len(opera_rows) > 1
            else ""
        ),
    )


def _reconcile_cmflex(
    opera: list[OperaPayment], cmflex: list[CmflexPayment], category: str
) -> list[ReconciliationItem]:
    opera_rows = [payment for payment in opera if classify_opera(payment) == category]
    opera_transaction_ids = {payment.transaction_id for payment in opera_rows}
    cmflex_rows = [
        payment
        for payment in cmflex
        if classify_cmflex(payment) == category
        or (
            category == "PIX"
            and classify_cmflex(payment) == "ESTORNO"
            and payment.document_number in opera_transaction_ids
        )
    ]
    opera_by_key = _group_by(
        opera_rows,
        lambda payment: (
            payment.transaction_id
            if category in {"DINHEIRO", "PIX"}
            else f"{payment.folio_number}011"
        ),
    )
    cmflex_by_key = _group_by(cmflex_rows, lambda payment: payment.document_number)
    items = []
    for key in sorted(opera_by_key.keys() | cmflex_by_key.keys()):
        source_rows = cmflex_by_key.get(key, ())
        target_rows = opera_by_key.get(key, ())
        items.append(
            _item(
                category=category,
                comparison="CMFlex x OPERA",
                key=key or "não informado",
                external_ids=tuple(row.document_number for row in source_rows),
                opera_ids=tuple(row.transaction_id for row in target_rows),
                expected=sum((row.amount for row in source_rows), start=Decimal("0")),
                opera_amount=sum(
                    (row.amount for row in target_rows), start=Decimal("0")
                ),
            )
        )
    return items


def _reconcile_deposits(
    opera: list[OperaPayment], cmflex: list[CmflexPayment]
) -> list[ReconciliationItem]:
    opera_pix_ids = {
        payment.transaction_id for payment in opera if classify_opera(payment) == "PIX"
    }
    opera_rows = [payment for payment in opera if classify_opera(payment) == "DEPÓSITO"]
    cmflex_rows = [
        payment
        for payment in cmflex
        if classify_cmflex(payment) == "DEPÓSITO"
        or (
            classify_cmflex(payment) == "ESTORNO"
            and payment.document_number not in opera_pix_ids
        )
    ]
    if not opera_rows and not cmflex_rows:
        return []
    return [
        _item(
            category="DEPÓSITO",
            comparison="CMFlex x OPERA",
            key="TOTAL DO DIA",
            external_ids=tuple(row.document_number for row in cmflex_rows),
            opera_ids=tuple(row.transaction_id for row in opera_rows),
            expected=sum((row.amount for row in cmflex_rows), start=Decimal("0")),
            opera_amount=sum((row.amount for row in opera_rows), start=Decimal("0")),
            observation="Depósitos são comparados pelo total diário.",
        )
    ]


def _item(
    *,
    category: str,
    comparison: str,
    key: str,
    external_ids: tuple[str, ...],
    opera_ids: tuple[str, ...],
    expected: Decimal,
    opera_amount: Decimal,
    observation: str = "",
) -> ReconciliationItem:
    status = "OK" if abs(expected - opera_amount) <= TOLERANCE else "DIVERGENTE"
    return ReconciliationItem(
        category=category,
        comparison=comparison,
        key=key,
        external_ids=external_ids,
        opera_ids=opera_ids,
        expected_amount=expected,
        opera_amount=opera_amount,
        status=status,
        observation=observation,
    )


def _group_by[T](rows: Iterable[T], key: Callable[[T], str]) -> dict[str, list[T]]:
    grouped: dict[str, list[T]] = defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    return grouped
