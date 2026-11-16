"""Testes novos: cálculo de noites de quarto (RN-02)."""

from datetime import date

import pytest

from onfly_report.services.stay_calculator import calculate_room_nights


@pytest.mark.parametrize(
    ("checkin", "checkout", "rooms", "expected"),
    [
        (date(2025, 1, 10), date(2025, 1, 13), 1, 3),  # exemplo do README
        (date(2025, 1, 30), date(2025, 2, 2), 1, 3),  # virada de mês
        (date(2024, 12, 30), date(2025, 1, 2), 1, 3),  # virada de ano
        (date(2024, 2, 28), date(2024, 3, 1), 1, 2),  # fevereiro bissexto
        (date(2025, 1, 28), date(2025, 2, 2), 2, 10),  # virada de mês com 2 quartos
    ],
)
def test_room_nights_use_date_difference(checkin: date, checkout: date, rooms: int, expected: int) -> None:
    """RN-02: room_nights = (checkout - checkin).days * rooms, inclusive na virada de mês/ano."""
    assert calculate_room_nights(checkin, checkout, rooms) == expected
