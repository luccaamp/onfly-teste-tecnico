"""Testes novos: conversão de moeda para BRL (RN-03, RN-05)."""

from decimal import Decimal

import pytest

from onfly_report.services.currency_converter import convert_to_brl

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
