"""Testes novos: conversão de moeda para BRL (RN-03, RN-05)."""

from decimal import Decimal

import pytest

from onfly_report.services.currency_converter import convert_to_brl
from onfly_report.services.report_builder import format_money

RATES = {"BRL": Decimal("1.000000"), "USD": Decimal("5.420000"), "EUR": Decimal("5.880000")}


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        (Decimal("100.00"), "BRL", Decimal("100.00")),
        (Decimal("100.00"), "USD", Decimal("542.00")),
        (Decimal("150.00"), "EUR", Decimal("882.00")),  # EX-09 da amostra do README
    ],
)
def test_conversion_multiplies_amount_by_rate(amount: Decimal, currency: str, expected: Decimal) -> None:
    """RN-03: amount_brl = amount * rate_to_brl (multiplica, não divide)."""
    assert convert_to_brl(amount, currency, RATES) == expected


def test_conversion_is_exact_decimal_without_float() -> None:
    """RN-05: conversão em Decimal exato; float muda o centavo no half-up.

    Caso real RSV-0111: US$ 84,75 x 5,42 = 459,345 -> "459.35". Via float o produto vira
    459,34499999999997 e arredonda para "459.34".
    """
    amount_brl = convert_to_brl(Decimal("84.75"), "USD", RATES)

    assert amount_brl == Decimal("459.345")
    assert format_money(amount_brl) == "459.35"
