# Entrega: consolidador de reservas de hotel

O CLI agora gera o relatório conforme o contrato do `README.md`. Os 5 testes fornecidos passam sem alteração e
a suíte tem 43 testes ao todo.

## Defeitos corrigidos

Um commit `fix` por defeito, cada um com o teste que o prova.

| # | Regra | Arquivo | Causa raiz |
|-|-|-|-|
| 1 | Só `CONFIRMED` é faturável | `services/status_policy.py` | A regra excluía só `CANCELLED`, então `NO_SHOW` entrava em noites e valores. |
| 2 | Noites na virada de mês/ano | `services/stay_calculator.py` | Subtraía o dia do mês (`checkout.day - checkin.day`) em vez das datas. |
| 3 | `amount * rate_to_brl` | `services/currency_converter.py` | Dividia o valor pela taxa em vez de multiplicar. |
| 4 | Dinheiro em `Decimal` | `services/currency_converter.py` | Convertia para `float` antes da conta; em 19 reservas reais o valor ficava inexato (ex.: 459,345 virava 459,34). |
| 5 | Ranking decrescente, empate por `hotel_id` | `services/report_builder.py` | Ordenava por valor crescente; a chave virou `(-total, hotel_id)` para manter o desempate ascendente. |
| 6 | `total_reservations` = todas as linhas | `repositories/csv_reservation_repository.py` | Um `break` parava a leitura em 200 linhas; o arquivo real tem 300. |

Os defeitos 4 e 6 não eram pegos pelos testes fornecidos.

## Como investiguei

1. **Diagnóstico antes de mexer.** Rodei a suíte, li todo o `src/` e perfilei os CSVs (status, moedas, BOM,
   espaços, virada de ano, quantidade de linhas) para separar defeito do CLI de problema nos dados.
2. **Oráculo independente.** Escrevi um script à parte que aplica as regras do README direto sobre o CSV, sem
   importar o `src/`. Ele bate exatamente com a tabela da amostra do README e serviu de referência para o
   arquivo real. Foi assim que apareceram o corte em 200 linhas e o erro de centavo do `float`.
3. **TDD, um commit por defeito.** Para cada defeito: teste novo falhando, correção mínima, suíte inteira,
   `ruff` nos arquivos alterados, conferência dos checksums dos arquivos protegidos e commit.
4. **Testes de contrato.** Depois das correções, testes em processo (`main(argv)`) para a amostra completa do
   README, média `"0.00"` sem noites, formato do dinheiro, `report_version`, offset `-03:00` e exit codes
   0, 1 e 2. Eles passam no código corrigido; no código original, os de amostra, média e dinheiro falham.

## Como validar

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest -q
pytest -q --cov=src --cov-report=term-missing
ruff check src tests
ruff format --check src
sha256sum -c .github/protected-files.sha256

PYTHONPATH=src python -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json
PYTHONPATH=src python -m onfly_report --input data/reservas_hoteis.csv --rates data/taxas_cambio.csv --output output/report.json
```

Resultado esperado no arquivo real: 300 reservas, 235 confirmadas, 1347 noites, `396170.00` BRL e média
`294.11`.

## Resultado

```
$ pytest -q
...........................................                              [100%]
43 passed in 0.85s
```

```
$ pytest -q --cov=src --cov-report=term-missing
Name                                                          Stmts   Miss  Cover   Missing
-------------------------------------------------------------------------------------------
src/onfly_report/__init__.py                                      1      0   100%
src/onfly_report/__main__.py                                      2      0   100%
src/onfly_report/cli.py                                          44      4    91%   59-61, 76
src/onfly_report/exceptions.py                                    2      0   100%
src/onfly_report/logging_config.py                                5      0   100%
src/onfly_report/models.py                                       25      0   100%
src/onfly_report/repositories/__init__.py                         0      0   100%
src/onfly_report/repositories/csv_rate_repository.py             36      8    78%   27, 33, 36-37, 39, 43-44, 47
src/onfly_report/repositories/csv_reservation_repository.py      24      1    96%   51
src/onfly_report/services/__init__.py                             0      0   100%
src/onfly_report/services/currency_converter.py                   5      0   100%
src/onfly_report/services/report_builder.py                      50      0   100%
src/onfly_report/services/row_parser.py                          12      0   100%
src/onfly_report/services/status_policy.py                        3      0   100%
src/onfly_report/services/stay_calculator.py                      4      0   100%
-------------------------------------------------------------------------------------------
TOTAL                                                           213     13    94%
```

As linhas não cobertas são caminhos de erro raros (falha ao gravar o JSON, erros de formato da tabela de
câmbio) e o `if __name__` do `cli.py`.

**Versões do Python:** validado em 3.13.3 (ambiente de desenvolvimento) e em 3.11.17 (venv limpo, `pytest -q`
com 43 testes passando e CLI na amostra e no arquivo real com exit 0).

## Melhorias futuras

Fora do escopo porque os dados fornecidos são consistentes, mas valem para entradas reais:

- Moeda sem taxa gera `KeyError` e termina com exit 1; deveria ser `InputFileError` com exit 2.
- A moeda da reserva não é normalizada para maiúsculas, ao contrário da tabela de câmbio; `usd` cairia no item
  anterior.
- Status desconhecido entra em `total_reservations` sem entrar em nenhuma contagem por status e sem aviso no log.
- Adicionar `mypy --strict` e testes para os caminhos de erro da tabela de câmbio.
