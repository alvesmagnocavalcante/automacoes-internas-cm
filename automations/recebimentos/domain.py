"""Regras de conciliação independentes de arquivos e automação de navegador."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from decimal import Decimal

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
    opera_by_card = _group_by(
        [payment for payment in opera if classify_opera(payment) == "CARTÃO"],
        lambda payment: payment.card_last_four,
    )
    rede_by_card = _group_by(
        [payment for payment in rede if _is_rede_card(payment)],
        lambda payment: payment.card_last_four,
    )
    items = []
    for card in sorted(opera_by_card.keys() | rede_by_card.keys()):
        opera_rows = list(opera_by_card.get(card, ()))
        rede_rows = list(rede_by_card.get(card, ()))
        remaining_opera = list(opera_rows)
        remaining_rede = []
        for rede_row in rede_rows:
            match = next(
                (
                    opera_row
                    for opera_row in remaining_opera
                    if abs(opera_row.amount - rede_row.amount) <= TOLERANCE
                ),
                None,
            )
            if match is None:
                remaining_rede.append(rede_row)
                continue
            remaining_opera.remove(match)
            items.append(
                _item(
                    category="CARTÃO",
                    comparison="Rede x OPERA",
                    key=f"cartão final {card or 'não informado'}",
                    external_ids=(rede_row.nsu,),
                    opera_ids=(match.transaction_id,),
                    expected=rede_row.amount,
                    opera_amount=match.amount,
                )
            )
        if remaining_opera or remaining_rede:
            items.append(
                _item(
                    category="CARTÃO",
                    comparison="Rede x OPERA",
                    key=f"cartão final {card or 'não informado'}",
                    external_ids=tuple(row.nsu for row in remaining_rede),
                    opera_ids=tuple(row.transaction_id for row in remaining_opera),
                    expected=sum(
                        (row.amount for row in remaining_rede), start=Decimal("0")
                    ),
                    opera_amount=sum(
                        (row.amount for row in remaining_opera), start=Decimal("0")
                    ),
                    observation="Lançamentos remanescentes agrupados pelo cartão.",
                )
            )
    return items


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
            if category == "PIX"
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
