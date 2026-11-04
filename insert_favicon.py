#!/usr/bin/env python3
"""
Insere favicon + meta description em todo template HTML do projeto.
Roda uma vez na raiz do repo: python3 insert_favicon.py
Idempotente: pode rodar de novo sem duplicar.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__"}

FAVICON_BLOCK = """    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon/favicon-16x16.png">
    <link rel="icon" href="/static/favicon/favicon.ico">
    <link rel="apple-touch-icon" sizes="180x180" href="/static/favicon/apple-touch-icon.png">
    <meta name="description" content="comenta EU QUERO — automação de comentários e DM no Instagram. Comentário, story e mensagem direta viram resposta automática no direct, com editor de fluxos visual.">
"""

MARKER = "<!-- favicon-auto -->"

def process(path: Path):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    match = re.search(r"<head[^>]*>", text, re.IGNORECASE)
    if not match:
        return False
    insert_at = match.end()
    new_text = text[:insert_at] + "\n" + MARKER + "\n" + FAVICON_BLOCK + text[insert_at:]
    path.write_text(new_text, encoding="utf-8")
    return True

def main():
    changed = []
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in (".html", ".htm"):
            continue
        if "<head" not in path.read_text(encoding="utf-8", errors="ignore").lower():
            continue
        if process(path):
            changed.append(str(path.relative_to(ROOT)))
    if changed:
        print("Arquivos atualizados:")
        for c in changed:
            print(" -", c)
    else:
        print("Nenhum arquivo <head> encontrado fora dos já atualizados (ou já tinham o marcador).")

if __name__ == "__main__":
    main()
