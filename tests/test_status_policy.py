"""Testes novos: política de status faturável (RN-01)."""

import pytest

from onfly_report.services.status_policy import is_billable


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("CONFIRMED", True),
        ("CANCELLED", False),
        ("NO_SHOW", False),
    ],
)
def test_only_confirmed_is_billable(status: str, expected: bool) -> None:
    """RN-01: só CONFIRMED é faturável; CANCELLED e NO_SHOW ficam fora de valores e noites."""
    assert is_billable(status) is expected
