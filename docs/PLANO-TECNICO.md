# Plano Técnico — Teste Técnico ONFLY 2026

> **Consolidador de reservas de hotel (`onfly_report`)**
> Contexto, regras de negócio, diagnóstico e estratégia de validação usados na entrega.
> Autor: Lucca Alvarenga · Elaborado com apoio de IA (Claude), declarado em `entrega/uso-de-ia/`.

---

## Sumário

1. [Contexto e objetivo](#1-contexto-e-objetivo)
2. [Escopo: o que pode e o que não pode](#2-escopo-o-que-pode-e-o-que-não-pode)
3. [Especificação de negócio (requisitos rastreáveis)](#3-especificação-de-negócio-requisitos-rastreáveis)
4. [Diagnóstico](#4-diagnóstico)
5. [Arquitetura e estrutura do projeto](#5-arquitetura-e-estrutura-do-projeto)
6. [Estratégia de qualidade](#6-estratégia-de-qualidade)
7. [Fluxo Git](#7-fluxo-git)
8. [Entrega (pasta `entrega/`)](#8-entrega-pasta-entrega)
9. [Riscos e mitigação](#9-riscos-e-mitigação)
10. [Definition of Done](#10-definition-of-done)

---

## 1. Contexto e objetivo

A ONFLY forneceu um CLI em Python 3.11 que lê a exportação de reservas de hotel de um cliente
(`data/reservas_hoteis.csv`), converte valores para BRL (`data/taxas_cambio.csv`) e gera um
relatório JSON consolidado. **O CLI roda, mas entrega números errados.**

É um teste de **depuração**, não de construção do zero. Não há API, banco, frontend nem deploy.

| O que é avaliado | Como foi demonstrado |
|-|-|
| O relatório segue o contrato do README | Testes de contrato + amostra de validação do README |
| Todos os defeitos foram corrigidos | Inclusive os **não cobertos** pelos testes fornecidos |
| Os testes fornecidos passam **sem alteração** | Checksums em `.github/protected-files.sha256` |
| Testes adicionais | Testes de exemplo dos serviços e testes de contrato do CLI |
| Qualidade da investigação | `entrega/README-ENTREGA.md` com causa raiz e evidências |
| Uso responsável de IA | Sessão exportada + declaração |

**Filosofia:** correções **cirúrgicas**, cada uma provada por um teste que falhava antes.

---

## 2. Escopo: o que pode e o que não pode

| Ação | Permitido? |
|-|-|
| Corrigir o código em `src/onfly_report/` | ✅ É a tarefa principal |
| Criar testes novos (`tests/test_*.py`) | ✅ |
| Adicionar ferramentas de **dev** (`requirements-dev.txt`) | ✅ |
| Alterar os testes fornecidos (`tests/test_*.py` originais e `tests/helpers.py`) | ❌ |
| Alterar os CSVs de `data/` | ❌ |
| Mudar comando/argumentos do CLI | ❌ |
| Mudar nomes, tipos ou semântica dos campos do JSON | ❌ |
| Adicionar dependência de **runtime** | ❌ (o CLI usa só a biblioteca padrão) |

> Testes novos ficam **na raiz de `tests/`**, junto dos fornecidos.

---

## 3. Especificação de negócio (requisitos rastreáveis)

Cada regra do README recebe um ID. Testes novos e commits citam o ID correspondente.

| ID | Regra (README) | Módulo responsável |
|-|-|-|
| RN-01 | Só `CONFIRMED` é faturável; `CANCELLED`/`NO_SHOW` só entram nas contagens | `status_policy.py` |
| RN-02 | `room_nights = (checkout − checkin).days × rooms`, não inclusivo, válido em virada de mês/ano | `stay_calculator.py` |
| RN-03 | `amount_brl = amount × rate_to_brl` | `currency_converter.py` |
| RN-04 | `total_reservations` = **todas** as linhas do arquivo | `csv_reservation_repository.py` |
| RN-05 | Dinheiro em `Decimal`, nunca `float`; soma exata; arredonda **só na serialização**, 2 casas, half-up | `currency_converter.py`, `report_builder.py` |
| RN-06 | `average_nightly_rate_brl = total_amount / total_nights`; sem noites → `"0.00"` | `report_builder.py` |
| RN-07 | `by_month` pelo mês do check-in, ordem crescente, só `CONFIRMED` | `report_builder.py` |
| RN-08 | `top_hotels`: `total_brl` decrescente, empate por `hotel_id` crescente, `--top` itens | `report_builder.py` |
| RN-09 | Dinheiro é string com exatamente 2 casas, sem separador de milhar | `report_builder.format_money` |
| RN-10 | `report_version = "1.0"`; `generated_at` com offset fixo `-03:00` | `report_builder.py` |
| RN-11 | Exit codes: `0` sucesso, `2` entrada/argumento inválido, `1` erro inesperado | `cli.py` |
| RN-12 | `--top` inteiro ≥ 1, padrão 5; `--output` padrão `output/report.json`; CLI cria o diretório | `cli.py` |
| RN-13 | Ordem: ler → converter tipos → contar status → filtrar CONFIRMED → agregar | `report_builder.py` |

---

## 4. Diagnóstico

### 4.1 Estado de partida

- `pytest -q` → os 5 testes fornecidos falhavam (esperado pelo README).
- Dataset real: 300 reservas, dados limpos (sem duplicatas, sem BOM, status/moedas consistentes,
  `hotel_id → hotel_name` único, todos os valores com 2 casas).

### 4.2 Mapa de defeitos

| # | Regra | Local | Defeito | Causa raiz (1 frase) | Pego pelos testes fornecidos? |
|-|-|-|-|-|-|
| D1 | RN-01 | `status_policy.is_billable` | `status != "CANCELLED"` | Regra escrita por exclusão em vez de inclusão, deixando `NO_SHOW` faturável. | ✅ `test_status_rules` |
| D2 | RN-02 | `stay_calculator.calculate_room_nights` | `checkout.day - checkin.day` | Subtrai o dia do mês em vez de subtrair datas, quebrando na virada de mês/ano. | ✅ `test_nights` |
| D3 | RN-03 | `currency_converter.convert_to_brl` | `amount / rate` | Operação invertida: divide pela taxa em vez de multiplicar. | ✅ `test_currency` |
| D4 | RN-05 | `currency_converter.convert_to_brl` | `Decimal(str(float(...)))` | Passa o dinheiro por `float` binário, introduzindo erro de representação. | ❌ **escondido** |
| D5 | RN-08 | `report_builder.build` | `sorted(key=(amount, id))` | Ordenação crescente; o ranking precisa ser decrescente por valor. | ⚠️ Parcial: `test_top_hotels` pega a ordem, mas não o desempate por `hotel_id` |
| D6 | RN-04 | `csv_reservation_repository.read` | `if len(rows) == 200: break` | Limite fixo de leitura descarta silenciosamente as linhas após a 200ª. | ❌ **escondido** |
| D7 | RN-11 | `currency_converter.convert_to_brl` | `rates[currency]` | Moeda sem taxa gera `KeyError` e termina com exit 1 em vez de exit 2 (entrada inválida). | ❌ **escondido** |

D4, D6 e D7 não são pegos pelos testes fornecidos, e o desempate de D5 só é coberto por `test_ranking.py`.
D6 apareceu comparando os totais do relatório com um cálculo independente das regras do README feito
direto sobre o CSV. D4 não muda nenhum total do arquivo real (o erro some no arredondamento final);
apareceu comparando a conversão reserva por reserva: em 19 das 235 confirmadas o valor via `float` é
inexato (ex.: 84,75 × 5,42 = 459,345 vira 459,34499999999997). D7 apareceu na revisão final e não afeta os
dados fornecidos (o README garante que todas as moedas do dataset têm taxa).

### 4.3 Valores de referência (pós-correção)

| Entrada | total | confirmed | room_nights | total_amount_brl |
|-|-|-|-|-|
| `exemplo-validacao.csv` | 12 | 9 | 28 | 7566.00 (bate com o README) |
| `reservas_hoteis.csv` | 300 | 235 | 1347 | 396170.00 |

---

## 5. Arquitetura e estrutura do projeto

### 5.1 Decisão: manter a arquitetura

```
cli.py  ──►  ReportBuilder (orquestração)  ──►  services/ (regras puras)
                     │                              ├─ status_policy
                     ▼                              ├─ stay_calculator
              repositories/ (I/O CSV)               ├─ currency_converter
              ├─ csv_reservation_repository         └─ row_parser
              └─ csv_rate_repository
models.py (dataclasses imutáveis) · exceptions.py (erros de domínio)
```

- **Repositórios** isolam I/O; **serviços** são funções puras e fáceis de testar.
- **Exceções de domínio** mapeiam para exit codes no CLI.
- Refatorar aumentaria o diff, esconderia as correções e arriscaria o contrato.

### 5.2 Estrutura do repositório

```
.
├── .claude/settings.json              # permissões da IA: bloqueia edição dos arquivos protegidos
├── .github/protected-files.sha256     # checksums dos testes fornecidos e CSVs
├── CLAUDE.md                          # regras de trabalho para a IA
├── data/                              # ⛔ não alterar
├── docs/
│   ├── PLANO-TECNICO.md               # este documento
│   └── CONVENCAO-COMMITS.md           # regras de commit, branch e PR
├── entrega/
│   ├── README-ENTREGA.md
│   └── uso-de-ia/
│       ├── sessao.md                  # exportação anonimizada da sessão
│       └── declaracao.md
├── output/.gitkeep                    # relatório gerado (ignorado pelo git)
├── src/onfly_report/                  # código corrigido (mesma estrutura)
├── tests/
│   ├── helpers.py                     # ⛔ fornecido
│   ├── test_currency.py               # ⛔ fornecido
│   ├── test_nights.py                 # ⛔ fornecido
│   ├── test_regression_report.py      # ⛔ fornecido
│   ├── test_status_rules.py           # ⛔ fornecido
│   ├── test_top_hotels.py             # ⛔ fornecido
│   ├── test_status_policy.py          # novo: D1 (RN-01)
│   ├── test_stay_calculator.py        # novo: D2 (RN-02)
│   ├── test_currency_converter.py     # novo: D3 e D4 (RN-03, RN-05)
│   ├── test_ranking.py                # novo: D5 (RN-08)
│   ├── test_reservation_repository.py # novo: D6 (RN-04)
│   ├── test_report_contract.py        # novo: amostra do README e contrato do JSON
│   ├── test_cli_exit_codes.py         # novo: exit codes 0, 1 e 2 (RN-11, RN-12)
│   └── test_missing_rate.py           # novo: D7, moeda sem taxa → exit 2 (RN-11)
├── tools/exportar_sessoes.py          # exportação anonimizada das sessões de IA
├── pyproject.toml
├── requirements.txt                   # sem deps de runtime
├── requirements-dev.txt               # pytest, ruff, pytest-cov
└── README.md                          # README da ONFLY
```

---

## 6. Estratégia de qualidade

1. **Leitura de negócio:** tabela RN-01…RN-13 a partir do README, comparada linha a linha com o
   módulo responsável.
2. **Cálculo independente:** script descartável (não versionado) aplicando as regras do README
   direto sobre o CSV, usado como referência para o arquivo real. Revelou D6 nos totais e D4 na comparação
   reserva por reserva.
3. **TDD:** para cada defeito, teste novo falhando → correção mínima → suíte inteira → commit.
4. **Testes de contrato em processo** (`main(argv)`): amostra completa do README, média `"0.00"`
   sem noites, formato do dinheiro, `report_version`, offset `-03:00` e exit codes 0, 1 e 2.
5. **Revisão final:** documentação conferida contra o código e o histórico. Revelou D7.
6. **Ferramentas:** `pytest`, `pytest-cov` (cobertura), `ruff` (lint e formatação) e checksum dos
   arquivos protegidos.

> Os módulos de D1, D2 e D3 tinham 100% de cobertura e mesmo assim estavam errados:
> cobertura mede execução, não correção.

**IA guiada por regras, com três camadas de controle:**

| Camada | Arquivo | Natureza |
|-|-|-|
| Instrução | `CLAUDE.md` | Missão, fluxo TDD, regras invioláveis, comandos |
| Imposição local | `.claude/settings.json` | Bloqueia edição dos arquivos protegidos e comandos git destrutivos |
| Verificação independente | `.github/protected-files.sha256` | `sha256sum -c` acusa qualquer alteração nos arquivos protegidos |

---

## 7. Fluxo Git

Regras completas em [`docs/CONVENCAO-COMMITS.md`](CONVENCAO-COMMITS.md). Resumo:

- **Conventional Commits** em português: `tipo(escopo): descrição no imperativo (RN-xx)`.
- **Atômico:** um defeito por commit, com o teste que prova e a correção juntos.
- `main` só recebe PR; branches `chore/`, `fix/`, `test/`, `docs/`.
- Merge **sem squash**, para preservar os commits atômicos.
- Nunca commitar `output/*.json`, `.venv/`, `.coverage`.

---

## 8. Entrega (pasta `entrega/`)

```
entrega/
├── README-ENTREGA.md
└── uso-de-ia/
    ├── sessao.md
    └── declaracao.md
```

Seções obrigatórias do `README-ENTREGA.md` (exigidas pela ONFLY): **defeitos corrigidos**,
**causa raiz em uma frase por defeito**, **como investigou/abordou**, **como validar** e
**resultado do `pytest`**.

---

## 9. Riscos e mitigação

| Risco | Impacto | Mitigação |
|-|-|-|
| Alterar sem querer um teste fornecido ou CSV | Reprovação | `sha256sum -c` antes de cada commit; não rodar `ruff format`/`--fix` em `tests/` |
| Ambiente local não ser 3.11 | Comportamento divergente | Validação em venv 3.11 limpo |
| Mudar formato do JSON ao corrigir | Quebra de contrato | `test_report_contract.py` congela chaves e formato |
| Commitar `output/report.json` | Ruído | `.gitignore` já cobre |

---

## 10. Definition of Done

- [x] CLI roda em Python 3.11 com exit 0 no dataset real e na amostra
- [x] Relatório segue o contrato (chaves, tipos, strings de dinheiro com 2 casas)
- [x] Amostra `exemplo-validacao.csv` bate com a tabela do README
- [x] `pytest -q` verde, com os testes fornecidos **inalterados**
- [x] D1–D7 corrigidos, cada um com teste que falhava antes
- [x] `ruff check` limpo e checksums dos arquivos protegidos OK
- [x] `entrega/README-ENTREGA.md` completo
- [x] `entrega/uso-de-ia/` com sessão e declaração
