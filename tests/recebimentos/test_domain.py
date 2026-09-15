from decimal import Decimal
from unittest import TestCase

from automations.recebimentos.domain import reconcile
from automations.recebimentos.models import CmflexPayment, OperaPayment, RedePayment


def opera(
    transaction_id: str,
    amount: str,
    *,
    code: str = "9302",
    description: str = "Rede Visa Credito",
    card: str = "1234",
    folio: str = "",
) -> OperaPayment:
    return OperaPayment(transaction_id, folio, code, description, card, Decimal(amount))


def rede(nsu: str, amount: str, *, card: str = "1234") -> RedePayment:
    return RedePayment(
        row_number=3,
        status="aprovada",
        modality="crédito",
        brand="Visa",
        card_last_four=card,
        nsu=nsu,
        amount=Decimal(amount),
    )


def cmflex(
    document: str,
    amount: str,
    *,
    customer: str,
    document_type: str,
) -> CmflexPayment:
    return CmflexPayment(
        row_number=2,
        document_number=document,
        customer=customer,
        carrier="Conta corrente",
        document_type=document_type,
        amount=Decimal(amount),
    )


class ReconciliationTests(TestCase):
    def test_matches_card_transactions_individually_and_by_grouped_total(self):
        result = reconcile(
            [opera("1", "100"), opera("2", "40"), opera("3", "10")],
            [],
            [rede("a", "100"), rede("b", "50")],
        )

        self.assertEqual(result.matched_count, 2)
        self.assertEqual(result.divergent_count, 0)
        grouped = next(item for item in result.items if item.external_ids == ("b",))
        self.assertEqual(grouped.opera_ids, ("2", "3"))
        self.assertEqual(grouped.opera_amount, Decimal("50"))
        self.assertEqual(
            result.as_dict()["totais_por_categoria"]["CARTÃO"]["diferenca"],
            "0.00",
        )

    def test_matches_cards_by_value_when_opera_has_no_card_number(self):
        result = reconcile(
            [
                opera("1", "4", card=""),
                opera("2", "4", card=""),
                opera("3", "12", card=""),
            ],
            [],
            [rede("nsu", "20", card="9876")],
        )

        self.assertEqual(result.matched_count, 1)
        self.assertEqual(result.items[0].opera_ids, ("1", "2", "3"))

    def test_opera_refund_without_rede_counterpart_is_divergent(self):
        result = reconcile([opera("1", "-5.50")], [], [])

        self.assertEqual(result.divergent_count, 1)
        self.assertEqual(result.items[0].expected_amount, Decimal("0"))
        self.assertEqual(result.items[0].opera_amount, Decimal("-5.50"))
        self.assertEqual(result.items[0].difference, Decimal("5.50"))

    def test_matches_pix_and_invoice_and_flags_unmatched_deposit(self):
        opera_rows = [
            opera("pix-1", "10", code="9087", description="Pix", card=""),
            opera(
                "invoice-1",
                "20",
                code="9090",
                description="A Faturar",
                card="",
                folio="265789",
            ),
        ]
        cmflex_rows = [
            cmflex("pix-1", "10", customer="DEPOSITO", document_type="Deposito"),
            cmflex(
                "265789011",
                "20",
                customer="AGÊNCIA",
                document_type="Nota Fiscal de Serviço Eletrônica",
            ),
            cmflex(
                "deposit-1",
                "30",
                customer="DEPOSITO",
                document_type="Extrato Bancário (E)",
            ),
            cmflex(
                "pix-refund",
                "-5",
                customer="DEPOSITO",
                document_type="Estorno de Recebimentos",
            ),
        ]
        opera_rows.append(
            opera("pix-refund", "-5", code="9087", description="Pix", card="")
        )

        result = reconcile(opera_rows, cmflex_rows, [])

        self.assertEqual(result.matched_count, 3)
        self.assertEqual(result.divergent_count, 1)
        deposit = next(item for item in result.items if item.category == "DEPÓSITO")
        self.assertEqual(deposit.expected_amount, Decimal("30"))
        self.assertEqual(deposit.opera_amount, Decimal("0"))

    def test_matches_cash_by_document_number(self):
        result = reconcile(
            [opera("cash-1", "10", code="9086", description="Dinheiro", card="")],
            [
                cmflex(
                    "cash-1",
                    "10",
                    customer="DINHEIRO",
                    document_type="MOVIMENTO DE CAIXA",
                )
            ],
            [],
        )

        self.assertEqual(result.matched_count, 1)
        self.assertEqual(result.items[0].category, "DINHEIRO")

    def test_ignores_non_reconciled_categories_and_unsuccessful_rede_rows(self):
        ignored_opera = opera("other-1", "10", code="9999", description="Outro")
        ignored_cmflex = cmflex(
            "other-1", "10", customer="OUTRO", document_type="OUTRO"
        )
        ignored_rede = RedePayment(
            3, "negada", "débito", "Visa", "1234", "nsu", Decimal("10")
        )

        result = reconcile([ignored_opera], [ignored_cmflex], [ignored_rede])

        self.assertEqual(result.items, ())
        self.assertEqual(result.ignored_opera_count, 1)
        self.assertEqual(result.ignored_cmflex_count, 1)
        self.assertEqual(result.ignored_rede_count, 1)
