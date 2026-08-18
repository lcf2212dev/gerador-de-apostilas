#!/usr/bin/env python3
"""Mede o corpo da aula: tempo de estudo e qualidade didática.

O tempo NUNCA vai para a apostila impressa: serve para dimensionar a redação.

Uso:
    python3 estimar_tempo.py corpo.html [--alvo 30]
    python3 estimar_tempo.py --alvo 30 --orcamento   # quantas palavras cabem no alvo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    MAX_MINUTOS,
    MIN_MINUTOS,
    PALAVRAS_POR_UNIDADE,
    PPM,
    RESERVA_ELEMENTOS_MIN,
    analisar_corpo,
    estimar_minutos,
    palavras_para_minutos,
    revisar_didatica,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Mede tempo e qualidade didática do corpo da aula.")
    ap.add_argument("corpo", nargs="?", type=Path, help="caminho de corpo.html")
    ap.add_argument("--alvo", type=float, help="duração-alvo em minutos")
    ap.add_argument("--orcamento", action="store_true",
                    help="mostra o orçamento de palavras do alvo e sai")
    args = ap.parse_args()

    if args.orcamento:
        alvo = args.alvo or 30.0
        palavras = palavras_para_minutos(alvo)
        print(f"alvo {alvo:g} min -> ~{palavras} palavras de corpo "
              f"(a {PPM} palavras/min, já reservando ~{RESERVA_ELEMENTOS_MIN:g} min "
              "para caixas, exemplos e checkpoints)")
        print(f"cabe, com tratamento didático completo, algo em torno de "
              f"{max(1, round(palavras / PALAVRAS_POR_UNIDADE))} unidades de conteúdo")
        return

    if not args.corpo:
        ap.error("informe o caminho de corpo.html (ou use --orcamento)")
    if not args.corpo.exists():
        print(f"ERRO: arquivo não encontrado: {args.corpo}", file=sys.stderr)
        raise SystemExit(1)

    analise = analisar_corpo(args.corpo.read_text(encoding="utf-8"))
    tempo = estimar_minutos(analise)
    c = analise["contagem"]

    print(f"palavras ............ {analise['palavras']}")
    print(f"seções .............. {c['secao']}")
    print(f"exemplos ............ {c['exemplo']}")
    print(f"passo-a-passo ....... {c['passo_a_passo']}")
    print(f"em outras palavras .. {c['em_outras_palavras']}")
    print(f"caixas .............. {c['box']}")
    print(f"tabelas ............. {c['tabela']}")
    print(f"pare-e-responda ..... {c['pare_responda']}")
    print(f"checkpoints ......... {c['checkpoint']}")
    print(f"leitura ............. {tempo['leitura']} min")
    print(f"elementos ........... {tempo['extras']} min")
    print(f"TOTAL ............... {tempo['total']} min")

    didatica = revisar_didatica(analise)
    if didatica:
        print("\nrevisão didática:")
        for d in didatica:
            print(f"  · {d}")
    else:
        print("\nrevisão didática: sem apontamentos")

    alvo = args.alvo
    if alvo and abs(tempo["total"] - alvo) / alvo > 0.15:
        delta = (alvo - tempo["total"]) * PPM
        verbo = "acrescente" if delta > 0 else "corte"
        print(f"\naviso: {tempo['total']} min contra alvo de {alvo:g} min — "
              f"{verbo} ~{abs(int(delta))} palavras", file=sys.stderr)

    if not tempo["dentro_da_faixa"]:
        print(f"ERRO: fora da faixa obrigatória de {MIN_MINUTOS}–{MAX_MINUTOS} min",
              file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
