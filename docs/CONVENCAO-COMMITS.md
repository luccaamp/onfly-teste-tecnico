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
| `fix` | Corrige comportamento divergente do README (D1–D7) |
| `test` | Adiciona/ajusta **testes novos** (nunca os fornecidos) |
| `chore` | Tooling, configuração, `.gitignore`, dependências de dev |
| `docs` | README, `entrega/`, `docs/`, `CLAUDE.md` |
| `style` | Somente formatação (ex.: `ruff format src`), sem lógica |
| `feat` | **Evitar.** O desafio não pede funcionalidade nova |

### 1.3 Escopos

Use o componente afetado: `reader`, `status`, `nights`, `currency`, `ranking`, `report`, `cli`,
`tooling`, `entrega`. Omita o escopo quando a mudança for transversal.

### 1.4 Corpo

Obrigatório em todo `fix` e em qualquer commit não óbvio. Responde a três perguntas:

1. **Qual era o problema?** Sintoma observável, com exemplo concreto se possível.
2. **Por que acontecia?** Causa raiz em uma frase.
3. **Como foi provado?** Qual teste falhava antes e passa agora.

Não descreva o diff linha a linha; o diff já mostra isso.

### 1.5 Rodapé (trailers)

```
Refs: RN-02
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
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
4. **Sem lixo:** nada de `output/*.json`, `.venv/`, `.coverage`, `__pycache__/`.
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

Prova: test_stay_calculator falhava e passa; test_nights (fornecido)
passa.

Refs: RN-02
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

```
fix(reader): ler todas as linhas do CSV de reservas (RN-04)

O repositório interrompia a leitura após 200 linhas (`if len(rows) ==
200: break`). O dataset real tem 300 reservas, então 100 eram
descartadas em silêncio e todos os totais saíam subestimados.

Nenhum teste fornecido cobre esse caso: os CSVs de teste têm poucas
linhas. Detectado comparando o relatório com um cálculo independente
das regras do README sobre o CSV real.

Prova: test_reservation_repository falhava e passa.

Refs: RN-04
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

```
fix(currency): multiplicar o valor pela taxa em vez de dividir (RN-03)

convert_to_brl dividia o valor pela taxa (100 USD viravam 18,45 BRL
em vez de 542,00).

Prova: test_currency_converter falhava e passa; test_currency
(fornecido) passa.

Refs: RN-03
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

```
chore: importa projeto original do teste técnico
```

```
style(report): aplicar ruff format em report_builder.py
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

## 4. Histórico do projeto

```
chore: importa projeto original do teste técnico
chore: ignora arquivos locais de configuração
chore: adiciona configuração e documentação para uso de ia
chore(tooling): adiciona script de exportação anonimizada das sessões de ia
fix(status): considerar faturável somente CONFIRMED (RN-01)
fix(nights): usar diferença de datas em vez do dia do mês (RN-02)
fix(currency): multiplicar o valor pela taxa em vez de dividir (RN-03)
fix(currency): converter em Decimal exato, sem passar por float (RN-05)
fix(ranking): ordenar top_hotels por total decrescente e hotel_id crescente (RN-08)
fix(reader): ler todas as linhas do CSV de reservas (RN-04)
style(report): aplicar ruff format em report_builder.py
chore(tooling): adicionar pytest-cov às dependências de dev
test(report): validar amostra do README e contrato do relatório
test(cli): cobrir códigos de saída 0, 1 e 2 do CLI
docs(entrega): adicionar README-ENTREGA com defeitos e validação
docs(entrega): adicionar declaração de uso de IA
docs(entrega): adicionar exportação anonimizada da sessão de IA
Merge pull request #1 from luccaamp/fix/defeitos-relatorio
fix(currency): retornar exit 2 para moeda sem taxa de câmbio (RN-11)
Merge pull request #2 from luccaamp/fix/moeda-sem-taxa
chore: remover permissões de ferramentas não usadas
fix(tooling): completar a anonimização da exportação de sessões
docs(entrega): regerar a sessão de IA com a anonimização corrigida
docs: alinhar documentação com o que foi implementado
Merge pull request #3 from luccaamp/docs/revisao-final
```

Teste e correção vão no mesmo commit `fix`.

> Os quatro primeiros commits (importação e configuração) foram escritos no presente
> (`importa`, `ignora`, `adiciona`) e entraram direto na `main` (dois commitados nela e dois por
> merge local fast-forward de `chore/setup-ia`), antes de as regras do imperativo e do fluxo por PR
> serem aplicadas. Eles não foram reescritos porque a sessão exportada em `entrega/uso-de-ia/` cita
> os hashes deles. Das correções em diante, tudo segue a convenção e entrou por PR.

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

**Título:** mesmo formato do commit (`fix: corrigir defeitos do relatório onfly_report`).

**Descrição (modelo):**

```markdown
## Contexto
O que este PR resolve e por quê.

## Mudanças
| Defeito | Regra | Causa raiz | Teste que prova |
|-|-|-|-|
| D2 | RN-02 | subtração de .day em vez de datas | test_nights, test_stay_calculator |

## Como validar
pytest -q
PYTHONPATH=src python -m onfly_report --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv --output output/exemplo.json

## Checklist
- [ ] `pytest -q` e `ruff check src tests` passando
- [ ] Arquivos protegidos intactos (checksum)
- [ ] Contrato do JSON inalterado
- [ ] Commits seguem docs/CONVENCAO-COMMITS.md
```

**Regras:**
- Merge com **“Create a merge commit”**. **Não use squash**: ele apaga os commits atômicos que
  documentam a investigação.

