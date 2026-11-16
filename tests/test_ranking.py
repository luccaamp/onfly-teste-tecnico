"""Testes novos: ranking de hotéis em top_hotels (RN-08)."""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from onfly_report.repositories.csv_rate_repository import CsvRateRepository
from onfly_report.repositories.csv_reservation_repository import CsvReservationRepository
from onfly_report.services.report_builder import ReportBuilder

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


def build_top_hotels(tmp_path: Path, hotels: list[tuple[str, str]], top: int) -> list[tuple[str, str]]:
    """Gera um CSV com uma reserva CONFIRMED em BRL por (hotel_id, amount) e devolve o ranking."""
    input_path = tmp_path / "reservas.csv"
    rates_path = tmp_path / "rates.csv"
    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for index, (hotel_id, amount) in enumerate(hotels, start=1):
            writer.writerow(
                {
                    "reservation_id": f"R-{index}",
                    "traveler_name": "Pessoa Teste",
                    "company_id": "EMP-001",
                    "hotel_id": hotel_id,
                    "hotel_name": f"Hotel {hotel_id}",
                    "city": "Sao Paulo",
                    "country": "BR",
                    "checkin_date": "2025-01-10",
                    "checkout_date": "2025-01-11",
                    "rooms": "1",
                    "status": "CONFIRMED",
                    "currency": "BRL",
                    "amount": amount,
                    "payment_method": "CORPORATE_CARD",
                    "booked_at": "2025-01-01T10:00:00-03:00",
                }
            )
    rates_path.write_text("currency,rate_to_brl\nBRL,1.000000\n", encoding="utf-8")

    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(input_path),
        rate_repository=CsvRateRepository(rates_path),
        top_n=top,
        now=datetime(2025, 7, 1, 10, 0, tzinfo=timezone(timedelta(hours=-3))),
    ).build()
    return [(hotel["hotel_id"], hotel["total_brl"]) for hotel in report["top_hotels"]]


def test_top_hotels_sorted_by_total_descending(tmp_path: Path) -> None:
    """RN-08: top_hotels ordenado por total_brl decrescente, limitado a --top itens."""
    ranking = build_top_hotels(
        tmp_path,
        [("H03", "300.00"), ("H01", "100.00"), ("H04", "400.00"), ("H02", "200.00")],
        top=3,
    )

    assert ranking == [("H04", "400.00"), ("H03", "300.00"), ("H02", "200.00")]


def test_top_hotels_tie_broken_by_hotel_id_ascending(tmp_path: Path) -> None:
    """RN-08: empate em total_brl é desempatado por hotel_id crescente."""
    ranking = build_top_hotels(
        tmp_path,
        [("H09", "500.00"), ("H02", "500.00"), ("H05", "500.00"), ("H01", "900.00")],
        top=5,
    )

    assert ranking == [("H01", "900.00"), ("H02", "500.00"), ("H05", "500.00"), ("H09", "500.00")]
