#!/usr/bin/env python3
"""Estado da apostila: cruza o grade.json do sumário com o que existe no disco.

Uma aula fechada deixa só o PDF na pasta. Enquanto as fontes ainda estão no
disco, a aula é parcial (produção ou review). HTML sozinho não conta.

    progresso.py sumarios/<slug>                      # tabela: uma linha por aula
    progresso.py sumarios/<slug> --pendentes --limite 16   # próximos seqs a despachar
    progresso.py sumarios/<slug> --pendentes --limite 16 --json  # com slug e diretório

A regra do slug e do diretório vem de contexto_aula.py (skill `apostila`), importado
como módulo — nada de nome de aula é recalculado aqui.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

FONTES = ["meta.json", "corpo.html", "questoes.json", "videos.json", "flashcards.json"]


def importar_contexto():
    caminho = Path(__file__).resolve().parents[2] / "apostila" / "scripts" / "contexto_aula.py"
    spec = importlib.util.spec_from_file_location("contexto_aula", caminho)
    if spec is None or spec.loader is None:
        print(f"ERRO: não encontrei {caminho}", file=sys.stderr)
        raise SystemExit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def nao_vazio(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0


def estado_da_aula(base: Path, slug: str) -> tuple[str, list, str]:
    """→ (status, falta, detalhe). status: pronta | parcial | pendente | CONFLITO."""
    d = base / slug
    if d.is_dir():
        pdfs = [p for p in d.glob("*.pdf") if nao_vazio(p)]
        outros = [p.name for p in d.iterdir() if p.is_file() and p.suffix.lower() != ".pdf"]
        if pdfs and not outros:
            return ("pronta", [], "")
        falta = [f for f in FONTES if not nao_vazio(d / f)]
        if not nao_vazio(d / f"{slug}.html"):
            falta.append("html")
        if not pdfs:
            falta.append("pdf")
        return ("parcial", falta, "")
    prefixo = slug.split("-", 2)
    prefixo = f"{prefixo[0]}-{prefixo[1]}-"          # "aula-NN-"
    outros = sorted(p.name for p in base.glob(prefixo + "*") if p.is_dir()) if base.is_dir() else []
    if outros:
        return ("CONFLITO", [], f"{prefixo}* existe com outro slug: {', '.join(outros)}")
    return ("pendente", [], "")


def main() -> None:
    ap = argparse.ArgumentParser(description="Estado da apostila: grade.json × filesystem.")
    ap.add_argument("alvo", type=Path, help="sumarios/<slug>, plano.json ou grade.json")
    ap.add_argument("--aulas-dir", type=Path, default=Path("aulas"),
                    help="raiz das aulas (padrão: aulas)")
    ap.add_argument("--pendentes", action="store_true",
                    help="só as aulas a despachar (pendentes e parciais), na ordem da grade")
    ap.add_argument("--limite", type=int, help="máximo de aulas em --pendentes")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args()

    mod = importar_contexto()
    plano, grade = mod.carregar(args.alvo)
    if not (grade and grade.get("aulas")):
        print(f"ERRO: não há grade.json com 'aulas' a partir de {args.alvo} — "
              "rode a skill montar-sumario antes.", file=sys.stderr)
        raise SystemExit(1)

    itens = plano["itens"]
    grafo = plano.get("grafo") or {}
    disciplina = grade.get("assunto") or grafo.get("escopo") \
        or (plano.get("assunto") or {}).get("rotulo") or "Estudo"
    base = args.aulas_dir / mod.slugificar(disciplina)

    curva = (plano.get("cobertura") or {}).get("curva") or []
    acum_por_num = {str(c.get("num")): c.get("acumulado") for c in curva}

    linhas = []
    for aula in sorted(grade["aulas"], key=lambda a: a.get("seq") or 0):
        item = mod.item_do_plano(itens, num=aula.get("item")) or {}
        titulo = aula.get("titulo") or item.get("rotulo") or "Aula"
        numero = int(aula.get("seq") or 0)
        slug = f"aula-{numero:02d}-{mod.slugificar(item.get('rotulo') or titulo)}"
        status, falta, detalhe = estado_da_aula(base, slug)
        linhas.append({
            "seq": numero, "status": status, "slug": slug,
            "dir": str(base / slug), "falta": falta, "detalhe": detalhe,
            "titulo": titulo, "minutos": int(aula.get("minutos") or 30),
            "item": str(aula.get("item")),
            "acumulado": acum_por_num.get(str(aula.get("item"))),
        })

    # Cobertura acumulada: maior prefixo da fila cujos itens têm todas as aulas prontas.
    prontos_por_item: dict[str, bool] = {}
    for ln in linhas:
        prontos_por_item[ln["item"]] = prontos_por_item.get(ln["item"], True) \
            and ln["status"] == "pronta"
    cobertura = 0.0
    for c in curva:
        if prontos_por_item.get(str(c.get("num"))):
            cobertura = c.get("acumulado") or cobertura
        else:
            break

    if args.pendentes:
        fila = [ln for ln in linhas if ln["status"] in ("pendente", "parcial")]
        if args.limite:
            fila = fila[:args.limite]
        if args.json:
            print(json.dumps(fila, ensure_ascii=False, indent=2))
        else:
            print(" ".join(str(ln["seq"]) for ln in fila))
        return

    conta = {s: sum(1 for ln in linhas if ln["status"] == s)
             for s in ("pronta", "parcial", "pendente", "CONFLITO")}
    horas = sum(ln["minutos"] for ln in linhas if ln["status"] == "pronta") / 60

    if args.json:
        print(json.dumps({"disciplina": disciplina, "destino": str(base),
                          "aulas": linhas, "resumo": conta,
                          "horas_prontas": round(horas, 2),
                          "cobertura_acumulada": round(cobertura, 4)},
                         ensure_ascii=False, indent=2))
        return

    print(f"apostila: {disciplina} — {args.alvo}")
    print(f"destino:  {base}")
    print(f" seq  status    {'falta':<34} diretório")
    for ln in linhas:
        falta = " ".join(ln["falta"]) if ln["falta"] else "—"
        resto = ln["detalhe"] if ln["status"] == "CONFLITO" else ln["slug"]
        print(f" {ln['seq']:>3}  {ln['status']:<9} {falta:<34} {resto}")
    partes = [f"{len(linhas)} aulas", f"{conta['pronta']} prontas",
              f"{conta['parcial']} parciais", f"{conta['pendente']} pendentes"]
    if conta["CONFLITO"]:
        partes.append(f"{conta['CONFLITO']} conflitos")
    print(" · ".join(partes))
    h = f"{horas:.1f}".replace(".", ",")
    print(f"{h} h prontas · cobertura acumulada {cobertura * 100:.1f}%".replace(".", ","))


if __name__ == "__main__":
    main()
