# CLAUDE.md — Regras do projeto para assistentes de IA

> Este arquivo é lido automaticamente pelo Claude Code. Ele define **como** a IA deve trabalhar
> neste repositório. Regras daqui têm prioridade sobre qualquer sugestão da própria IA.
> Contexto completo: `docs/PLANO-TECNICO.md` · Commits: `docs/CONVENCAO-COMMITS.md`.

## 1. Missão

Corrigir os defeitos do CLI `onfly_report` (consolidador de reservas de hotel da ONFLY) para que o
relatório JSON siga **exatamente** o contrato do `README.md`, provando cada correção com um teste.

Este é um teste técnico de **depuração**. Não é para construir features, refatorar a arquitetura,
adicionar API/banco/frontend ou fazer deploy.

A fonte da verdade é o `README.md` da ONFLY. Em caso de dúvida sobre regra de negócio, **cite o
trecho do README**. Se o README não responder, **pare e pergunte ao humano**: não invente regra.

## 2. Regras invioláveis

1. **NUNCA edite, formate, renomeie ou apague** estes arquivos (também bloqueados em
   `.claude/settings.json` e verificados por checksum no CI em `.github/protected-files.sha256`):
   - `tests/helpers.py`, `tests/test_currency.py`, `tests/test_nights.py`,
     `tests/test_regression_report.py`, `tests/test_status_rules.py`, `tests/test_top_hotels.py`
   - `data/reservas_hoteis.csv`, `data/taxas_cambio.csv`, `data/exemplo-validacao.csv`
   - Não tente contornar o bloqueio pelo terminal (`sed -i`, `>`, `tee`, `git checkout`, `cp` etc.).
2. **NUNCA altere** o comando do CLI, seus argumentos, nem nomes/tipos/semântica dos campos do JSON.
3. **Sem dependências de runtime.** O CLI usa só a biblioteca padrão. Ferramentas vão em
   `requirements-dev.txt`.
4. **Dinheiro sempre em `Decimal`**, nunca `float`. Arredondar só na serialização (2 casas, half-up).
5. **Não rode `ruff format` / `ruff check --fix` em `tests/` inteiro.** Apenas em `src/` e nos
   arquivos de teste novos, nomeando-os explicitamente.
6. **Git:** nunca `push --force`, `reset --hard`, `rebase` em branch publicada, nem `--amend` após push.
   Nunca faça push sem o humano pedir. Nunca commite em `main` diretamente.
7. **Não declare algo como feito sem evidência executada** (saída de teste, comando, diff).

## 3. Fluxo obrigatório para cada defeito (TDD)

```
1. Identificar a regra (RN-xx) no README e o módulo responsável.
2. Escrever/indicar um teste que FALHA no código atual. Rodar e mostrar a falha.
3. Aplicar a correção MÍNIMA (sem refatorar o entorno).
4. Rodar o teste novo + a suíte inteira. Mostrar que passa.
5. Rodar lint/tipos nos arquivos tocados.
6. Propor a mensagem de commit seguindo docs/CONVENCAO-COMMITS.md e aguardar o OK do humano.
```

Um defeito por vez, um commit por defeito. Se encontrar outro problema no caminho, **anote e
avise**, mas não corrija junto.

## 4. Regras de negócio (resumo; detalhes em `docs/PLANO-TECNICO.md` §3)

