#!/usr/bin/env python3
"""Extrai o briefing de uma aula a partir do sumário de estudo (skill `montar-sumario`).

Quando existe um plano, é ele que manda: tema, duração, título, objetivo e pré-requisitos
já foram decididos a partir do grafo de incidência. A apostila não redecide nada disso —
só escreve a aula.

    contexto_aula.py sumarios/<slug> --aula 3            # via grade.json (preferido)
    contexto_aula.py sumarios/<slug>/plano.json --seq 3  # só o plano, sem grade
    contexto_aula.py sumarios/<slug> --aula 3 --meta > meta.json

Sem sumário nenhum, a skill apostila dimensiona sozinha (references/orcamento-de-tempo.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ESTILOS_BANCA = {
    "cebraspe": "cebraspe-ce", "cespe": "cebraspe-ce",
    "ibfc": "A-D", "aocp": "A-D", "avanca": "A-D",
}


def slugificar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", str(texto).lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", sem_acento)).strip("-")[:60]


def estilo_da_banca(bancas) -> str:
    for b in bancas or []:
        chave = str(b).lower()
        for marca, estilo in ESTILOS_BANCA.items():
            if marca in chave:
                return estilo
    return "A-E"


def ler_json(caminho: Path) -> dict | None:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"ERRO: JSON inválido em {caminho}: {e}", file=sys.stderr)
        raise SystemExit(1)


def carregar(alvo: Path) -> tuple[dict, dict | None]:
    """Aceita o diretório do sumário, o plano.json ou o grade.json."""
    if alvo.is_dir():
        plano = ler_json(alvo / "plano.json")
        grade = ler_json(alvo / "grade.json")
    elif alvo.name == "grade.json":
        grade = ler_json(alvo)
        caminho_plano = Path((grade or {}).get("plano") or (alvo.parent / "plano.json"))
        plano = ler_json(caminho_plano) or ler_json(alvo.parent / "plano.json")
    else:
        plano = ler_json(alvo)
        grade = ler_json(alvo.parent / "grade.json")

    if not plano or not plano.get("itens"):
        print(f"ERRO: não encontrei um plano.json com 'itens' a partir de {alvo}", file=sys.stderr)
        raise SystemExit(1)
    return plano, grade


def item_do_plano(itens: list, num=None, seq=None, ident=None) -> dict | None:
    for i in itens:
        if num is not None and str(i.get("num")) == str(num):
            return i
        if seq is not None and i.get("seq") == seq:
            return i
        if ident and str(i.get("id")) == str(ident):
            return i
    if ident:
        alvo = slugificar(ident)
        for i in itens:
            if alvo and alvo in slugificar(i.get("rotulo", "")):
                return i
    return None


def rotulos(itens: list, ids) -> list:
    mapa = {i.get("id"): i.get("rotulo", i.get("id")) for i in itens}
    return [mapa.get(x, x) for x in (ids or [])]


def listar(plano: dict, grade: dict | None) -> None:
    if grade and grade.get("aulas"):
        print("aulas disponíveis (--aula N):", file=sys.stderr)
        for a in grade["aulas"][:40]:
            print(f"  {a.get('seq')} · item {a.get('item')} · {a.get('minutos')} min · "
                  f"{a.get('titulo')}", file=sys.stderr)
    else:
        print("itens disponíveis (--seq N | --num X | --id ID):", file=sys.stderr)
        for i in plano["itens"][:40]:
            print(f"  seq {i.get('seq')} · num {i.get('num')} · {i.get('rotulo')}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Briefing de uma aula a partir do sumário de estudo.")
    ap.add_argument("alvo", type=Path, help="sumarios/<slug>, plano.json ou grade.json")
    ap.add_argument("--aula", type=int, help="seq da aula no grade.json")
    ap.add_argument("--seq", type=int, help="seq do item no plano.json")
    ap.add_argument("--num", help="número do item no plano (ex.: 5.1)")
    ap.add_argument("--id", dest="ident", help="id ou rótulo do tópico")
    ap.add_argument("--parte", type=int, default=1,
                    help="qual fatia, quando o item virou várias aulas e não há grade")
    ap.add_argument("--numero", type=int, help="número da aula na apostila (padrão: a seq da aula)")
    ap.add_argument("--meta", action="store_true", help="emite um meta.json inicial")
    ap.add_argument("--json", action="store_true", help="emite o briefing completo em JSON")
    ap.add_argument("--listar", action="store_true", help="lista as aulas ou itens disponíveis")
    args = ap.parse_args()

    plano, grade = carregar(args.alvo)
    itens = plano["itens"]

    if args.listar:
        listar(plano, grade)
        return
    if not any((args.aula, args.seq, args.num, args.ident)):
        ap.error("informe --aula (com grade.json), --seq, --num ou --id; ou use --listar")

    aula_grade, item, parte, total_partes = None, None, args.parte, 1

    if args.aula is not None:
        if not (grade and grade.get("aulas")):
            print("ERRO: --aula exige um grade.json; use --seq/--num sobre o plano.",
                  file=sys.stderr)
            raise SystemExit(1)
        aula_grade = next((a for a in grade["aulas"] if a.get("seq") == args.aula), None)
        if not aula_grade:
            print(f"ERRO: aula {args.aula} não existe no grade.json.", file=sys.stderr)
            listar(plano, grade)
            raise SystemExit(1)
        item = item_do_plano(itens, num=aula_grade.get("item")) or {}
        irmas = [a for a in grade["aulas"] if a.get("item") == aula_grade.get("item")]
        total_partes = len(irmas) or 1
        parte = irmas.index(aula_grade) + 1 if aula_grade in irmas else 1
    else:
        item = item_do_plano(itens, num=args.num, seq=args.seq, ident=args.ident)
        if not item:
            print("ERRO: item não encontrado no plano.", file=sys.stderr)
            listar(plano, grade)
            raise SystemExit(1)
        fatias = item.get("minutos_por_aula") or [item.get("minutos") or 30]
        total_partes = len(fatias)
        parte = max(1, min(args.parte, total_partes))

    if aula_grade:
        minutos = int(aula_grade.get("minutos") or 30)
        titulo = aula_grade.get("titulo") or item.get("rotulo") or "Aula"
        numero = args.numero or aula_grade.get("seq") or 1
        objetivo = aula_grade.get("objetivo") or ""
    else:
        fatias = item.get("minutos_por_aula") or [item.get("minutos") or 30]
        minutos = int(fatias[parte - 1])
        titulo = item.get("rotulo") or "Aula"
        if total_partes > 1:
            titulo = f"{titulo} (parte {parte} de {total_partes})"
        numero = args.numero or item.get("seq") or 1
        objetivo = ""

    grafo = plano.get("grafo") or {}
    disciplina = (grade or {}).get("assunto") or grafo.get("escopo") \
        or (plano.get("assunto") or {}).get("rotulo") or "Estudo"

    briefing = {
        "disciplina": disciplina,
        "numero": numero,
        "titulo": titulo,
        "objetivo_do_sumario": objetivo,
        "slug": f"aula-{int(numero):02d}-{slugificar(item.get('rotulo') or titulo)}",
        "banca_estilo": estilo_da_banca(grafo.get("banca_alvo")),
        "duracao_alvo_min": minutos,
        "duracao_definida_por": "plano",
        "plano": {
            "arquivo": str(args.alvo),
            "item_id": item.get("id"),
            "item_num": item.get("num"),
            "aula_id": (aula_grade or {}).get("id"),
            "parte": parte,
            "de_partes": total_partes,
            "modulo": item.get("modulo"),
        },
        "prioridade": {
            "importancia": item.get("importancia"),
            "classe_grafo": item.get("classe_grafo"),
            "share": item.get("share"),
            "n_questoes": item.get("n_questoes"),
            "tipo_cobranca": item.get("tipo_cobranca"),
            "nivel": (aula_grade or {}).get("nivel") or item.get("nivel"),
            "formato": (aula_grade or {}).get("formato") or item.get("formato"),
            "marcas": item.get("marcas") or [],
        },
        "pre_requisitos": rotulos(itens, item.get("requer")),
        "destrava": rotulos(itens, item.get("destrava")),
        "obs": item.get("obs") or "",
    }

    if args.meta:
        objetivos = [objetivo] if objetivo else []
        objetivos.append("PREENCHER: complete até 3 objetivos observáveis")
        print(json.dumps({
            "disciplina": briefing["disciplina"],
            "numero": briefing["numero"],
            "titulo": briefing["titulo"],
            "slug": briefing["slug"],
            "banca_estilo": briefing["banca_estilo"],
            "duracao_alvo_min": briefing["duracao_alvo_min"],
            "duracao_definida_por": "plano",
            "margem_anotacao": False,
            "objetivos": objetivos,
            "pre_requisitos": briefing["pre_requisitos"],
            "plano": briefing["plano"],
            "fontes": [],
        }, ensure_ascii=False, indent=2))
        return

    if args.json:
        print(json.dumps(briefing, ensure_ascii=False, indent=2))
        return

    p = briefing["prioridade"]
    print(f"aula {briefing['numero']} · {briefing['disciplina']}")
    print(f"  título ............ {briefing['titulo']}")
    if objetivo:
        print(f"  objetivo .......... {objetivo}")
    print(f"  duração-alvo ...... {minutos} min"
          + (f"  (parte {parte} de {total_partes} do tópico)" if total_partes > 1 else ""))
    print(f"  estilo de banca ... {briefing['banca_estilo']}")
    print(f"  importância ....... {p['importancia']}/10"
          + (f" · classe {p['classe_grafo']}" if p.get("classe_grafo") else "")
          + (f" · {p['n_questoes']} questões mapeadas" if p.get("n_questoes") else ""))
    if p.get("formato") and p["formato"] != "cheia":
        print(f"  formato ........... {p['formato']} (regra de lastro do sumário)")
    if p.get("tipo_cobranca"):
        cobranca = p["tipo_cobranca"]
        if isinstance(cobranca, (list, tuple)):
            cobranca = ", ".join(str(c) for c in cobranca)
        print(f"  cobrança .......... {cobranca}")
    if briefing["pre_requisitos"]:
        print(f"  pré-requisitos .... {'; '.join(briefing['pre_requisitos'][:6])}")
    if briefing["destrava"]:
        print(f"  destrava .......... {'; '.join(briefing['destrava'][:6])}")
    if p.get("marcas"):
        print(f"  marcas ............ {', '.join(p['marcas'])}")
    if briefing["obs"]:
        print(f"  obs ............... {briefing['obs']}")
    print(f"  slug .............. {briefing['slug']}")


if __name__ == "__main__":
    main()
