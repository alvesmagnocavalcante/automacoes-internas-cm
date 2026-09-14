"""Modelos da conferência diária de recebimentos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OperaPayment:
    transaction_id: str
    folio_number: str
    transaction_code: str
    description: str
    card_last_four: str
    amount: Decimal


@dataclass(frozen=True)
class RedePayment:
    row_number: int
    status: str
    modality: str
    brand: str
    card_last_four: str
    nsu: str
    amount: Decimal


@dataclass(frozen=True)
class CmflexPayment:
    row_number: int
    document_number: str
    customer: str
    carrier: str
    document_type: str
    amount: Decimal


@dataclass(frozen=True)
class ReconciliationItem:
    category: str
    comparison: str
    key: str
    external_ids: tuple[str, ...]
    opera_ids: tuple[str, ...]
    expected_amount: Decimal
    opera_amount: Decimal
    status: str
    observation: str = ""

    @property
    def difference(self) -> Decimal:
        return self.expected_amount - self.opera_amount

    def as_dict(self) -> dict[str, object]:
        return {
            "categoria": self.category,
            "conferencia": self.comparison,
            "chave": self.key,
            "ids_origem": list(self.external_ids),
            "ids_opera": list(self.opera_ids),
            "valor_esperado": f"{self.expected_amount:.2f}",
            "valor_opera": f"{self.opera_amount:.2f}",
            "diferenca": f"{self.difference:.2f}",
            "status": self.status,
            "observacao": self.observation,
        }


@dataclass(frozen=True)
class ReconciliationResult:
    items: tuple[ReconciliationItem, ...]
    ignored_opera_count: int
    ignored_cmflex_count: int
    ignored_rede_count: int

    @property
    def matched_count(self) -> int:
        return sum(item.status == "OK" for item in self.items)

    @property
    def divergent_count(self) -> int:
        return sum(item.status == "DIVERGENTE" for item in self.items)

    def as_dict(self) -> dict[str, object]:
        totals = {}
        for category in sorted({item.category for item in self.items}):
            category_items = [item for item in self.items if item.category == category]
            expected = sum(
                (item.expected_amount for item in category_items), start=Decimal("0")
            )
            opera = sum(
                (item.opera_amount for item in category_items), start=Decimal("0")
            )
            totals[category] = {
                "valor_esperado": f"{expected:.2f}",
                "valor_opera": f"{opera:.2f}",
                "diferenca": f"{expected - opera:.2f}",
            }
        return {
            "resumo": {
                "conferencias": len(self.items),
                "ok": self.matched_count,
                "divergentes": self.divergent_count,
                "ignorados_opera": self.ignored_opera_count,
                "ignorados_cmflex": self.ignored_cmflex_count,
                "ignorados_rede": self.ignored_rede_count,
            },
            "totais_por_categoria": totals,
            "itens": [item.as_dict() for item in self.items],
        }
