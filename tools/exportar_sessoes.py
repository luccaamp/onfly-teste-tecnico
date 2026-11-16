"""Exporta as sessões do Claude Code deste projeto para Markdown anonimizado.

Uso (na raiz do projeto):
    python tools/exportar_sessoes.py

Gera entrega/uso-de-ia/sessao-NN.md, uma por sessão, em ordem cronológica.

O que é removido/mascarado:
- metadados da conta (UUIDs, IDs de sessão, e-mail, organização);
- lembretes de sistema e contexto injetado pela ferramenta;
- raciocínio interno do modelo (só ficam prompts, respostas e chamadas de ferramenta);
- caminhos do computador: home do usuário, diretório do projeto e pastas temporárias;
- nome de usuário do sistema operacional, qualquer e-mail e os termos listados em
  `.redact-terms.local` (um por linha; arquivo ignorado pelo git, nunca é publicado).

Ao final o script relê cada arquivo gerado e aborta se sobrar qualquer termo sensível.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "entrega" / "uso-de-ia"
TERMS_FILE = PROJECT_ROOT / ".redact-terms.local"
# IDs de sessões que não entram na entrega (ex.: sessões de configuração); um por linha.
IGNORED_FILE = PROJECT_ROOT / ".sessoes-ignoradas.local"
MAX_RESULT_LINES = 80

# Também pega e-mail truncado (sem ".com") e com partes já mascaradas (<usuario>.dev@...).
EMAIL_RE = re.compile(r"[\w.+<>-]+@[\w-]+(?:\.[\w-]+)*")
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
SYSTEM_BLOCK_RE = re.compile(
    r"<(system-reminder|ide_selection|ide_opened_file)>.*?</\1>", re.S
)


def sessions_dir() -> Path:
    encoded = re.sub(r"[^A-Za-z0-9]", "-", str(PROJECT_ROOT))
    candidates = [
        p
        for p in (Path.home() / ".claude" / "projects").glob("*")
        if p.name.lower() == encoded.lower()
    ]
    if not candidates:
        sys.exit(f"pasta de sessões não encontrada para o projeto ({encoded})")
    return candidates[0]


def path_pattern(path: Path) -> re.Pattern[str]:
    """Casa o caminho em qualquer grafia: C:\\x, c:/x, /c/x e com barras escapadas (\\\\, \\\\\\\\)."""
    parts = [p for p in re.split(r"[\\/]+", str(path)) if p]
    drive, rest = parts[0], parts[1:]
    if drive.endswith(":"):
        letter = re.escape(drive[0])
        head = rf"(?:{letter}:|(?<![\w.])/{letter}(?=[\\/]))"
    else:
        head = re.escape(drive)
    sep = r"[\\/]+"
    return re.compile(head + "".join(sep + re.escape(p) for p in rest) + r"(?![\w-])", re.I)


def build_redactor() -> tuple[list[tuple[re.Pattern[str], str]], list[str]]:
    rules: list[tuple[re.Pattern[str], str]] = []
    sensitive: list[str] = []

    def add_literal(text: str, label: str) -> None:
        if text and len(text) >= 3:
            rules.append((re.compile(re.escape(text), re.I), label))
            sensitive.append(text)

    temp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or "")
    for base, label in ((temp, "<temp>"), (PROJECT_ROOT, "<projeto>"), (Path.home(), "<home>")):
        if str(base) not in ("", "."):
            rules.append((path_pattern(base), label))
    add_literal(sessions_dir().name, "<pasta-sessoes>")
    rules.append((EMAIL_RE, "<email>"))
    rules.append((UUID_RE, "<id>"))

    terms: list[str] = []
    if TERMS_FILE.exists():
        terms = [t.strip() for t in TERMS_FILE.read_text(encoding="utf-8").splitlines() if t.strip()]
    terms.append(getpass.getuser())
    for term in sorted(set(terms), key=len, reverse=True):
        add_literal(term, "<usuario>")
    return rules, sensitive


def redact(text: str, rules: list[tuple[re.Pattern[str], str]]) -> str:
    for pattern, label in rules:
        text = pattern.sub(label, text)
    return text


def clean_user_text(text: str) -> str:
    return SYSTEM_BLOCK_RE.sub("", text).strip()


def truncate(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= MAX_RESULT_LINES:
        return text
    omitted = len(lines) - MAX_RESULT_LINES
    return "\n".join(lines[:MAX_RESULT_LINES] + [f"... ({omitted} linhas omitidas)"])


def result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def fence(text: str, lang: str = "") -> str:
    ticks = "````" if "```" in text else "```"
    return f"{ticks}{lang}\n{text}\n{ticks}"


def render_session(path: Path) -> tuple[str, str]:
    parts: list[str] = []
    first_ts = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        kind = entry.get("type")
        if kind not in ("user", "assistant") or entry.get("isSidechain"):
            continue
        first_ts = first_ts or entry.get("timestamp", "")
        content = entry.get("message", {}).get("content", [])
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for block in content:
            btype = block.get("type")
            if kind == "user" and btype == "text":
                text = clean_user_text(block.get("text", ""))
                if text:
                    parts.append(f"### Usuário\n\n{text}")
            elif kind == "user" and btype == "tool_result":
                text = truncate(result_text(block.get("content")).strip())
                if text:
                    parts.append(f"Resultado:\n\n{fence(text)}")
            elif kind == "assistant" and btype == "text" and block.get("text", "").strip():
                parts.append(f"### Assistente\n\n{block['text'].strip()}")
            elif kind == "assistant" and btype == "tool_use":
                args = json.dumps(block.get("input", {}), ensure_ascii=False, indent=2)
                parts.append(f"Chamada de ferramenta: `{block.get('name')}`\n\n{fence(truncate(args), 'json')}")
    return first_ts, "\n\n".join(parts)


def main() -> int:
    rules, sensitive = build_redactor()
    ignored: set[str] = set()
    if IGNORED_FILE.exists():
        ignored = {s.strip() for s in IGNORED_FILE.read_text(encoding="utf-8").splitlines() if s.strip()}
    sessions = [p for p in sessions_dir().glob("*.jsonl") if p.stem not in ignored]
    rendered = [render_session(p) for p in sessions]
    rendered = sorted((r for r in rendered if r[1]), key=lambda r: r[0])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index, (ts, body) in enumerate(rendered, start=1):
        header = (
            f"# Sessão {index:02d}\n\n"
            "| Campo | Valor |\n|-|-|\n"
            "| Ferramenta | Claude Code |\n"
            f"| Data | {ts[:10]} |\n"
            "| Observação | Exportação anonimizada: identidade, caminhos locais e metadados de conta removidos; "
            f"saídas de ferramentas limitadas a {MAX_RESULT_LINES} linhas. |\n"
        )
        text = redact(f"{header}\n{body}\n", rules)
        leaks = [s for s in sensitive if s.lower() in text.lower()]
        leaks += [m.group() for pattern, _ in rules for m in pattern.finditer(text)]
        if leaks:
            sys.exit(f"sessão {index:02d}: termo sensível remanescente, nada gravado")
        out = OUTPUT_DIR / f"sessao-{index:02d}.md"
        out.write_text(text, encoding="utf-8")
        print(f"gravado: {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
