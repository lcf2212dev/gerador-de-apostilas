#!/usr/bin/env python3
"""Busca e verifica vídeos do YouTube sem chave de API. Só biblioteca padrão.

    yt.py buscar "principios fundamentais cf 88 concurso" [--max 20] [--json]
    yt.py inspecionar dQw4w9WgXcQ outroID [--json]

`buscar` raspa os metadados reais da página de resultados (título, canal, duração,
visualizações, data). `inspecionar` confirma que o vídeo existe e está público — via
oEmbed, que devolve HTTP 400 para id inexistente — e coleta os números da página do vídeo.

Nenhum vídeo deve entrar em videos.json sem passar por `inspecionar`: é o que impede
recomendar um link que não existe.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/151.0.0.0 Safari/537.36")
CABECALHOS = {
    "User-Agent": UA,
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Cookie": "CONSENT=YES+cb; SOCS=CAI",
}
TEMPO_LIMITE = 25


def buscar_html(url: str) -> str:
    req = urllib.request.Request(url, headers=CABECALHOS)
    with urllib.request.urlopen(req, timeout=TEMPO_LIMITE) as r:
        return r.read().decode("utf-8", "replace")


def extrair_json(html: str, marcador: str) -> dict:
    """Extrai o objeto JSON que segue o marcador, contando chaves balanceadas."""
    i = html.find(marcador)
    if i < 0:
        return {}
    i = html.find("{", i)
    if i < 0:
        return {}
    nivel, em_string, escapado = 0, False, False
    for j in range(i, len(html)):
        c = html[j]
        if escapado:
            escapado = False
            continue
        if c == "\\":
            escapado = True
            continue
        if c == '"':
            em_string = not em_string
            continue
        if em_string:
            continue
        if c == "{":
            nivel += 1
        elif c == "}":
            nivel -= 1
            if nivel == 0:
                try:
                    return json.loads(html[i:j + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


def achar_chave(no, chave: str):
    """Percorre a árvore devolvendo todos os valores de uma chave, em qualquer profundidade."""
    if isinstance(no, dict):
        for k, v in no.items():
            if k == chave:
                yield v
            else:
                yield from achar_chave(v, chave)
    elif isinstance(no, list):
        for item in no:
            yield from achar_chave(item, chave)


def texto(no) -> str:
    """Achata os formatos de texto do YouTube (simpleText ou runs)."""
    if not isinstance(no, dict):
        return ""
    if "simpleText" in no:
        return no["simpleText"]
    return "".join(r.get("text", "") for r in no.get("runs", []))


def para_int(s: str) -> int | None:
    digitos = re.sub(r"[^\d]", "", s or "")
    return int(digitos) if digitos else None


def duracao_segundos(s: str) -> int | None:
    if not s or not re.match(r"^\d+(:\d{2})+$", s.strip()):
        return None
    partes = [int(p) for p in s.strip().split(":")]
    total = 0
    for p in partes:
        total = total * 60 + p
    return total


# --- buscar ---------------------------------------------------------------


def buscar(consulta: str, maximo: int) -> list[dict]:
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode(
        {"search_query": consulta, "hl": "pt-BR", "gl": "BR"}
    )
    html = buscar_html(url)
    dados = extrair_json(html, "ytInitialData")
    if not dados:
        return []

    vistos, achados = set(), []
    for vr in achar_chave(dados, "videoRenderer"):
        if not isinstance(vr, dict):
            continue
        vid = vr.get("videoId")
        if not vid or vid in vistos:
            continue
        vistos.add(vid)

        dur_txt = texto(vr.get("lengthText") or {})
        segundos = duracao_segundos(dur_txt)
        overlays = json.dumps(vr.get("thumbnailOverlays", []), ensure_ascii=False)
        ao_vivo = "LIVE" in overlays or any(
            texto(b.get("metadataBadgeRenderer", {}).get("label", {})) == "AO VIVO"
            for b in vr.get("badges", []) if isinstance(b, dict)
        )

        achados.append({
            "id": vid,
            "url": f"https://youtu.be/{vid}",
            "titulo": texto(vr.get("title") or {}),
            "canal": texto(vr.get("ownerText") or vr.get("longBylineText") or {}),
            "duracao_txt": dur_txt,
            "duracao_seg": segundos,
            "duracao_min": round(segundos / 60, 1) if segundos else None,
            "visualizacoes": para_int(texto(vr.get("viewCountText") or {})),
            "publicado_txt": texto(vr.get("publishedTimeText") or {}),
            "descricao": texto(vr.get("detailedMetadataSnippets", [{}])[0].get("snippetText", {}))
            if vr.get("detailedMetadataSnippets") else texto(vr.get("descriptionSnippet") or {}),
            "short": segundos is not None and segundos <= 60 and not dur_txt,
            "ao_vivo": ao_vivo,
        })
        if len(achados) >= maximo:
            break
    return achados


# --- inspecionar ----------------------------------------------------------


def oembed(vid: str) -> dict | None:
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"}
    )
    try:
        req = urllib.request.Request(url, headers=CABECALHOS)
        with urllib.request.urlopen(req, timeout=TEMPO_LIMITE) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def inspecionar(vid: str) -> dict:
    info = {"id": vid, "url": f"https://youtu.be/{vid}", "existe": False}

    oe = oembed(vid)
    if oe is None:
        info["motivo"] = "oEmbed recusou: vídeo inexistente, privado, removido ou não incorporável"
        return info

    info.update({
        "existe": True,
        "titulo": oe.get("title", ""),
        "canal": oe.get("author_name", ""),
        "canal_url": oe.get("author_url", ""),
    })

    try:
        html = buscar_html(f"https://www.youtube.com/watch?v={vid}&hl=pt-BR&gl=BR")
    except (urllib.error.URLError, TimeoutError) as e:
        info["aviso"] = f"metadados detalhados indisponíveis ({e})"
        return info

    player = extrair_json(html, "ytInitialPlayerResponse")
    detalhes = player.get("videoDetails", {}) if player else {}
    micro = (player.get("microformat", {}) or {}).get("playerMicroformatRenderer", {}) if player else {}
    status = (player.get("playabilityStatus", {}) or {}).get("status") if player else None

    segundos = para_int(detalhes.get("lengthSeconds", ""))
    info.update({
        "reproduzivel": status == "OK",
        "duracao_seg": segundos,
        "duracao_min": round(segundos / 60, 1) if segundos else None,
        "visualizacoes": para_int(detalhes.get("viewCount", "")),
        "publicado": (micro.get("publishDate") or micro.get("uploadDate") or "")[:10],
        "canal_id": detalhes.get("channelId", ""),
        "idioma": (micro.get("language") or ""),
        "categoria": micro.get("category", ""),
        "ao_vivo": bool(detalhes.get("isLiveContent")),
        "descricao": (detalhes.get("shortDescription") or "")[:600],
    })
    if status and status != "OK":
        info["motivo"] = f"playabilityStatus = {status}"

    dados = extrair_json(html, "ytInitialData")
    if dados:
        for dono in achar_chave(dados, "videoOwnerRenderer"):
            inscritos = texto(dono.get("subscriberCountText") or {})
            if inscritos:
                info["inscritos_txt"] = inscritos
                break
        for cur in achar_chave(dados, "captionTracks"):
            info["tem_legenda"] = bool(cur)
            break
    return info


# --- saída ----------------------------------------------------------------


def linha_tabela(v: dict) -> str:
    vis = v.get("visualizacoes")
    vis_txt = f"{vis:,}".replace(",", ".") if vis else "?"
    dur = v.get("duracao_min")
    marcas = []
    if v.get("ao_vivo"):
        marcas.append("AO-VIVO")
    if v.get("short") or (v.get("duracao_seg") or 999) <= 60:
        marcas.append("SHORT")
    if v.get("existe") is False:
        marcas.append("INDISPONÍVEL")
    return " | ".join([
        v["id"],
        (v.get("titulo") or "")[:70],
        (v.get("canal") or "")[:28],
        f"{dur} min" if dur else "?",
        f"{vis_txt} views",
        v.get("publicado") or v.get("publicado_txt") or "?",
        v.get("inscritos_txt", ""),
        " ".join(marcas),
    ])


def main() -> None:
    ap = argparse.ArgumentParser(description="Busca e verifica vídeos do YouTube sem API key.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("buscar", help="busca candidatos com metadados reais")
    b.add_argument("consulta")
    b.add_argument("--max", type=int, default=20)
    b.add_argument("--json", action="store_true")

    i = sub.add_parser("inspecionar", help="verifica existência e coleta metadados")
    i.add_argument("ids", nargs="+")
    i.add_argument("--json", action="store_true")

    args = ap.parse_args()

    try:
        if args.cmd == "buscar":
            resultados = buscar(args.consulta, args.max)
            if not resultados:
                print("nenhum resultado — o HTML do YouTube pode ter mudado; "
                      "use WebSearch para descobrir candidatos e verifique cada um com "
                      "'yt.py inspecionar'", file=sys.stderr)
                raise SystemExit(3)
        else:
            resultados = [inspecionar(v) for v in args.ids]
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"ERRO de rede: {e}", file=sys.stderr)
        raise SystemExit(4)

    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    else:
        for v in resultados:
            print(linha_tabela(v))
            if v.get("motivo"):
                print(f"    ^ {v['motivo']}")


if __name__ == "__main__":
    main()
