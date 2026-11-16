# Convenção de Commits, Branches e Pull Requests

> Vale para humanos e para assistentes de IA (referenciado no `CLAUDE.md`).
> Objetivo: que o `git log` conte a história da investigação. Cada defeito encontrado,
> provado e corrigido deve ser legível sem abrir o código.

---

## 1. Formato da mensagem

Baseado em [Conventional Commits 1.0.0](https://www.conventionalcommits.org/pt-br/v1.0.0/), em português.

```
<tipo>(<escopo>): <descrição curta> (RN-xx)
                                              ← linha em branco
<corpo: o PORQUÊ da mudança, quebrado em ~72 colunas>
                                              ← linha em branco
<rodapé: referências e trailers>
```

### 1.1 Assunto (primeira linha)

| Regra | Certo | Errado |
|-|-|-|
| Imperativo, como uma ordem | `usar diferença de datas` | `usando…`, `usei…`, `uso…` |
| Começa com minúscula | `fix(status): somente CONFIRMED…` | `fix(status): Somente…` |
| Sem ponto final | `…(RN-02)` | `…(RN-02).` |
| Até ~72 caracteres | — | assunto que vira parágrafo |
| Diz **o quê**, de forma específica | `ler todas as linhas do CSV` | `ajustes`, `corrige bug`, `wip` |
| Cita a regra de negócio quando houver | `(RN-04)` | — |

### 1.2 Tipos

| Tipo | Quando usar neste projeto |
|-|-|
| `fix` | Corrige comportamento divergente do README (D1–D6, M1) |
| `test` | Adiciona/ajusta **testes novos** (nunca os fornecidos) |
| `refactor` | Muda estrutura sem mudar comportamento (ex.: tipagem para mypy strict) |
| `chore` | Tooling, configuração, `.gitignore`, dependências de dev |
| `ci` | GitHub Actions, CodeQL, verificações automáticas |
| `docs` | README, `entrega/`, `docs/`, `CLAUDE.md` |
| `style` | Somente formatação (ex.: `ruff format src`), sem lógica |
| `perf` | Melhoria de desempenho (improvável aqui) |
| `feat` | **Evitar.** O desafio não pede funcionalidade nova |

### 1.3 Escopos

Use o componente afetado: `reader`, `rates`, `parser`, `status`, `nights`, `currency`, `ranking`,
`report`, `cli`, `types`, `logs`, `tooling`, `entrega`. Omita o escopo quando a mudança for transversal.

### 1.4 Corpo

Obrigatório em todo `fix` e em qualquer commit não óbvio. Responde a três perguntas:

1. **Qual era o problema?** Sintoma observável, com exemplo concreto se possível.
2. **Por que acontecia?** Causa raiz em uma frase.
3. **Como foi provado?** Qual teste falhava antes e passa agora.

Não descreva o diff linha a linha; o diff já mostra isso.

### 1.5 Rodapé (trailers)

```
Refs: RN-02
Co-Authored-By: Claude <noreply@anthropic.com>
```

- `Refs:` liga o commit à regra de negócio (rastreabilidade).
- `Co-Authored-By:` em commits com código escrito ou proposto pela IA. Isso conversa com
  `entrega/uso-de-ia/declaracao.md`. O Claude Code adiciona automaticamente; mantenha.
- `BREAKING CHANGE:` não deve aparecer: o contrato não pode mudar.

---

## 2. Regras de conteúdo

1. **Atômico:** um defeito por commit. O commit de correção contém **o teste que prova e a correção**.
2. **Coerente:** a suíte do commit não piora em relação ao anterior. Nada de "commit quebrado no meio".
3. **Sem mistura:** formatação (`style`) separada de lógica (`fix`), senão o diff da correção fica ilegível.
4. **Sem lixo:** nada de `output/*.json`, `.venv/`, `mutants/`, `.coverage`, `__pycache__/`.
5. **Arquivos protegidos intactos:** antes de commitar, `sha256sum -c .github/protected-files.sha256`.
6. **Histórico público é imutável:** nada de `--amend`, `rebase` ou `push --force` depois do push.
   Errou? Faça um novo commit corrigindo (ou `git revert`).
7. **Commits pequenos e frequentes** durante o trabalho; o PR agrupa o contexto.

Checklist antes de cada commit:

```bash
pytest -q && ruff check src tests && sha256sum -c .github/protected-files.sha256 && git diff --staged
```

---

## 3. Exemplos

### ✅ Bem escritos

```
fix(nights): usar diferença de datas em vez do dia do mês (RN-02)

calculate_room_nights subtraía checkout.day - checkin.day, o que só
funciona dentro do mesmo mês. Na virada (30/01 → 02/02) o resultado
era -28 noites em vez de 3, contaminando total_room_nights e a média.

Causa raiz: subtração de componentes do calendário em vez de subtração
de datas. Agora usa (checkout - checkin).days * rooms.

Prova: test_nights (fornecido) passa; test_properties cobre datas
aleatórias entre 2000 e 2100, incluindo virada de ano.

Refs: RN-02
Co-Authored-By: Claude <noreply@anthropic.com>
```

```
fix(reader): ler todas as linhas do CSV de reservas (RN-04)

O repositório interrompia a leitura após 200 linhas (`if len(rows) ==
200: break`). O dataset real tem 300 reservas, então 100 eram
descartadas em silêncio e todos os totais saíam subestimados.

Nenhum teste fornecido cobre esse caso: os CSVs de teste têm poucas
linhas. Detectado por ruff PLR2004 (número mágico) e pela cobertura de
ramos (linha do break nunca executada).

Prova: test_reader.py::test_reads_more_than_200_rows falhava com 200 e
passa com 250; oráculo diferencial no dataset real passa.

Refs: RN-04
```

```
fix(currency): multiplicar pela taxa em Decimal, sem float (RN-03, RN-05)

convert_to_brl tinha dois defeitos na mesma linha: dividia o valor
pela taxa (100 USD viravam 18,45 BRL em vez de 542,00) e convertia
para float no meio do cálculo, introduzindo erro binário de
representação em valores monetários.

Agora retorna amount * rates[currency], 100% Decimal.

Prova: test_currency (fornecido) passa; propriedade Hypothesis exige
igualdade exata com amount * rate; regra semgrep no-float-in-money
deixa de acusar.

Refs: RN-03, RN-05
```

```
test: adicionar oráculo diferencial sobre o dataset real

Reimplementação ingênua e independente das regras do README (não
importa nada de src/) comparada com o ReportBuilder em
reservas_hoteis.csv e exemplo-validacao.csv. Única verificação que
detecta os seis defeitos simultaneamente.
```

```
chore: material original do teste técnico ONFLY
```

```
style(report): aplicar ruff format em src/ sem alteração de lógica
```

### ❌ Mal escritos (e por quê)

| Mensagem | Problema |
|-|-|
| `fix bugs` | Vago, sem escopo, vários defeitos num commit |
| `Corrigido o cálculo.` | Particípio, maiúscula, ponto final, não diz qual cálculo |
| `wip` / `ajustes` / `asdf` | Não conta nada; não deve ir para o histórico público |
| `fix(currency): corrige conversão e formata arquivos e adiciona testes` | Três mudanças num commit |
| `test: altera test_currency para passar` | **Proibido**: os testes fornecidos não podem mudar |
| `fix: resolve tudo que a IA sugeriu` | Sem causa, sem prova, sem autoria crítica |

---

## 4. Histórico-alvo do projeto

```
chore: material original do teste técnico ONFLY
docs: adicionar CLAUDE.md, plano técnico e convenção de commits
chore(tooling): configurar ruff, mypy, coverage e pre-commit
ci: adicionar pipeline de qualidade e verificação de arquivos protegidos
style: aplicar ruff format em src/ sem alteração de lógica
test(reader): reproduzir leitura truncada em 200 linhas (RN-04)
fix(reader): ler todas as linhas do CSV de reservas (RN-04)
fix(status): considerar faturável somente CONFIRMED (RN-01)
fix(nights): usar diferença de datas em vez do dia do mês (RN-02)
fix(currency): multiplicar pela taxa em Decimal, sem float (RN-03, RN-05)
fix(ranking): ordenar por total desc com desempate por hotel_id (RN-08)
test: adicionar propriedades Hypothesis para RN-01 a RN-05
test: adicionar oráculo diferencial sobre o dataset real
test(cli): cobrir contrato do JSON, exit codes e --top (RN-10 a RN-12)
fix(cli): retornar exit 2 para moeda sem taxa de câmbio (RN-11)
refactor(types): tipar ReportBuilder para mypy --strict
docs(entrega): adicionar README-ENTREGA e declaração de uso de IA
```

> `test(reader)` antes de `fix(reader)` é opcional: mostra explicitamente o teste vermelho no
> histórico. Para os demais defeitos, teste e correção vão no mesmo commit.

---

## 5. Branches

| Prefixo | Uso | Exemplo |
|-|-|-|
| `main` | Sempre verde; só recebe PR | — |
| `chore/` | Tooling e configuração | `chore/tooling-qualidade` |
| `fix/` | Correções de defeitos | `fix/defeitos-relatorio` |
| `test/` | Testes avançados | `test/propriedades-e-oraculo` |
| `docs/` | Documentação e entrega | `docs/entrega` |

Nomes em minúsculas, com hífen, descritivos.

---

## 6. Pull Requests

**Título:** mesmo formato do commit (`fix: corrigir defeitos D1–D6 do relatório`).

**Descrição (modelo):**

```markdown
## Contexto
O que este PR resolve e por quê.

## Mudanças
| Defeito | Regra | Causa raiz | Teste que prova |
|-|-|-|-|
| D2 | RN-02 | subtração de .day em vez de datas | test_nights, test_properties |

## Como validar
pytest -q
PYTHONPATH=src python -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json

## Checklist
- [ ] CI verde
- [ ] Arquivos protegidos intactos (checksum)
- [ ] Contrato do JSON inalterado
- [ ] Commits seguem docs/CONVENCAO-COMMITS.md
```

**Regras:**
- CI verde é obrigatório para o merge (proteção de branch em *Settings → Branches*).
- Revisão por IA (CodeRabbit ou Copilot) é bem-vinda: **responda** cada comentário (aceito/recusado e por quê).
- Merge com **“Create a merge commit”** ou **“Rebase and merge”**. **Não use squash**: ele apaga os
  commits atômicos que documentam a investigação.
- Apague a branch após o merge.

---

## 7. Release final

Ao concluir a entrega:

```bash
git tag -a v1.0.0 -m "Entrega do teste técnico ONFLY: defeitos D1–D6 corrigidos"
git push origin v1.0.0
```

Depois crie uma *Release* no GitHub a partir da tag, com o resumo do `README-ENTREGA.md`.

---

## 8. Validação automática (opcional)

Hook `commit-msg` local que rejeita mensagens fora do padrão. Salve em `.git/hooks/commit-msg` e
rode `chmod +x .git/hooks/commit-msg`:

```bash
#!/usr/bin/env bash
subject=$(head -n1 "$1")
pattern='^(feat|fix|test|refactor|perf|docs|chore|ci|build|style|revert)(\([a-z0-9-]+\))?!?: [^A-Z].{1,70}[^.]$'
if ! grep -qP "$pattern" <<< "$subject" && ! grep -qE '^Merge ' <<< "$subject"; then
  echo "✖ Mensagem fora do padrão (docs/CONVENCAO-COMMITS.md):"
  echo "  $subject"
  echo "  Esperado: tipo(escopo): descrição no imperativo, minúscula, sem ponto final"
  exit 1
fi
```

Validado contra os exemplos: aceita `fix(nights): usar diferença de datas… (RN-02)` e
`chore: material original…`; rejeita `Fixed bug.` e `fix: Corrige`.
