"""Testes novos: códigos de saída do CLI chamando main(argv) em processo (RN-11, RN-12)."""

from pathlib import Path

import pytest

from onfly_report.cli import main
from onfly_report.repositories.csv_reservation_repository import REQUIRED_COLUMNS
from onfly_report.services.report_builder import ReportBuilder

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_INPUT = PROJECT_ROOT / "data" / "exemplo-validacao.csv"
RATES = PROJECT_ROOT / "data" / "taxas_cambio.csv"

VALID_ROW = {
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


def write_csv(path: Path, columns: list[str], row: dict[str, str]) -> Path:
    path.write_text(",".join(columns) + "\n" + ",".join(row[column] for column in columns) + "\n", encoding="utf-8")
    return path


def run(input_path: Path, output_path: Path, rates_path: Path = RATES, *extra: str) -> int:
    return main(["--input", str(input_path), "--rates", str(rates_path), "--output", str(output_path), *extra])


def test_valid_input_exits_zero(tmp_path: Path) -> None:
    """RN-11: sucesso termina com exit 0 e grava o relatório."""
    output_path = tmp_path / "report.json"

    assert run(SAMPLE_INPUT, output_path) == 0
    assert output_path.exists()


@pytest.mark.parametrize("missing", ["input", "rates"])
def test_missing_file_exits_two(tmp_path: Path, missing: str) -> None:
    """RN-11: arquivo de reservas ou de câmbio inexistente é entrada inválida (exit 2), sem gravar relatório."""
    absent = tmp_path / "nao-existe.csv"
    output_path = tmp_path / "report.json"

    if missing == "input":
        exit_code = run(absent, output_path)
    else:
        exit_code = run(SAMPLE_INPUT, output_path, absent)

    assert exit_code == 2
    assert not output_path.exists()


def test_missing_required_column_exits_two(tmp_path: Path) -> None:
    """RN-11: CSV de reservas sem coluna obrigatória (amount) é entrada inválida (exit 2)."""
    columns = [column for column in REQUIRED_COLUMNS if column != "amount"]
    input_path = write_csv(tmp_path / "reservas.csv", columns, VALID_ROW)
    output_path = tmp_path / "report.json"

    assert run(input_path, output_path) == 2
    assert not output_path.exists()


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("checkin_date", "2025-13-01"),
        ("checkout_date", "02/02/2025"),
        ("rooms", "um"),
        ("amount", "R$ 100"),
    ],
)
def test_invalid_row_exits_two(tmp_path: Path, column: str, value: str) -> None:
    """RN-11: linha com data, quartos ou valor fora do formato é entrada inválida (exit 2)."""
    input_path = write_csv(tmp_path / "reservas.csv", list(REQUIRED_COLUMNS), {**VALID_ROW, column: value})
    output_path = tmp_path / "report.json"

    assert run(input_path, output_path) == 2
    assert not output_path.exists()


@pytest.mark.parametrize("top", ["0", "-1", "abc"])
def test_invalid_top_exits_two(tmp_path: Path, top: str) -> None:
    """RN-11, RN-12: --top precisa ser inteiro >= 1; senão é argumento inválido (exit 2)."""
    output_path = tmp_path / "report.json"

    with pytest.raises(SystemExit) as exc_info:
        run(SAMPLE_INPUT, output_path, RATES, "--top", top)

    assert exc_info.value.code == 2
    assert not output_path.exists()


def test_unexpected_error_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RN-11: erro inesperado (não é de entrada) termina com exit 1, sem gravar relatório."""

    def explode(self: ReportBuilder) -> dict[str, object]:
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(ReportBuilder, "build", explode)
    output_path = tmp_path / "report.json"

    assert run(SAMPLE_INPUT, output_path) == 1
    assert not output_path.exists()
