# Declaração de uso de IA

## Ferramentas

- **Claude Desktop (Claude Opus 5.5):** análise do enunciado e preparação dos prompts.
- **Claude Code (Claude Opus 5.5):** execução no repositório. A sessão exportada nesta pasta (`sessao.md`) é dele.

## O que a IA fez

- Diagnosticou os defeitos, com um oráculo independente das regras do README.
- Escreveu os testes novos e as correções, seguindo TDD com um commit por defeito.
- Rodou pytest, ruff, cobertura e checksum dos arquivos protegidos, e redigiu as mensagens de commit e os
  documentos da entrega.
- Na revisão final, corrigiu o defeito 7 (moeda sem taxa → exit 2), completou a anonimização do script de
  exportação, regerou a sessão e alinhou a documentação com o que foi implementado.

## O que eu fiz

- Preparei o `CLAUDE.md` e as regras do projeto (convenção de commits, arquivos protegidos e permissões).
- Decidi a ordem e o escopo das correções, incluindo o que ficou como melhoria futura.
- Revisei e aprovei cada bloco de commits.
- Conferi a validação final.

## Sessões

O README pede a exportação das sessões. Esta é a relação completa do uso de IA; só a sessão principal, com todo o
trabalho técnico das correções, foi exportada.

| Sessão | Quando (fuso -03:00) | Exportada? | Conteúdo |
|-|-|-|-|
| Claude Desktop | antes do trabalho no repositório | Não | Análise do enunciado e preparação dos prompts. |
| Claude Code, exploratória | 12/11/2026, 20:38–20:54 | Não | Entender o projeto e escrever o script de exportação anonimizada (`tools/exportar_sessoes.py`, commitado depois em `fbd2417`) e o ajuste do `.gitignore`. Ficou fora da exportação pelo `.sessoes-ignoradas.local`. |
| Claude Code, principal | 15/11/2026, 21:51–22:46 | **Sim**: `sessao.md` | Commits de `17ae94a` a `6e333ec`: configuração, correções 1 a 6, testes e documentos da entrega. |
| Claude Code, conferência | 15/11/2026, 22:51–22:53 | Não | Só leitura: rodou os testes e conferiu a entrega, sem alterar arquivos. |
| Claude Code, publicação | 15/11/2026, 22:54–22:57 | Não | Commit `344efd5` (a exportação da sessão principal) e a primeira publicação no GitHub. |
| Claude Code, revisão final | 15/11/2026, a partir das 22:59 | Não | Merge do PR #1, correção 7 (PR #2) e PR #3: anonimização do script, sessão regerada, permissões e documentação. |

A anonimização da sessão remove dados de conta e do computador (nome de usuário, e-mails, IDs e caminhos locais).
A autoria do trabalho é minha e está identificada no plano técnico e nos commits.
