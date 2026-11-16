"""Testes novos: leitura completa do CSV de reservas (RN-04)."""

from pathlib import Path

from onfly_report.repositories.csv_reservation_repository import REQUIRED_COLUMNS, CsvReservationRepository


def test_reads_every_row_of_the_file(tmp_path: Path) -> None:
    """RN-04: total_reservations = todas as linhas do arquivo; nada é descartado (ex.: 250 > 200)."""
    total_rows = 250
    input_path = tmp_path / "reservas.csv"
    lines = [",".join(REQUIRED_COLUMNS)]
    lines += [
        f"R-{index},Pessoa,EMP-001,H01,Hotel,Cidade,BR,2025-01-10,2025-01-11,1,CONFIRMED,BRL,100.00,PIX,"
        "2025-01-01T10:00:00-03:00"
        for index in range(1, total_rows + 1)
    ]
    input_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rows = CsvReservationRepository(input_path).read()

    assert len(rows) == total_rows
    assert rows[-1].values["reservation_id"] == f"R-{total_rows}"
