# Plano Técnico — Teste Técnico ONFLY 2026

> **Consolidador de reservas de hotel (`onfly_report`)**
> Documento de contexto, estratégia de qualidade e plano de execução em 4 dias.
> Autor: Lucca Alvarenga · Elaborado com apoio de IA (Claude), declarado em `entrega/uso-de-ia/`.

---

## Sumário

1. [Contexto e objetivo](#1-contexto-e-objetivo)
2. [Escopo: o que pode e o que não pode](#2-escopo-o-que-pode-e-o-que-não-pode)
3. [Especificação de negócio (requisitos rastreáveis)](#3-especificação-de-negócio-requisitos-rastreáveis)
4. [Diagnóstico inicial](#4-diagnóstico-inicial)
5. [Arquitetura e estrutura do projeto](#5-arquitetura-e-estrutura-do-projeto)
6. [Estratégia de qualidade](#6-estratégia-de-qualidade)
   - 6.1 Análise de negócio · 6.2 Análise estática · 6.3 Testes avançados · 6.4 Análise com IA · 6.5 CI/CD
7. [Plano de execução — 4 dias](#7-plano-de-execução--4-dias)
8. [Fluxo Git e histórico de commits](#8-fluxo-git-e-histórico-de-commits)
9. [Entrega (pasta `entrega/`)](#9-entrega-pasta-entrega)
10. [Riscos e mitigação](#10-riscos-e-mitigação)
11. [Definition of Done](#11-definition-of-done)
12. [Apêndice: arquivos prontos](#12-apêndice-arquivos-prontos)

---

## 1. Contexto e objetivo

A ONFLY forneceu um CLI em Python 3.11 que lê a exportação de reservas de hotel de um cliente
(`data/reservas_hoteis.csv`), converte valores para BRL (`data/taxas_cambio.csv`) e gera um
relatório JSON consolidado. **O CLI roda, mas entrega números errados.**

**Natureza do desafio:** é um teste de **depuração e engenharia de qualidade**, não de construção
do zero. Não há API, banco, frontend nem deploy. O avaliador quer ver:

| O que é avaliado | Como vamos demonstrar |
|-|-|
| O relatório segue o contrato do README | Testes de contrato + oráculo independente + amostra de validação |
| Todos os defeitos foram corrigidos | Inclusive os **não cobertos** pelos testes fornecidos |
| Os 5 testes fornecidos passam **sem alteração** | `git diff` vazio em `tests/` fornecidos desde o commit inicial |
| Testes adicionais (“são considerados”) | Property-based, diferencial, contrato, mutation testing |
| Qualidade da investigação | `README-ENTREGA.md` com causa raiz, método e evidências |
| Uso responsável de IA | Sessão exportada + declaração honesta |

**Objetivo final:** entregar um repositório público em que qualquer pessoa clone, rode três
comandos e veja, com evidências objetivas, que o relatório está correto e por quê.

**Filosofia:** correções **cirúrgicas**, cada uma provada por um teste que falhava antes.
Qualidade demonstrada por evidência, não por volume de ferramentas.

---

## 2. Escopo: o que pode e o que não pode

| Ação | Permitido? |
|-|-|
| Corrigir o código em `src/onfly_report/` | ✅ É a tarefa principal |
| Criar testes novos (`tests/test_*.py`) | ✅ Contam pontos |
| Melhorar logs, reorganizar código interno, adicionar arquivos | ✅ |
| Adicionar ferramentas de **dev** (`requirements-dev.txt`, CI, pre-commit) | ✅ |
| Alterar os 5 testes fornecidos (`tests/test_*.py` originais e `tests/helpers.py`) | ❌ |
| Alterar `data/reservas_hoteis.csv` ou `data/taxas_cambio.csv` | ❌ |
| Mudar comando/argumentos do CLI | ❌ |
| Mudar nomes, tipos ou semântica dos campos do JSON | ❌ |
| Adicionar dependência de **runtime** | ❌ (o CLI usa só a biblioteca padrão) |

> ⚠️ Testes novos ficam **na raiz de `tests/`**. Subpastas quebram o `from helpers import run_cli`
> dos testes fornecidos se alguém reaproveitar o helper.

---

## 3. Especificação de negócio (requisitos rastreáveis)

Cada regra do README recebe um ID. Todo teste novo e todo commit citam o ID correspondente.
Isso cria **rastreabilidade bidirecional**: regra → código → teste.

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

## 4. Diagnóstico inicial

### 4.1 Estado de partida (medido)

- `pytest -q` → **5 failed** (esperado pelo README).
- Dataset real: 300 reservas, dados limpos (sem duplicatas, sem BOM, status/moedas consistentes,
  `hotel_id → hotel_name` único, todos os valores com 2 casas).
- Cobertura com os testes fornecidos: **85%**, mas com uma armadilha (ver 6.3.1).

### 4.2 Mapa de defeitos

| # | Regra | Local | Defeito | Causa raiz (1 frase) | Pego pelos testes fornecidos? |
|-|-|-|-|-|-|
| D1 | RN-01 | `status_policy.is_billable` | `status != "CANCELLED"` | Regra escrita por exclusão em vez de inclusão, deixando `NO_SHOW` faturável. | ✅ `test_status_rules` |
| D2 | RN-02 | `stay_calculator.calculate_room_nights` | `checkout.day - checkin.day` | Subtrai o dia do mês em vez de subtrair datas, quebrando na virada de mês/ano. | ✅ `test_nights` |
| D3 | RN-03 | `currency_converter.convert_to_brl` | `amount / rate` | Operação invertida: divide pela taxa em vez de multiplicar. | ✅ `test_currency` |
| D4 | RN-05 | `currency_converter.convert_to_brl` | `Decimal(str(float(...)))` | Passa o dinheiro por `float` binário, introduzindo erro de representação. | ❌ **escondido** |
| D5 | RN-08 | `report_builder.build` | `sorted(key=(amount, id))` | Ordenação crescente; o ranking precisa ser decrescente por valor. | ✅ `test_top_hotels` |
| D6 | RN-04 | `csv_reservation_repository.read` | `if len(rows) == 200: break` | Limite fixo de leitura descarta silenciosamente as linhas após a 200ª. | ❌ **escondido** |

> **D4 e D6 são o diferencial.** Validamos: com os dois reintroduzidos, os 5 testes fornecidos
> **continuam verdes**, e o relatório do dataset real ignora 100 reservas. Só os testes novos
> (propriedade + oráculo) os detectam.

### 4.3 Melhorias de robustez (não são defeitos do contrato, mas são do nível sênior)

| # | Situação | Hoje | Proposta |
|-|-|-|-|
| M1 | Moeda da reserva sem taxa na tabela | `KeyError` → exit **1** | `InputFileError` com mensagem clara → exit **2** (RN-11) |
| M2 | Moeda com caixa/espaço diferente | Repositório de taxas faz `.upper()`, parser não | Normalizar dos dois lados |
| M3 | `mypy --strict` | 3 erros (`dict` sem parâmetros de tipo) | Tipar com `dict[str, Any]` ou `TypedDict` |
| M4 | Logs | Só erros | `INFO` com linhas lidas, confirmadas e filtradas (em `stderr`, preservando o `stdout`) |

### 4.4 Valores de referência (obtidos na validação pós-correção)

| Entrada | total | confirmed | room_nights | total_amount_brl |
|-|-|-|-|-|
| `exemplo-validacao.csv` | 12 | 9 | 28 | 7566.00 (bate com o README) |
| `reservas_hoteis.csv` | 300 | 235 | 1347 | 396170.00 |

Estes números são **checkpoint**, não prova. A prova é o oráculo (6.3.4) e os testes.

---

## 5. Arquitetura e estrutura do projeto

### 5.1 Decisão: manter a arquitetura

A arquitetura fornecida já é limpa e **não deve ser reorganizada**:

```
cli.py  ──►  ReportBuilder (orquestração)  ──►  services/ (regras puras)
                     │                              ├─ status_policy
                     ▼                              ├─ stay_calculator
              repositories/ (I/O CSV)               ├─ currency_converter
              ├─ csv_reservation_repository         └─ row_parser
              └─ csv_rate_repository
models.py (dataclasses imutáveis) · exceptions.py (erros de domínio)
```

- **Repositórios** isolam I/O; **serviços** são funções puras (fáceis de testar com propriedades).
- **Exceções de domínio** mapeiam para exit codes no CLI.
- Refatorar aumentaria o diff, esconderia as correções e arriscaria o contrato.
  **Justifique essa decisão no README-ENTREGA**: decidir *não* refatorar também é decisão sênior.

### 5.2 Estrutura final do repositório

```
.
├── .claude/
│   └── settings.json                 # permissões da IA: bloqueia edição dos arquivos protegidos
├── .github/
│   ├── protected-files.sha256        # checksums dos testes fornecidos e CSVs (verificado no CI)
│   └── workflows/
│       └── ci.yml                    # lint, tipos, testes, cobertura, semgrep, amostra
│                                     # (CodeQL via "Default setup" do GitHub, sem YAML)
├── .semgrep/
│   └── money.yml                     # regra customizada: proibido float em dinheiro (RN-05)
├── .pre-commit-config.yaml           # ruff + mypy antes de cada commit
├── CLAUDE.md                         # regras de trabalho para a IA (lido pelo Claude Code)
├── data/                             # ⛔ não alterar
├── docs/
│   ├── PLANO-TECNICO.md              # este documento
│   └── CONVENCAO-COMMITS.md          # regras de commit, branch, PR e exemplos
├── entrega/
│   ├── README-ENTREGA.md             # obrigatório
│   └── uso-de-ia/
│       ├── sessao-01.md              # exportação das sessões
│       └── declaracao.md
├── output/.gitkeep                   # relatório gerado (ignorado pelo git)
├── src/onfly_report/                 # código corrigido (mesma estrutura)
├── tests/
│   ├── helpers.py                    # ⛔ fornecido
│   ├── test_currency.py              # ⛔ fornecido
│   ├── test_nights.py                # ⛔ fornecido
│   ├── test_regression_report.py     # ⛔ fornecido
│   ├── test_status_rules.py          # ⛔ fornecido
│   ├── test_top_hotels.py            # ⛔ fornecido
│   ├── test_properties.py            # novo: Hypothesis, uma propriedade por regra
│   ├── test_oracle.py                # novo: teste diferencial contra oráculo independente
│   ├── test_cli_contract.py          # novo: schema, exit codes, --top (em processo)
│   ├── test_reader.py                # novo: >200 linhas, arquivo ausente, colunas faltando
│   └── test_report_rules.py          # novo: empate no ranking, by_month, half-up, média zero
├── pyproject.toml                    # + config de ruff, mypy, coverage, mutmut
├── requirements.txt                  # inalterado (sem deps de runtime)
├── requirements-dev.txt              # + hypothesis, pytest-cov, mypy, mutmut
└── README.md                         # README da ONFLY + seção curta no topo
```

---

## 6. Estratégia de qualidade

Quatro frentes complementares. Nenhuma sozinha encontra todos os defeitos. A tabela abaixo
mostra **o que foi efetivamente validado** sobre este código:

| Defeito | Leitura de negócio | Ruff | Semgrep | Cobertura | Hypothesis | Oráculo | Testes fornecidos |
|-|-|-|-|-|-|-|-|
| D1 NO_SHOW faturado | ✅ | – | – | – | ✅ | ✅ | ✅ |
| D2 `.day` | ✅ | – | – | – | ✅ | ✅ | ✅ |
| D3 divide | ✅ | – | – | – | ✅ | ✅ | ✅ |
| D4 float | ✅ | – | ✅ | – | ✅ | ✅* | ❌ |
| D5 ordenação | ✅ | – | – | – | – | ✅ | ✅ |
| D6 corte em 200 | ✅ | ✅ `PLR2004` | – | ✅ linha não executada | – | ✅ | ❌ |

\* depende de o erro de float alterar o arredondamento final; a propriedade pega sempre.

**Lição para o README-ENTREGA:** os módulos com D1, D2 e D3 tinham **100% de cobertura** e
mesmo assim estavam errados. Cobertura mede execução, não correção.

### 6.1 Análise de negócio (manual, a mais importante)

1. Ler o README da ONFLY e preencher a tabela RN-01…RN-13 (seção 3).
2. Para cada RN, abrir o módulo responsável e comparar **linha a linha** com a regra.
3. Para cada divergência: registrar hipótese → escrever teste que reproduz → só então corrigir.
4. Rodar a amostra `exemplo-validacao.csv` e comparar campo a campo com a tabela do README.
5. Revisar casos de borda que a amostra não cobre: virada de **ano**, `rooms > 1`, empate no
   ranking, `--top` maior que o número de hotéis, média sem noites, hotel com nome contendo vírgula.

**Caderno de investigação** (vira a seção “Como investiguei”): para cada defeito anote sintoma,
hipótese, experimento, evidência e conclusão.

### 6.2 Análise estática

| Ferramenta | Uso | Achado neste código |
|-|-|-|
| **Ruff** (lint + format) | Regras `E,F,I,B,UP,SIM,RUF,PLR2004` | `PLR2004` aponta o `== 200` (D6) |
| **mypy `--strict`** | Tipos | 3 erros de `dict` sem parâmetros (M3) |
| **Semgrep** (regra custom) | Proíbe `float()` em `services/` | Pega D4; 0 achados após a correção |
| **CodeQL** | Análise semântica no GitHub | Gratuito em repositório público |
| **Bandit** | Segurança | Esperado: nada relevante (bom registrar) |
| **Vulture** | Código morto | Opcional |
| **Radon** | Complexidade ciclomática / manutenibilidade | Opcional; registre o índice antes e depois |
| **pip-audit** | CVEs em dependências de dev | Opcional, roda no CI |

> `PLR2004` acusa números mágicos nos **testes fornecidos** (`== 3`). Como não podemos alterá-los,
> desligue essa regra para `tests/**` via `per-file-ignores` (configuração na seção 12.1).

### 6.3 Testes avançados

Pirâmide adotada:

```
              ┌───────────────────────────┐
              │ Mutation testing (mutmut) │  mede a força da suíte
              ├───────────────────────────┤
              │ Diferencial (oráculo)     │  dataset real inteiro
              ├───────────────────────────┤
              │ Contrato do CLI           │  schema, exit codes, --top
              ├───────────────────────────┤
              │ Property-based (Hypothesis)│  uma propriedade por RN
              ├───────────────────────────┤
              │ Unitários de exemplo       │  bordas específicas
              └───────────────────────────┘
        + 5 testes E2E fornecidos (subprocesso), intocados
```

#### 6.3.1 Cobertura (pytest-cov) — com uma armadilha

Os testes fornecidos executam o CLI em **subprocesso**. Sem configuração, o `pytest-cov` reporta
**“no data collected”**. Solução validada (coverage ≥ 7.10):

```toml
[tool.coverage.run]
source = ["onfly_report"]
branch = true
patch = ["subprocess"]
```

Resultado medido: 85% de cobertura com os testes fornecidos, e a linha do `break` (D6)
aparece como **nunca executada**. Após os testes novos: 88%+ (meta: ≥ 90% com ramos).

#### 6.3.2 Property-based testing (Hypothesis)

Cada regra vira uma propriedade universal. O Hypothesis gera milhares de entradas, inclusive
viradas de mês/ano e valores com centavos difíceis para `float`, e **reduz** o contraexemplo ao
menor caso. Validado: falha no código original (D1, D2, D3, D4) e passa no corrigido.
Código completo em 12.5.

#### 6.3.3 Testes de contrato do CLI (em processo)

Chamar `main(argv)` diretamente, **não** via subprocesso, para que cobertura e mutation testing
enxerguem o `cli.py`. Cobre: ordem das chaves do JSON, `report_version`, offset `-03:00`,
`--top` respeitado, exit 2 para arquivo ausente e para `--top` = `0`, `-1`, `abc`.
Código em 12.7.

#### 6.3.4 Teste diferencial (oráculo independente)

Uma reimplementação **ingênua e independente** das regras (sem reaproveitar nenhuma função do
`src/`), comparada com o `ReportBuilder` no **dataset real inteiro** e na amostra. É a técnica
de *N-version programming* aplicada a testes. É o único teste que pega **os 6 defeitos**.
Código em 12.6.

#### 6.3.5 Mutation testing (mutmut 3)

O mutmut injeta pequenos bugs (troca `-` por `+`, `==` por `!=`, remove linhas) e verifica se
algum teste falha. **Mutation score** = mutantes mortos ÷ total. Mede a qualidade real da suíte.

Resultado medido no código corrigido com os testes novos:

| Módulo | Resultado |
|-|-|
| `status_policy`, `stay_calculator`, `currency_converter` | **100% mortos** |
| `report_builder` | 186 mortos / 33 sobreviventes |
| `row_parser`, repositórios | sobreviventes em mensagens de erro e caminhos de exceção |
| `cli.py` | “no tests”: mutmut 3 não enxerga testes em subprocesso → por isso 6.3.3 |

Ação: analisar sobreviventes, matar os relevantes com testes, justificar os equivalentes
(ex.: texto de mensagem de log). Registrar score antes e depois no README-ENTREGA.

#### 6.3.6 Opcionais de nível pesquisa

| Ferramenta | Técnica | Onde aplicar |
|-|-|-|
| **CrossHair** | Execução simbólica (solver Z3) | Contratos em `calculate_room_nights` e `convert_to_brl` |
| **Atheris** (Google) | Fuzzing guiado por cobertura | `RowParser.parse` com linhas malformadas (deve sempre dar `InputFileError`) |
| **Pynguin** | Geração automática de testes (busca evolutiva) | **Só após** as correções: ele congela o comportamento atual, inclusive bugs |

Use no máximo um destes, e só se sobrar tempo no Dia 3. Valor real: baixo para um CLI deste tamanho.

### 6.4 Análise com IA

**Princípio:** IA acelera, mas **toda conclusão é verificada por um teste executável**. Nada
entra no código porque “a IA disse”.

| Uso | Ferramenta | Como |
|-|-|-|
| Revisão de requisitos vs. código | Claude (esta sessão) | Mapeou RN → defeitos; cada achado foi reproduzido por teste |
| Revisão automática de PR | **CodeRabbit** ou **GitHub Copilot code review** | Abrir um PR `fix/defeitos` → `main` e deixar o bot revisar; responder os comentários |
| Geração de testes para cobertura | **Qodo Cover** (opcional) | Só após as correções; revisar e editar cada teste gerado |
| Análise estática com ML | **Snyk Code** / **SonarQube Cloud** | Gratuitos para repositório público; anexar o print do quality gate |

**IA guiada por regras, com três camadas de controle:**

| Camada | Arquivo | Natureza |
|-|-|-|
| Instrução | `CLAUDE.md` | Diz à IA o que fazer: missão, fluxo TDD, regras invioláveis, comandos |
| Imposição local | `.claude/settings.json` | **Bloqueia** edição dos arquivos protegidos e comandos git destrutivos; pede confirmação para commit/push |
| Verificação independente | `.github/protected-files.sha256` + CI | Falha o build se qualquer arquivo protegido mudar, mesmo que a IA contorne pelo terminal |

Documentar a regra é bom; impor a regra no ambiente e verificá-la de forma independente é o nível sênior.

**Registro obrigatório** (`entrega/uso-de-ia/`): exportar **todas** as sessões e declarar
ferramenta, modelo, o que a IA fez e o que você fez (modelo em 12.9).

### 6.5 CI/CD

Pipeline no GitHub Actions a cada push/PR, em **Python 3.11** (versão do contrato):

```
ruff check → ruff format --check → mypy --strict → semgrep → pytest + cobertura (gate ≥ 90%)
→ roda o CLI na amostra e no dataset real → upload do report.json como artefato
```

Mais CodeQL pelo "Default setup" do GitHub, além da verificação de checksum dos arquivos protegidos. O badge do CI fica no topo do README. Arquivo em 12.3.

> “Deploy” não se aplica: o produto é um CLI. O equivalente é o CI verde e o `report.json`
> publicado como artefato do workflow.

---

## 7. Plano de execução — 4 dias

### Dia 1 — Setup, linha de base e investigação

| # | Tarefa | Pronto quando |
|-|-|-|
| 1.1 | Criar repositório público; **commit 1 = material intacto** | `git log` mostra o original |
| 1.1b | Commit 2: `CLAUDE.md`, `.claude/settings.json`, `docs/`, `.github/protected-files.sha256` | `sha256sum -c .github/protected-files.sha256` = tudo OK |
| 1.2 | Python 3.11 + venv; instalar `requirements-dev.txt` | `python --version` = 3.11.x |
| 1.3 | Rodar `pytest -q`, CLI na amostra e no dataset; salvar saídas em `docs/baseline/` | 5 falhas registradas |
| 1.4 | Configurar ruff, mypy, coverage (com `patch = ["subprocess"]`); rodar e salvar a linha de base | Números “antes” registrados |
| 1.5 | Preencher a matriz RN-01…RN-13 e o caderno de investigação | Hipóteses D1–D6 anotadas com evidência |
| 1.6 | Commit: `chore: tooling de qualidade (ruff, mypy, coverage)` | CI ainda vermelho (esperado) |

### Dia 2 — Correções guiadas por teste (um defeito por commit)

Para cada defeito: **teste falhando → correção mínima → teste passando → commit.**

| # | Defeito | Teste que prova | Commit |
|-|-|-|-|
| 2.1 | D6 corte em 200 | `test_reader.py` com 250 linhas | `fix(reader): ler todas as linhas do CSV (RN-04)` |
| 2.2 | D1 status | `test_status_rules` + propriedade | `fix(status): somente CONFIRMED é faturável (RN-01)` |
| 2.3 | D2 noites | `test_nights` + propriedade (virada de ano) | `fix(nights): usar diferença de datas (RN-02)` |
| 2.4 | D3 + D4 câmbio | `test_currency` + propriedade + semgrep | `fix(currency): multiplicar em Decimal, sem float (RN-03, RN-05)` |
| 2.5 | D5 ranking | `test_top_hotels` + teste de empate | `fix(ranking): ordenar desc por valor, empate por id (RN-08)` |
| 2.6 | Validação | Amostra bate 100% com o README; `pytest -q` verde | `test: oráculo diferencial no dataset real` |

**Meta do dia:** 5 testes fornecidos verdes, amostra correta, oráculo verde, `total_reservations = 300`.

### Dia 3 — Robustez, testes avançados e automação

| # | Tarefa | Pronto quando |
|-|-|-|
| 3.1 | M1–M4 (moeda sem taxa → exit 2, normalização, tipos, logs) | `mypy --strict` limpo |
| 3.2 | `test_cli_contract.py` e `test_report_rules.py` | Cobertura ≥ 90% com ramos |
| 3.3 | Mutation testing; matar sobreviventes relevantes | Score registrado antes/depois |
| 3.4 | `.pre-commit-config.yaml`, `ci.yml`, CodeQL (Default setup) | CI verde no GitHub |
| 3.5 | PR `fix/defeitos` → revisão do CodeRabbit/Copilot; responder e mergear | PR com revisão visível |
| 3.6 | (Opcional) SonarQube Cloud ou um item de 6.3.6 | Print/link anexado |

### Dia 4 — Documentação, entrega e verificação final

| # | Tarefa | Pronto quando |
|-|-|-|
| 4.1 | `entrega/README-ENTREGA.md` (modelo 12.8) | Todas as seções obrigatórias preenchidas |
| 4.2 | `entrega/uso-de-ia/` (sessões + declaração) | Arquivos exportados |
| 4.3 | Seção curta no topo do `README.md` (badge, como rodar, link para a entrega) | — |
| 4.4 | **Teste de fumaça do zero:** clonar em pasta nova, criar venv 3.11, seguir o README | Funciona sem nenhum passo extra |
| 4.5 | `sha256sum -c .github/protected-files.sha256` e `git diff <commit-inicial> -- tests/helpers.py tests/test_currency.py tests/test_nights.py tests/test_regression_report.py tests/test_status_rules.py tests/test_top_hotels.py data/` | Tudo `OK` e diff **vazio** |
| 4.6 | Checklist da ONFLY item a item + Definition of Done (seção 11) | Tudo marcado |
| 4.7 | Confirmar repositório público (aba anônima) e enviar o link no forms | Link enviado |

**Folga:** o trabalho cabe em ~2,5 dias. Use a sobra para revisar o texto da entrega, não para
adicionar ferramentas.

---

## 8. Fluxo Git e histórico de commits

> **Regras completas, exemplos de commits bem e mal escritos, modelo de PR, estratégia de merge e
> hook de validação: [`docs/CONVENCAO-COMMITS.md`](CONVENCAO-COMMITS.md).**

Resumo:

- **Conventional Commits** em português: `tipo(escopo): descrição no imperativo (RN-xx)`.
- **Atômico:** um defeito por commit, com o teste que prova e a correção juntos.
- **Corpo** responde: qual era o problema, por que acontecia, como foi provado.
- **Trailers:** `Refs: RN-xx` e `Co-Authored-By` quando a IA escreveu o código.
- `main` só recebe PR com CI verde; branches `chore/`, `fix/`, `test/`, `docs/`.
- Merge **sem squash**, para preservar os commits atômicos.
- Histórico público é imutável: sem `--amend`, `rebase` ou `push --force` após o push.
- Nunca commitar `output/*.json`, `.venv/`, `mutants/` (adicione `mutants/` ao `.gitignore`).
- Release final: tag `v1.0.0` + GitHub Release.

O histórico-alvo completo está na seção 4 da convenção.

---

## 9. Entrega (pasta `entrega/`)

```
entrega/
├── README-ENTREGA.md
└── uso-de-ia/
    ├── sessao-01.md        # exportação nativa da ferramenta (uma por sessão)
    └── declaracao.md
```

Seções obrigatórias do `README-ENTREGA.md` (exigidas pela ONFLY): **defeitos corrigidos**,
**causa raiz em uma frase por defeito**, **como investigou/abordou**, **como validar** e
**resultado do `pytest`**. Modelos completos em 12.8 e 12.9.

---

## 10. Riscos e mitigação

| Risco | Impacto | Mitigação |
|-|-|-|
| Alterar sem querer um teste fornecido ou CSV | Reprovação | `git diff` do item 4.5; não rodar `ruff --fix`/`ruff format` sobre os arquivos fornecidos |
| Ambiente local não ser 3.11 | Comportamento divergente | venv 3.11 + matriz do CI em 3.11 |
| Mudar formato do JSON ao “melhorar” | Quebra de contrato | `test_cli_contract.py` congela chaves e tipos |
| Overengineering (ferramentas demais) | Avaliador vê ruído | Cada ferramenta precisa de um achado ou métrica no README-ENTREGA |
| Ferramenta de IA gerar teste que congela bug | Falsa segurança | Gerar testes só após correções; revisar cada um |
| Commitar `output/report.json` | Ruído | `.gitignore` já cobre; checar no item 4.4 |
| Esquecer a exportação da sessão de IA | Entrega incompleta | Exportar ao fim de **cada** sessão, não só no Dia 4 |

> Cuidado com `ruff format`: rode só em `src/` e nos **seus** testes. Formatar `tests/` inteiro
> alteraria os arquivos fornecidos.

---

## 11. Definition of Done

- [ ] `PYTHONPATH=src python -m onfly_report --input data/reservas_hoteis.csv --rates data/taxas_cambio.csv --output output/report.json` roda em Python 3.11 com exit 0
- [ ] Relatório segue exatamente o contrato (chaves, tipos, strings de dinheiro com 2 casas)
- [ ] Amostra `exemplo-validacao.csv` bate 100% com a tabela do README
- [ ] `pytest -q` verde, com os 5 testes fornecidos **inalterados**
- [ ] D1–D6 corrigidos, cada um com teste que falhava antes
- [ ] Oráculo diferencial verde no dataset real
- [ ] Cobertura ≥ 90% (ramos), mutation score registrado
- [ ] `ruff check`, `mypy --strict`, `semgrep` limpos
- [ ] CI verde + badge no README
- [ ] `entrega/README-ENTREGA.md` completo
- [ ] `entrega/uso-de-ia/` com sessões e declaração
- [ ] `git diff` vazio nos arquivos protegidos
- [ ] Repositório público, testado em clone limpo, link enviado no forms

---

## 12. Apêndice: arquivos prontos

> Validados em uma cópia do projeto com as correções aplicadas: testes de propriedade e oráculo
> **falham no código original** e **passam no corrigido**; com D4 e D6 reintroduzidos, os 5 testes
> fornecidos continuam verdes e estes falham. Validação feita em Python 3.13; o CI confirma em 3.11.

### 12.1 `pyproject.toml` (acréscimos)

```toml
[tool.ruff]
line-length = 120
target-version = "py311"
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "RUF", "PLR2004"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["PLR2004"]   # números mágicos são aceitáveis em asserts (e os testes fornecidos não podem mudar)

[tool.mypy]
python_version = "3.11"
strict = true
mypy_path = "src"
packages = ["onfly_report"]

[tool.coverage.run]
source = ["onfly_report"]
branch = true
patch = ["subprocess"]     # mede o CLI executado pelos testes fornecidos via subprocess

[tool.coverage.report]
show_missing = true
fail_under = 90

[tool.mutmut]
paths_to_mutate = ["src/onfly_report/"]
tests_dir = ["tests/"]
also_copy = ["data/"]
```

**Estado esperado logo após aplicar esta configuração** (validado), que vira trabalho planejado:

| Verificação | Resultado inicial | Resolvido em |
|-|-|-|
| `ruff check src tests` | limpo (com as correções) / `PLR2004` no `== 200` antes delas | Dia 2 |
| `ruff format --check src` | `report_builder.py` fora do padrão (código original) | rode `ruff format src` no commit de tooling |
| `mypy` | 3 erros `type-arg` em `report_builder.py` | Dia 3 (M3) |
| `pytest --cov` | 88% < 90% (`fail_under`) | Dia 3 (`test_reader.py`, `test_report_rules.py`) |

### 12.2 `requirements-dev.txt`

```text
pytest==8.3.4
ruff==0.8.4
pytest-cov
hypothesis
mypy
mutmut
```

Depois de instalar, fixe as versões que você usou (`pip freeze | grep -iE "pytest-cov|hypothesis|mypy|mutmut"`).
Na validação foram: `pytest-cov 7.1.0`, `hypothesis 6.170.15`, `mypy 2.3.1`, `mutmut 3.8.1`,
`coverage 7.17.2`. Semgrep fica fora deste arquivo (é pesado); o CI instala à parte.

Comandos do dia a dia:

```bash
ruff check src tests && ruff format --check src
mypy
pytest -q --cov
semgrep scan --config .semgrep/ --error --metrics=off src/
mutmut run && mutmut results
```

### 12.3 `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Arquivos protegidos intactos (testes fornecidos e CSVs)
        run: sha256sum -c .github/protected-files.sha256

      - name: Instalar dependências de dev
        run: pip install -r requirements-dev.txt

      - name: Lint (ruff)
        run: |
          ruff check src tests
          ruff format --check src

      - name: Tipos (mypy --strict)
        run: mypy

      - name: Regras de negócio estáticas (semgrep)
        run: |
          pip install semgrep
          semgrep scan --config .semgrep/ --error --metrics=off --disable-version-check src/

      - name: Testes + cobertura
        run: pytest -q --cov --cov-report=term-missing

      - name: Amostra de validação e dataset real
        run: |
          PYTHONPATH=src python -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json
          PYTHONPATH=src python -m onfly_report --input data/reservas_hoteis.csv --rates data/taxas_cambio.csv --output output/report.json

      - uses: actions/upload-artifact@v4
        with:
          name: relatorios
          path: output/*.json
```

`codeql.yml`: em *Settings → Code security → Code scanning → CodeQL analysis → Default setup*, o
GitHub configura sozinho (sem YAML) para Python em repositório público.

`.pre-commit-config.yaml` (hooks locais, sem depender de versões de repositórios externos):

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff
        name: ruff check
        entry: ruff check src
        language: system
        pass_filenames: false
      - id: ruff-format
        name: ruff format
        entry: ruff format --check src
        language: system
        pass_filenames: false
      - id: mypy
        name: mypy --strict
        entry: mypy
        language: system
        pass_filenames: false
```

### 12.4 `.semgrep/money.yml`

```yaml
rules:
  - id: no-float-in-money
    languages: [python]
    severity: ERROR
    message: "Dinheiro deve usar Decimal do início ao fim (README: 'Use Decimal, nunca float'). Encontrado float() em código de valores."
    paths:
      include: ["**/onfly_report/services/*.py"]
    pattern-either:
      - pattern: float(...)
      - pattern: Decimal(str(float(...)))
```

Validado: 2 achados no código original (`currency_converter.py`), 0 no corrigido.

### 12.5 `tests/test_properties.py`

```python
"""Testes baseados em propriedades (Hypothesis): cada regra do README vira uma propriedade."""

from datetime import date, timedelta
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from onfly_report.services.currency_converter import convert_to_brl
from onfly_report.services.status_policy import is_billable
from onfly_report.services.stay_calculator import calculate_room_nights

RATES = {"BRL": Decimal("1.000000"), "USD": Decimal("5.420000"), "EUR": Decimal("5.880000")}

dates = st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
money = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000"), places=2)


@given(checkin=dates, stay=st.integers(min_value=1, max_value=400), rooms=st.integers(min_value=1, max_value=10))
def test_room_nights_is_date_difference_times_rooms(checkin, stay, rooms):
    """RN-02: diferença não inclusiva, válida em virada de mês/ano."""
    checkout = checkin + timedelta(days=stay)
    assert calculate_room_nights(checkin, checkout, rooms) == stay * rooms


@given(amount=money, currency=st.sampled_from(sorted(RATES)))
def test_conversion_is_exact_multiplication(amount, currency):
    """RN-03 e RN-05: amount * rate, exato em Decimal (sem passar por float)."""
    result = convert_to_brl(amount, currency, RATES)
    assert isinstance(result, Decimal)
    assert result == amount * RATES[currency]


@given(status=st.text())
def test_only_confirmed_is_billable(status):
    """RN-01: somente CONFIRMED é faturável."""
    assert is_billable(status) is (status == "CONFIRMED")
```

Sugestão: acrescente propriedades para RN-08 (ranking sempre ordenado e com no máximo `--top`
itens) e RN-09 (todo campo de dinheiro casa com `^\d+\.\d{2}$`).

### 12.6 `tests/test_oracle.py`

```python
"""Teste diferencial: um oráculo independente e ingênuo das regras do README vs. o CLI."""

import csv
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from onfly_report.repositories.csv_rate_repository import CsvRateRepository
from onfly_report.repositories.csv_reservation_repository import CsvReservationRepository
from onfly_report.services.report_builder import ReportBuilder

ROOT = Path(__file__).resolve().parent.parent
RATES = ROOT / "data" / "taxas_cambio.csv"


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def oracle(input_path: Path, top: int = 5) -> dict:
    rates = {r["currency"]: Decimal(r["rate_to_brl"]) for r in csv.DictReader(RATES.open(encoding="utf-8"))}
    rows = list(csv.DictReader(input_path.open(encoding="utf-8")))
    confirmed = [r for r in rows if r["status"] == "CONFIRMED"]
    months, hotels = defaultdict(lambda: [0, 0, Decimal(0)]), defaultdict(lambda: ["", 0, Decimal(0)])
    nights_total, amount_total = 0, Decimal(0)
    for r in confirmed:
        nights = (date.fromisoformat(r["checkout_date"]) - date.fromisoformat(r["checkin_date"])).days * int(r["rooms"])
        brl = Decimal(r["amount"]) * rates[r["currency"]]
        nights_total += nights
        amount_total += brl
        m = months[r["checkin_date"][:7]]
        m[0], m[1], m[2] = m[0] + 1, m[1] + nights, m[2] + brl
        h = hotels[r["hotel_id"]]
        h[0], h[1], h[2] = r["hotel_name"], h[1] + nights, h[2] + brl
    ranked = sorted(hotels.items(), key=lambda kv: (-kv[1][2], kv[0]))[:top]
    return {
        "summary": {
            "total_reservations": len(rows),
            "confirmed_reservations": len(confirmed),
            "cancelled_reservations": sum(r["status"] == "CANCELLED" for r in rows),
            "no_show_reservations": sum(r["status"] == "NO_SHOW" for r in rows),
            "total_room_nights": nights_total,
            "total_amount_brl": _money(amount_total),
            "average_nightly_rate_brl": _money(amount_total / nights_total) if nights_total else "0.00",
        },
        "by_month": [
            {"month": k, "reservations": v[0], "room_nights": v[1], "total_brl": _money(v[2])}
            for k, v in sorted(months.items())
        ],
        "top_hotels": [
            {"hotel_id": k, "hotel_name": v[0], "room_nights": v[1], "total_brl": _money(v[2])} for k, v in ranked
        ],
    }


@pytest.mark.parametrize("dataset", ["reservas_hoteis.csv", "exemplo-validacao.csv"])
def test_cli_matches_independent_oracle(dataset):
    path = ROOT / "data" / dataset
    report = ReportBuilder(CsvReservationRepository(path), CsvRateRepository(RATES), top_n=5).build()
    report.pop("report_version"), report.pop("generated_at")
    assert report == oracle(path)
```

> O oráculo é **propositalmente ingênuo e independente** (lê o CSV direto, sem usar nada de `src/`).
> Se ele reutilizasse funções do código testado, herdaria os mesmos bugs.

### 12.7 `tests/test_cli_contract.py`

```python
"""Contrato do CLI em processo (visível para cobertura e mutation testing)."""

import json
from pathlib import Path

import pytest

from onfly_report.cli import main

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def test_exit_code_0_and_schema(tmp_path, capsys):
    out = tmp_path / "r.json"
    code = main(
        [
            "--input",
            str(DATA / "exemplo-validacao.csv"),
            "--rates",
            str(DATA / "taxas_cambio.csv"),
            "--output",
            str(out),
            "--top",
            "2",
        ]
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert list(report) == ["report_version", "generated_at", "summary", "by_month", "top_hotels"]
    assert report["report_version"] == "1.0"
    assert report["generated_at"].endswith("-03:00")
    assert len(report["top_hotels"]) == 2
    assert "Reservas: 12" in capsys.readouterr().out


def test_missing_input_returns_2(tmp_path):
    assert main(["--input", str(tmp_path / "nao-existe.csv"), "--rates", str(DATA / "taxas_cambio.csv")]) == 2


@pytest.mark.parametrize("top", ["0", "-1", "abc"])
def test_invalid_top_exits_2(top):
    with pytest.raises(SystemExit) as exc:
        main(["--input", "x.csv", "--rates", "y.csv", "--top", top])
    assert exc.value.code == 2
```

### 12.8 Modelo de `entrega/README-ENTREGA.md`

````markdown
# Entrega — Teste Técnico ONFLY 2026

**Candidato:** Lucca Alvarenga · **Repositório:** <link> · **CI:** <badge>

## Resumo
Corrigi 6 defeitos no CLI (4 cobertos pelos testes fornecidos e 2 escondidos), sem alterar
testes fornecidos, dados, comando ou schema. Adicionei N testes (propriedades, oráculo
diferencial, contrato) e automação de qualidade.

## Defeitos corrigidos
| # | Arquivo | Regra | Causa raiz (uma frase) | Correção | Teste que prova |
|-|-|-|-|-|-|
| D1 | services/status_policy.py | Só CONFIRMED é faturável | … | … | test_status_rules, test_properties |
| D2 | … | … | … | … | … |
| … | | | | | |

## Como investiguei
1. Matriz de regras (RN-01..13) a partir do README, comparada linha a linha com o código.
2. Linha de base: 5 testes falhando, cobertura X%, ruff/mypy/semgrep.
3. Achados escondidos: PLR2004 e cobertura de ramos apontaram o corte em 200 linhas…
4. Para cada defeito: teste que falha → correção mínima → commit (ver `git log`).
5. Oráculo independente no dataset real para garantir que não restou divergência.

## Decisões técnicas
- Mantive a arquitetura (repositórios/serviços) para preservar o contrato e um diff auditável.
- Melhorias além do contrato: moeda sem taxa → exit 2; mypy --strict; logs em stderr.

## Como validar
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
PYTHONPATH=src python -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json
```
Compare `output/exemplo.json` com a tabela “Amostra de validação” do README.

## Resultado do pytest
```
<colar a saída real de: pytest -q>
```

## Métricas de qualidade
| Métrica | Antes | Depois |
|-|-|-|
| Testes passando | 0/5 | N/N |
| Cobertura (ramos) | 85% | X% |
| Mutation score | — | X% |
| ruff / mypy --strict / semgrep | n achados | 0 |

## Uso de IA
Ver `entrega/uso-de-ia/declaracao.md`.
````

### 12.9 Modelo de `entrega/uso-de-ia/declaracao.md`

```markdown
# Declaração de uso de IA

## Ferramentas e modelos
- Claude (Anthropic), modelo claude-opus-5-5, no app Claude: análise do material, planejamento,
  mapeamento de regras para defeitos, rascunho de testes e configurações.
- <CodeRabbit / Copilot code review, se usado>: revisão automática do PR.

## O que a IA fez
- Leu o material e propôs a matriz de regras e o mapa de defeitos D1–D6.
- Sugeriu ferramentas e rascunhou testes de propriedade, oráculo e CI.

## O que eu fiz
- Reproduzi cada defeito localmente antes de corrigir; escrevi/revisei cada correção.
- Validei cada sugestão executando testes; descartei/ajustei: <exemplos concretos>.
- Decidi escopo, arquitetura e o que ficou de fora; escrevi a documentação final.

## Sessões
- `sessao-01.md`: planejamento e análise (data).
- `sessao-02.md`: …
```
