#!/usr/bin/env python3
"""Valida questoes.json contra a rubrica de item bem construído.

Uso:
    python3 validar_questoes.py questoes.json [--corpo corpo.html]

Saída: erros (bloqueantes, código 1) e avisos (exigem julgamento, código 0).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

# Casadas contra o texto normalizado (minúsculo, sem acento e sem pontuação),
# sempre com fronteira de palavra — "nda" solto casaria dentro de "fundamentos".
PROIBIDAS = re.compile(
    r"\b("
    r"todas as (anteriores|alternativas (anteriores|acima)|opcoes (anteriores|acima))"
    r"|nenhuma das (anteriores|alternativas|opcoes)"
    r"|n d a"
    r"|as alternativas [a-e] e [a-e] (estao|sao) corretas"
    r")\b"
)
ABSOLUTOS = ("sempre", "nunca", "jamais", "exclusivamente", "unicamente",
             "em hipotese alguma", "em qualquer hipotese")
NIVEIS_ESPERADOS = {"facil": 3, "media": 5, "dificil": 2}
COMPETENCIAS = {"lembrar", "compreender", "aplicar", "analisar"}


def normalizar(texto: str) -> str:
    sem_tags = re.sub(r"<[^>]+>", "", texto or "")
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", sem_tags.lower())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(re.sub(r"[^\w\s]", " ", sem_acento).split())


def palavras(texto: str) -> int:
    return len(normalizar(texto).split())


class _Secoes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.n = 0
        self._quadro = 0

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        if "quadro-sintese" in classes:
            self._quadro = 1
        elif self._quadro:
            self._quadro += 1
        if tag == "h2" and not self._quadro and "sem-numero" not in classes:
            self.n += 1

    def handle_endtag(self, tag):
        if self._quadro:
            self._quadro -= 1


def secoes_do_corpo(caminho: Path) -> int:
    p = _Secoes()
    p.feed(caminho.read_text(encoding="utf-8"))
    p.close()
    return p.n


def validar(dados: dict, total_secoes: int | None) -> tuple[list, list]:
    erros: list[str] = []
    avisos: list[str] = []

    estilo = dados.get("banca_estilo", "A-E")
    questoes = dados.get("questoes") or []

    if len(questoes) != 10:
        erros.append(f"são exigidas 10 questões; o arquivo tem {len(questoes)}")

    cebraspe = estilo == "cebraspe-ce"
    letras_validas = ("C", "E") if cebraspe else tuple("ABCDE"[: 4 if estilo == "A-D" else 5])

    gabaritos = []
    razoes_comprimento = []

    for i, q in enumerate(questoes, 1):
        rot = f"questão {q.get('id', i)}"
        enunciado = q.get("enunciado", "")
        gab = q.get("gabarito")
        gabaritos.append(gab)

        if not enunciado:
            erros.append(f"{rot}: enunciado vazio")
        elif palavras(enunciado) < 8:
            avisos.append(f"{rot}: enunciado com {palavras(enunciado)} palavras — curto demais "
                          "para ser respondível sem olhar as alternativas")
        elif palavras(enunciado) > 90:
            avisos.append(f"{rot}: enunciado com {palavras(enunciado)} palavras — prolixo")

        if gab not in letras_validas:
            erros.append(f"{rot}: gabarito '{gab}' fora de {list(letras_validas)}")

        if not q.get("justificativa"):
            erros.append(f"{rot}: sem justificativa do gabarito")
        if not q.get("fonte"):
            erros.append(f"{rot}: sem 'fonte' — todo item precisa de fundamento verificável")

        nivel = q.get("nivel")
        if nivel not in NIVEIS_ESPERADOS:
            erros.append(f"{rot}: nivel '{nivel}' inválido (use facil, media ou dificil)")
        if q.get("competencia") and q["competencia"] not in COMPETENCIAS:
            avisos.append(f"{rot}: competencia '{q['competencia']}' fora de {sorted(COMPETENCIAS)}")

        if cebraspe:
            if q.get("alternativas"):
                avisos.append(f"{rot}: estilo Cebraspe não usa alternativas")
            continue

        alts = q.get("alternativas") or {}
        if set(alts) != set(letras_validas):
            erros.append(f"{rot}: alternativas devem ser exatamente {list(letras_validas)}")
            continue

        erros_dict = q.get("erros") or {}
        faltando = [l for l in letras_validas if l != gab and not erros_dict.get(l)]
        if faltando:
            erros.append(f"{rot}: sem comentário de erro para {', '.join(faltando)}")

        textos = {l: normalizar(t) for l, t in alts.items()}
        for l, t in textos.items():
            if PROIBIDAS.search(t):
                erros.append(f"{rot}, alternativa {l}: usa formulação proibida "
                             "('todas/nenhuma das anteriores')")
            if not t:
                erros.append(f"{rot}, alternativa {l}: vazia")

        vistos = {}
        for l, t in textos.items():
            if t and t in vistos:
                erros.append(f"{rot}: alternativas {vistos[t]} e {l} são idênticas")
            vistos[t] = l

        comprimentos = {l: len(t) for l, t in textos.items()}
        if gab in comprimentos and len(comprimentos) > 1:
            mediana = statistics.median(comprimentos.values())
            if mediana:
                razoes_comprimento.append(comprimentos[gab] / mediana)
            if comprimentos[gab] == max(comprimentos.values()) and mediana:
                if comprimentos[gab] > 1.6 * mediana:
                    avisos.append(f"{rot}: a alternativa correta é bem mais longa que as demais "
                                  "— pista clássica que entrega a resposta")

        for l, t in textos.items():
            if l != gab and any(f" {a} " in f" {t} " for a in ABSOLUTOS):
                avisos.append(f"{rot}, alternativa {l}: usa termo absoluto "
                              "('sempre', 'nunca'…), pista comum de distrator")

    # --- padrões do conjunto ---
    contagem = Counter(g for g in gabaritos if g)
    if not cebraspe:
        for letra in letras_validas:
            if contagem[letra] == 0:
                avisos.append(f"a letra {letra} nunca é gabarito — distribua melhor")
            if contagem[letra] > 3:
                erros.append(f"a letra {letra} é gabarito {contagem[letra]} vezes "
                             "(máximo 3 em 10 questões)")
    else:
        certos = contagem.get("C", 0)
        if not 4 <= certos <= 6:
            erros.append(f"{certos} itens 'Certo' em 10 — mantenha entre 4 e 6 no estilo Cebraspe")

    for i in range(len(gabaritos) - 2):
        if gabaritos[i] and gabaritos[i] == gabaritos[i + 1] == gabaritos[i + 2]:
            erros.append(f"três gabaritos '{gabaritos[i]}' seguidos "
                         f"(questões {i + 1} a {i + 3})")
            break

    if len(razoes_comprimento) >= 8:
        acima = sum(1 for r in razoes_comprimento if r > 1.15)
        if acima >= 7:
            erros.append(f"em {acima} de {len(razoes_comprimento)} questões a alternativa correta "
                         "é a mais longa — viés sistemático de comprimento")

    niveis = Counter(q.get("nivel") for q in questoes)
    for nivel, esperado in NIVEIS_ESPERADOS.items():
        if abs(niveis[nivel] - esperado) > 1:
            erros.append(f"distribuição de dificuldade: {niveis[nivel]} '{nivel}' "
                         f"(esperado {esperado} ± 1)")

    profundas = sum(1 for q in questoes if q.get("competencia") in ("compreender", "aplicar", "analisar"))
    if questoes and profundas < 4:
        avisos.append(f"apenas {profundas} questões acima de 'lembrar' — o conjunto está "
                      "medindo memória, não compreensão")

    secoes = {str(q.get("secao")) for q in questoes if q.get("secao")}
    if total_secoes:
        esperadas = {str(i) for i in range(1, total_secoes + 1)}
        sem_questao = sorted(esperadas - secoes, key=int)
        if sem_questao:
            erros.append(f"seções sem nenhuma questão: {', '.join(sem_questao)}")
    elif len(secoes) < 2 and questoes:
        avisos.append("todas as questões apontam para a mesma seção — verifique a cobertura")

    return erros, avisos


def main() -> None:
    ap = argparse.ArgumentParser(description="Valida questoes.json.")
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--corpo", type=Path, help="corpo.html da aula, para checar cobertura de seções")
    args = ap.parse_args()

    try:
        dados = json.loads(args.arquivo.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERRO: arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"ERRO: JSON inválido: {e}", file=sys.stderr)
        raise SystemExit(1)

    total_secoes = None
    if args.corpo and args.corpo.exists():
        total_secoes = secoes_do_corpo(args.corpo)

    erros, avisos = validar(dados, total_secoes)

    for e in erros:
        print(f"ERRO: {e}")
    for a in avisos:
        print(f"aviso: {a}")

    n = len(dados.get("questoes") or [])
    if erros:
        print(f"\n{len(erros)} erro(s) bloqueante(s) em {n} questões — corrija e rode de novo.")
        raise SystemExit(1)
    print(f"\nok: {n} questões válidas"
          f"{f', {len(avisos)} aviso(s) para revisar' if avisos else ''}.")


if __name__ == "__main__":
    main()
