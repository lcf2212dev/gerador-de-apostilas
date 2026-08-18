#!/usr/bin/env python3
"""Envia os flashcards da aula para o Anki.

    python3 anki_import.py aulas/<disciplina>/aula-NN-<slug>   # ou o caminho do flashcards.json

Cascata, do mais automático ao mais manual:
  1. AnkiConnect em 127.0.0.1:8765 — insere direto na coleção, sem duplicar;
  2. arquivo .tsv com cabeçalhos nativos (deck e tags já embutidos), sempre gerado;
  3. --apkg gera um pacote .apkg via `uv run --with genanki` (importa com dois cliques).

Opções: --dry-run  --deck NOME  --apkg  --so-arquivo
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path

ANKICONNECT = "http://127.0.0.1:8765"
TEMPO_LIMITE = 10

MODELO_BASICO_ID = 1748392011
MODELO_CLOZE_ID = 1748392012

CSS_CARTAO = """
.card { font-family: "Noto Serif", Georgia, serif; font-size: 20px; text-align: left;
        color: #111827; background: #ffffff; line-height: 1.5; padding: 12px; }
.fonte { font-family: "Noto Sans", Arial, sans-serif; font-size: 14px; color: #6B7280;
         margin-top: 10px; }
hr#answer { border: none; border-top: 2px solid #12805C; margin: 14px 0; }
.cloze { color: #0E6B4F; font-weight: 700; }
"""


# --- AnkiConnect ----------------------------------------------------------


def anki(acao: str, **params):
    corpo = json.dumps({"action": acao, "version": 6, "params": params}).encode("utf-8")
    req = urllib.request.Request(ANKICONNECT, data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TEMPO_LIMITE) as r:
        resposta = json.loads(r.read().decode("utf-8"))
    if resposta.get("error"):
        raise RuntimeError(resposta["error"])
    return resposta.get("result")


def escolher_modelo(nomes: list[str], cloze: bool) -> str | None:
    """O Anki traduz os nomes dos modelos padrão; procura o equivalente em qualquer idioma."""
    baixo = {n.lower(): n for n in nomes}
    if cloze:
        for exato in ("cloze", "omissão de palavras", "omissao de palavras",
                      "preenchimento de lacunas"):
            if exato in baixo:
                return baixo[exato]
        for n in nomes:
            if any(t in n.lower() for t in ("cloze", "omiss", "lacuna")):
                return n
        return None
    for exato in ("basic", "básico", "basico"):
        if exato in baixo:
            return baixo[exato]
    for n in nomes:
        low = n.lower()
        if low.startswith(("basic", "básic", "basic")) and not any(
            t in low for t in ("revers", "type", "digit", "opcional")
        ):
            return n
    return nomes[0] if nomes else None


def enviar_por_ankiconnect(deck: str, cards: list, tags: list, dry: bool) -> tuple[bool, str]:
    try:
        versao = anki("version")
    except (urllib.error.URLError, OSError, TimeoutError):
        return False, "Anki fechado ou AnkiConnect indisponível"
    except RuntimeError as e:
        return False, f"AnkiConnect recusou: {e}"

    nomes = anki("modelNames")
    modelo_basico = escolher_modelo(nomes, cloze=False)
    precisa_cloze = any(c.get("tipo") == "cloze" for c in cards)
    modelo_cloze = escolher_modelo(nomes, cloze=True) if precisa_cloze else None

    if precisa_cloze and not modelo_cloze:
        return False, "nenhum modelo de omissão (cloze) encontrado na sua coleção"

    campos_basico = anki("modelFieldNames", modelName=modelo_basico)
    campos_cloze = anki("modelFieldNames", modelName=modelo_cloze) if modelo_cloze else []

    notas = []
    for c in cards:
        etiquetas = sorted(set(tags) | set(c.get("tags", [])))
        if c.get("tipo") == "cloze":
            valores = [c["texto"], c.get("extra", "")]
            campos = campos_cloze
            modelo = modelo_cloze
        else:
            valores = [c["frente"], c["verso"]]
            if c.get("extra"):
                valores.append(c["extra"])
            campos = campos_basico
            modelo = modelo_basico
        notas.append({
            "deckName": deck,
            "modelName": modelo,
            "fields": {nome: valor for nome, valor in zip(campos, valores)},
            "tags": etiquetas,
            "options": {"allowDuplicate": False, "duplicateScope": "deck"},
        })

    if dry:
        return True, (f"AnkiConnect v{versao} respondendo · modelos '{modelo_basico}'"
                      f"{f' e ' + repr(modelo_cloze) if modelo_cloze else ''} · "
                      f"{len(notas)} notas prontas (dry-run, nada gravado)")

    anki("createDeck", deck=deck)

    # Filtrar antes de enviar: o addNotes devolve erro (e não resultado) quando toda a
    # remessa é duplicada, o que faria uma reexecução legítima parecer falha.
    try:
        podem = anki("canAddNotes", notes=notas)
    except RuntimeError:
        podem = [True] * len(notas)

    novas = [n for n, ok in zip(notas, podem) if ok]
    duplicadas = len(notas) - len(novas)

    if not novas:
        return True, (f"nada a fazer: os {duplicadas} cards já estão no deck '{deck}'")

    resultado = anki("addNotes", notes=novas)
    inseridas = [r for r in resultado if r]
    return True, (f"{len(inseridas)} de {len(notas)} cards inseridos no deck '{deck}'"
                  + (f" ({duplicadas} já existiam e foram ignorados)" if duplicadas else ""))


# --- TSV ------------------------------------------------------------------


def limpar(texto: str) -> str:
    return re.sub(r"[\t\r\n]+", " ", texto or "").strip()


def gerar_tsv(destino: Path, deck: str, cards: list, tags: list,
              modelo_basico="Basic", modelo_cloze="Cloze") -> Path:
    linhas = [
        "#separator:tab",
        "#html:true",
        "#notetype column:1",
        "#deck column:2",
        "#tags column:5",
    ]
    for c in cards:
        etiquetas = " ".join(sorted(set(tags) | set(c.get("tags", []))))
        if c.get("tipo") == "cloze":
            campos = [modelo_cloze, deck, limpar(c["texto"]), limpar(c.get("extra", ""))]
        else:
            verso = limpar(c["verso"])
            if c.get("extra"):
                verso += f"<div class='fonte'>{limpar(c['extra'])}</div>"
            campos = [modelo_basico, deck, limpar(c["frente"]), verso]
        linhas.append("\t".join(campos + [etiquetas]))
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


# --- apkg (genanki) -------------------------------------------------------


def gerar_apkg(destino: Path, deck: str, cards: list, tags: list) -> None:
    import genanki  # noqa: PLC0415 — só existe quando rodando sob `uv run --with genanki`

    basico = genanki.Model(
        MODELO_BASICO_ID, "Apostila — Básico",
        fields=[{"name": "Frente"}, {"name": "Verso"}, {"name": "Fonte"}],
        templates=[{
            "name": "Cartão 1",
            "qfmt": "{{Frente}}",
            "afmt": '{{FrontSide}}<hr id=answer>{{Verso}}'
                    '{{#Fonte}}<div class="fonte">{{Fonte}}</div>{{/Fonte}}',
        }],
        css=CSS_CARTAO,
    )
    cloze = genanki.Model(
        MODELO_CLOZE_ID, "Apostila — Omissão",
        fields=[{"name": "Texto"}, {"name": "Extra"}],
        templates=[{
            "name": "Omissão",
            "qfmt": "{{cloze:Texto}}",
            "afmt": '{{cloze:Texto}}{{#Extra}}<div class="fonte">{{Extra}}</div>{{/Extra}}',
        }],
        css=CSS_CARTAO,
        model_type=genanki.Model.CLOZE,
    )

    # id estável a partir do nome: reimportar atualiza o mesmo deck em vez de criar outro.
    deck_id = 1_000_000_000 + zlib.crc32(deck.encode("utf-8")) % 1_000_000_000
    baralho = genanki.Deck(deck_id, deck)

    for c in cards:
        etiquetas = sorted(set(tags) | set(c.get("tags", [])))
        if c.get("tipo") == "cloze":
            nota = genanki.Note(model=cloze,
                                fields=[c["texto"], c.get("extra", "")],
                                tags=etiquetas)
        else:
            nota = genanki.Note(model=basico,
                                fields=[c["frente"], c["verso"], c.get("extra", "")],
                                tags=etiquetas)
        baralho.add_note(nota)

    genanki.Package(baralho).write_to_file(str(destino))


def gerar_apkg_via_uv(destino: Path, origem: Path, deck: str) -> tuple[bool, str]:
    cmd = ["uv", "run", "--quiet", "--with", "genanki", "python", str(Path(__file__).resolve()),
           str(origem), "--apkg", "--so-arquivo", "--deck", deck, "--_apkg-interno"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"não foi possível rodar o uv ({e})"
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout) \
            else "falha desconhecida ao gerar o .apkg"
    return destino.exists(), f"pacote gerado: {destino}"


# --- principal ------------------------------------------------------------


def carregar(caminho: Path) -> tuple[Path, dict]:
    arquivo = caminho / "flashcards.json" if caminho.is_dir() else caminho
    if not arquivo.exists():
        print(f"ERRO: não encontrei {arquivo}", file=sys.stderr)
        raise SystemExit(1)
    try:
        return arquivo, json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERRO: JSON inválido em {arquivo}: {e}", file=sys.stderr)
        raise SystemExit(1)


def validar(dados: dict) -> list:
    cards = dados.get("cards") or []
    if not cards:
        print("ERRO: nenhum card em flashcards.json", file=sys.stderr)
        raise SystemExit(1)
    for i, c in enumerate(cards, 1):
        if c.get("tipo") == "cloze":
            if "{{c" not in (c.get("texto") or ""):
                print(f"ERRO: card {i} é cloze mas não tem {{{{c1::…}}}}", file=sys.stderr)
                raise SystemExit(1)
        elif not (c.get("frente") and c.get("verso")):
            print(f"ERRO: card {i} sem 'frente' ou 'verso'", file=sys.stderr)
            raise SystemExit(1)
    return cards


def main() -> None:
    ap = argparse.ArgumentParser(description="Importa os flashcards da aula para o Anki.")
    ap.add_argument("alvo", type=Path, help="diretório da aula ou caminho do flashcards.json")
    ap.add_argument("--deck", help="sobrescreve o nome do deck")
    ap.add_argument("--dry-run", action="store_true", help="não grava nada, só relata")
    ap.add_argument("--apkg", action="store_true", help="também gera um pacote .apkg")
    ap.add_argument("--so-arquivo", action="store_true", help="não tenta o AnkiConnect")
    ap.add_argument("--_apkg-interno", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    arquivo, dados = carregar(args.alvo)
    cards = validar(dados)
    deck = args.deck or dados.get("deck") or "Concurso"
    tags = dados.get("tags") or []
    pasta = arquivo.parent

    # Re-execução sob `uv run --with genanki`: só gera o pacote e sai.
    if args._apkg_interno:
        gerar_apkg(pasta / "flashcards.apkg", deck, cards, tags)
        return

    print(f"deck: {deck}")
    print(f"cards: {len(cards)} ({sum(1 for c in cards if c.get('tipo') == 'cloze')} de omissão)")

    if not args.so_arquivo:
        ok, msg = enviar_por_ankiconnect(deck, cards, tags, args.dry_run)
        print(("anki: " if ok else "anki: falhou — ") + msg)
        if not ok:
            print("      abra o Anki (o add-on AnkiConnect já está instalado) e rode de novo,\n"
                  "      ou importe o arquivo .tsv abaixo manualmente.")

    if not args.dry_run:
        tsv = gerar_tsv(pasta / "flashcards.tsv", deck, cards, tags)
        print(f"tsv: {tsv}  (Anki > Arquivo > Importar — deck e tags já vêm no arquivo)")

        if args.apkg:
            destino = pasta / "flashcards.apkg"
            try:
                gerar_apkg(destino, deck, cards, tags)
                print(f"apkg: {destino}")
            except ImportError:
                ok, msg = gerar_apkg_via_uv(destino, arquivo, deck)
                print(("apkg: " if ok else "apkg: falhou — ") + msg)


if __name__ == "__main__":
    main()