| ID | Regra |
|-|-|
| RN-01 | Só `CONFIRMED` é faturável; `CANCELLED`/`NO_SHOW` só entram nas contagens |
| RN-02 | `room_nights = (checkout − checkin).days × rooms`, válido na virada de mês/ano |
| RN-03 | `amount_brl = amount × rate_to_brl` |
| RN-04 | `total_reservations` = todas as linhas do arquivo |
| RN-05 | `Decimal` sempre; soma exata; arredonda só ao serializar (2 casas, half-up) |
| RN-06 | média = total ÷ noites; sem noites → `"0.00"` |
| RN-07 | `by_month` pelo mês do check-in, crescente, só `CONFIRMED` |
| RN-08 | `top_hotels`: `total_brl` decrescente, empate por `hotel_id` crescente, `--top` itens |
| RN-09 | Dinheiro como string com exatamente 2 casas, sem separador de milhar |
| RN-10 | `report_version = "1.0"`; `generated_at` com offset `-03:00` |
| RN-11 | Exit codes: `0` sucesso, `2` entrada/argumento inválido, `1` erro inesperado |
| RN-12 | `--top` inteiro ≥ 1 (padrão 5); `--output` padrão `output/report.json` |
| RN-13 | Ordem: ler → converter tipos → contar status → filtrar CONFIRMED → agregar |

## 5. Arquitetura (manter)

```
src/onfly_report/
├── cli.py                  # argparse, exit codes, escrita do JSON, resumo no stdout
├── models.py               # dataclasses imutáveis (RawRow, Reservation)
├── exceptions.py           # DomainError → InputFileError (exit 2)
├── logging_config.py       # logs sempre em stderr
├── repositories/           # I/O de CSV, sem regra de negócio
└── services/               # regras puras: status, noites, câmbio, parser, ReportBuilder
```

- Regra de negócio fica em `services/`. I/O fica em `repositories/`. Não misture.
- `stdout` é só para o resumo final; logs vão para `stderr`.
- Erros de entrada levantam `InputFileError` (exit 2), nunca exceção genérica.

## 6. Testes

- Testes novos ficam na **raiz de `tests/`**, em arquivos novos `test_*.py`.
- Prefira testes **em processo** (chamando `main(argv)` ou os serviços). Os fornecidos usam
  subprocesso, que é invisível ao mutmut.
- Cada teste novo tem docstring citando o RN que protege.
- Tipos de teste em uso: exemplo, propriedades (Hypothesis), oráculo diferencial, contrato do CLI.
- Testes gerados por ferramenta só **depois** da correção, e revisados um a um. Eles congelam o
  comportamento atual, inclusive bugs.

## 7. Comandos

```bash
# Ambiente (Python 3.11)
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Executar o CLI
PYTHONPATH=src python -m onfly_report --input data/reservas_hoteis.csv --rates data/taxas_cambio.csv --output output/report.json
PYTHONPATH=src python -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json

# Qualidade
pytest -q                                   # suíte completa
pytest -q --cov                             # cobertura (inclui subprocesso)
ruff check src tests                        # lint
ruff format --check src                     # formatação (só src/)
mypy                                        # tipos (--strict via pyproject)
semgrep scan --config .semgrep/ --error --metrics=off src/
mutmut run && mutmut results                # mutation testing (lento; sob demanda)
sha256sum -c .github/protected-files.sha256 # arquivos protegidos intactos
```

Antes de propor qualquer commit: `pytest -q`, `ruff check src tests` e
`sha256sum -c .github/protected-files.sha256` precisam passar.

## 8. Commits e branches

Siga `docs/CONVENCAO-COMMITS.md`. Resumo:

- `tipo(escopo): descrição no imperativo, minúscula, sem ponto final (RN-xx)`
- Um defeito por commit, com teste e correção juntos; o corpo explica **o porquê**.
- Commits com código escrito pela IA levam o trailer `Co-Authored-By`.
- Trabalho em branch (`fix/...`, `test/...`, `chore/...`), entra na `main` só por PR com CI verde.

## 9. Como se comunicar com o humano

- Seja direto. Mostre **evidência** (saída de comando), não promessa.
- Ao propor uma correção, diga: regra violada, linha exata, causa raiz em uma frase, teste que prova.
- Se discordar de um pedido por conflitar com este arquivo ou com o README, diga claramente e por quê.
- Ao fim de cada tarefa: o que mudou, o que foi validado e o que fica pendente.
- O humano é o responsável pelas decisões e pelo commit final. A IA propõe, executa e verifica.
