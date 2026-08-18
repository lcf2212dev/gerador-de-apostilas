#!/usr/bin/env python3
"""Gera QR codes SVG para as URLs recebidas. Imprime {url: svg} em JSON.

Chamado por montar.py, primeiro com o Python do sistema e, se segno não estiver
instalado, via `uv run --with segno`. Falha silenciosa é aceitável: sem QR, a
apostila imprime apenas a URL curta.
"""

import io
import json
import sys

try:
    import segno
except ImportError:
    sys.exit(3)

AZUL = "#0B3C5D"


def svg(url: str) -> str:
    """SVG sem width/height fixos: o tamanho vem do CSS (.video .qr svg)."""
    qr = segno.make(url, error="m")
    buf = io.BytesIO()
    try:
        qr.save(buf, kind="svg", xmldecl=False, svgns=True, omitsize=True,
                border=2, dark=AZUL, svgclass=None, lineclass=None)
    except TypeError:
        buf = io.BytesIO()
        qr.save(buf, kind="svg", xmldecl=False, border=2, dark=AZUL)
    return buf.getvalue().decode("utf-8").strip()


def main() -> None:
    urls = sys.argv[1:]
    if not urls:
        print("{}")
        return
    print(json.dumps({u: svg(u) for u in urls}, ensure_ascii=False))


if __name__ == "__main__":
    main()
