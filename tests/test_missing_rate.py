"""Testes novos: moeda da reserva sem taxa na tabela de câmbio é entrada inválida (RN-11)."""

from decimal import Decimal
from pathlib import Path

import pytest

from onfly_report.cli import main
from onfly_report.exceptions import InputFileError
from onfly_report.services.currency_converter import convert_to_brl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_INPUT = PROJECT_ROOT / "data" / "exemplo-validacao.csv"


def test_convert_without_rate_raises_input_error() -> None:
    """RN-11: moeda sem taxa vira InputFileError com a moeda na mensagem, não KeyError."""
    with pytest.raises(InputFileError, match="GBP"):
        convert_to_brl(Decimal("10.00"), "GBP", {"BRL": Decimal("1.000000")})


def test_cli_exits_two_when_rate_is_missing(tmp_path: Path) -> None:
    """RN-11: tabela de câmbio sem uma moeda usada nas reservas termina com exit 2, sem gravar relatório."""
    rates_path = tmp_path / "taxas.csv"
    rates_path.write_text("currency,rate_to_brl\nBRL,1.000000\n", encoding="utf-8")
    output_path = tmp_path / "report.json"

    exit_code = main(["--input", str(SAMPLE_INPUT), "--rates", str(rates_path), "--output", str(output_path)])

    assert exit_code == 2
    assert not output_path.exists()
