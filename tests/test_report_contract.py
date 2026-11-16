"""Testes novos: relatório completo e formato do contrato JSON (RN-06, RN-07, RN-08, RN-09, RN-10)."""

import csv
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from onfly_report.cli import main
from onfly_report.services.report_builder import format_money

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_INPUT = PROJECT_ROOT / "data" / "exemplo-validacao.csv"
RATES = PROJECT_ROOT / "data" / "taxas_cambio.csv"

COLUMNS = [
    "reservation_id",
    "traveler_name",
    "company_id",
    "hotel_id",
    "hotel_name",
    "city",
    "country",
    "checkin_date",
    "checkout_date",
    "rooms",
    "status",
    "currency",
    "amount",
    "payment_method",
    "booked_at",
]

BASE_ROW = {
    "reservation_id": "R-1",
    "traveler_name": "Pessoa Teste",
    "company_id": "EMP-001",
    "hotel_id": "H01",
    "hotel_name": "Hotel Teste",
    "city": "Sao Paulo",
    "country": "BR",
    "checkin_date": "2025-01-10",
    "checkout_date": "2025-01-11",
    "rooms": "1",
    "status": "CONFIRMED",
    "currency": "BRL",
    "amount": "100.00",
    "payment_method": "CORPORATE_CARD",
    "booked_at": "2025-01-01T10:00:00-03:00",
}

# Valores copiados da seção "Amostra de validação" do README.
EXPECTED_SAMPLE_REPORT = {
    "report_version": "1.0",
    "summary": {
        "total_reservations": 12,
        "confirmed_reservations": 9,
        "cancelled_reservations": 2,
        "no_show_reservations": 1,
        "total_room_nights": 28,
        "total_amount_brl": "7566.00",
        "average_nightly_rate_brl": "270.21",
    },
    "by_month": [
        {"month": "2025-01", "reservations": 8, "room_nights": 25, "total_brl": "6684.00"},
        {"month": "2025-02", "reservations": 1, "room_nights": 3, "total_brl": "882.00"},
    ],
    "top_hotels": [
        {"hotel_id": "H01", "hotel_name": "Hotel Aurora Paulista", "room_nights": 3, "total_brl": "1200.00"},
        {"hotel_id": "H02", "hotel_name": "Hotel Mirante", "room_nights": 2, "total_brl": "1084.00"},
        {"hotel_id": "H12", "hotel_name": "Hotel Miami Beach", "room_nights": 1, "total_brl": "1000.00"},
        {"hotel_id": "H10", "hotel_name": "Hotel Madrid, Gran Vía", "room_nights": 4, "total_brl": "900.00"},
        {"hotel_id": "H09", "hotel_name": "Hotel Lisboa, Centro", "room_nights": 3, "total_brl": "882.00"},
    ],
}

MONEY_RE = re.compile(r"^-?\d+\.\d{2}$")


def run_main(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Executa o CLI em processo e devolve o JSON gravado."""
    exit_code = main(["--input", str(input_path), "--rates", str(RATES), "--output", str(output_path)])
    assert exit_code == 0
    report: dict[str, Any] = json.loads(output_path.read_text(encoding="utf-8"))
    return report


def write_reservations(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({**BASE_ROW, **row} for row in rows)
    return path


def test_sample_report_matches_readme_table(tmp_path: Path) -> None:
    """RN-07, RN-08, RN-09: a amostra do README gera exatamente o relatório da tabela (exceto generated_at)."""
    report = run_main(SAMPLE_INPUT, tmp_path / "exemplo.json")

    generated_at = report.pop("generated_at")

    assert isinstance(generated_at, str)
    assert report == EXPECTED_SAMPLE_REPORT
    assert list(report) == ["report_version", "summary", "by_month", "top_hotels"]


def test_average_is_zero_when_there_are_no_room_nights(tmp_path: Path) -> None:
    """RN-06: sem noites CONFIRMED, total e média saem "0.00" e listas ficam vazias."""
    input_path = write_reservations(
        tmp_path / "reservas.csv",
        [
            {"reservation_id": "R-1", "status": "CANCELLED", "amount": "500.00"},
            {"reservation_id": "R-2", "status": "NO_SHOW", "amount": "300.00"},
        ],
    )

    report = run_main(input_path, tmp_path / "report.json")

    assert report["summary"]["total_reservations"] == 2
    assert report["summary"]["total_room_nights"] == 0
    assert report["summary"]["total_amount_brl"] == "0.00"
    assert report["summary"]["average_nightly_rate_brl"] == "0.00"
    assert report["by_month"] == []
    assert report["top_hotels"] == []


def test_money_fields_are_strings_with_two_decimals(tmp_path: Path) -> None:
    """RN-09: todo campo de dinheiro é string com exatamente 2 casas e sem separador de milhar."""
    input_path = write_reservations(
        tmp_path / "reservas.csv",
        [
            {"reservation_id": "R-1", "amount": "1234567.5"},
            {"reservation_id": "R-2", "hotel_id": "H02", "amount": "10", "checkout_date": "2025-01-13"},
        ],
    )

    report = run_main(input_path, tmp_path / "report.json")

    money_values = [
        report["summary"]["total_amount_brl"],
        report["summary"]["average_nightly_rate_brl"],
        *(month["total_brl"] for month in report["by_month"]),
        *(hotel["total_brl"] for hotel in report["top_hotels"]),
    ]
    assert all(isinstance(value, str) and MONEY_RE.match(value) for value in money_values), money_values
    assert report["summary"]["total_amount_brl"] == "1234577.50"
    assert report["top_hotels"][1]["total_brl"] == "10.00"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0"), "0.00"),
        (Decimal("10"), "10.00"),
        (Decimal("1234.5"), "1234.50"),
        (Decimal("0.005"), "0.01"),  # half-up, não half-even
        (Decimal("2.675"), "2.68"),
        (Decimal("459.345"), "459.35"),
        (Decimal("1234567.891"), "1234567.89"),
    ],
)
def test_format_money_two_places_half_up(value: Decimal, expected: str) -> None:
    """RN-05, RN-09: serialização com 2 casas, arredondamento half-up, sem separador de milhar."""
    assert format_money(value) == expected


def test_report_version_and_generated_at_offset(tmp_path: Path) -> None:
    """RN-10: report_version é "1.0" e generated_at é ISO 8601 com offset fixo -03:00."""
    report = run_main(SAMPLE_INPUT, tmp_path / "exemplo.json")

    assert report["report_version"] == "1.0"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-03:00", report["generated_at"])
    assert datetime.fromisoformat(report["generated_at"]).utcoffset() == timedelta(hours=-3)
