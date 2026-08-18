#!/usr/bin/env python3
"""Depois do PDF aprovado, deixa só o PDF na pasta da aula.

    python3 fechar_aula.py --dir aulas/<disciplina>/aula-NN-<slug>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def erro(msg: str) -> None:
    print(f"ERRO: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Mantém só o PDF na pasta da aula.")
    ap.add_argument("--dir", required=True, type=Path)
    args = ap.parse_args()
    d = args.dir
    if not d.is_dir():
        erro(f"diretório não encontrado: {d}")

    pdfs = sorted(p for p in d.glob("*.pdf") if p.is_file() and p.stat().st_size > 0)
    if not pdfs:
        erro(f"nenhum PDF em {d} — não apago as fontes")

    apagados = []
    for p in d.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() == ".pdf":
            continue
        p.unlink()
        apagados.append(p.name)

    print(f"aula fechada: {d}")
    print(f"  pdf ........... {', '.join(p.name for p in pdfs)}")
    print(f"  removidos ..... {', '.join(apagados) if apagados else 'nada'}")


if __name__ == "__main__":
    main()
