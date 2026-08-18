#!/usr/bin/env python3
"""grafo.py — motor determinístico do grafo de conteúdo ponderado.

Lê `evidencias.json` (o que foi observado em editais e provas), aplica as fórmulas
documentadas em `references/pesos.md` e escreve `grafo.md`.

A regra que justifica este arquivo existir: **o modelo extrai evidência, o script
calcula peso**. Nenhum número do grafo sai de julgamento — todos saem de fórmula
sobre dados rastreáveis, o que torna o resultado auditável e recalculável.

Determinismo: o mesmo `evidencias.json` sempre gera o mesmo `grafo.md`. O ano de
referência do decaimento é `janela.ate`, nunca a data de execução.

Sem dependências externas: só a biblioteca padrão do Python.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

SCHEMA = "grafo-concurso/1"

# Ordem canônica da hierarquia. O peso é normalizado DENTRO de cada nível, então
# só faz sentido comparar nós do mesmo nível entre si.
NIVEIS = ["escopo", "bloco", "disciplina", "tema", "topico", "subtopico"]

# Padrões de cálculo. Qualquer um pode ser sobrescrito em evidencias.json
# ("parametros") ou em ajustes.json — o grafo registra os valores usados.
PADROES = {
    "w_incidencia": 0.65,          # o que cai pesa mais...
    "w_edital": 0.35,              # ...mas o edital cobre o que ainda não caiu
    "meia_vida_anos": 2.5,         # prova de 5 anos atrás vale 1/4 de uma deste ano
    "peso_banca_alvo": 1.0,
    "peso_outras_bancas": 0.45,
    "k_confianca": 5.0,            # nº de questões para a confiança chegar a ~50%
    "m_prior_ramo": 5.0,           # força do prior uniforme dentro do ramo, em questões
    "mencao_explicita": 1.0,
    "mencao_generica": 0.5,
    "limiar_tendencia": 0.35,
    "min_questoes_tendencia": 4,
    "mult_alta": 1.15,
    "mult_estavel": 1.0,
    "mult_queda": 0.88,
    "cortes_classe": [0.50, 0.80, 0.95],
    "limiar_confianca_baixa": 0.30,
    "limiar_edital_obrigatorio": 0.80,
    "jaccard_min": 0.15,
    "coocorrencia_min": 2,
    "custo_h_padrao": 1.0,
    "max_nos_arquivo_unico": 250,
}

TIPOS_ARESTA = {"prerequisito", "correlato", "atualiza", "contem", "coocorre"}
# `contem` e `coocorre` são derivadas pelo script; não se declaram à mão.
TIPOS_ARESTA_DECLARAVEIS = {"prerequisito", "correlato", "atualiza"}


# --- E/S ------------------------------------------------------------------


def erro(mensagem: str) -> None:
    print(f"ERRO: {mensagem}", file=sys.stderr)
    raise SystemExit(1)


def aviso(mensagem: str) -> None:
    print(f"aviso: {mensagem}", file=sys.stderr)


def raiz_projeto() -> Path:
    """A raiz do projeto, subindo de .claude/skills/mapear-conteudo/scripts/."""
    return Path(__file__).resolve().parents[4]


def dir_grafo(slug: str, raiz: Path | None = None) -> Path:
    """Aceita um slug (grafos/<slug>) ou um caminho de diretório direto."""
    if "/" in slug or slug.startswith("."):
        return Path(slug).resolve()
    return (raiz or raiz_projeto()) / "grafos" / slug


def carregar_json(caminho: Path, obrigatorio: bool = True) -> dict:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if obrigatorio:
            erro(f"arquivo não encontrado: {caminho}")
        return {}
    except json.JSONDecodeError as e:
        erro(f"JSON inválido em {caminho}: {e}")
    return {}


def carregar(slug: str, raiz: Path | None = None) -> tuple[Path, dict, dict]:
    d = dir_grafo(slug, raiz)
    ev = carregar_json(d / "evidencias.json")
    ajustes = carregar_json(d / "ajustes.json", obrigatorio=False)
    return d, ev, ajustes


def _norm(texto: str) -> str:
    """Normaliza para comparação: sem acento, sem caixa, sem espaço nas pontas."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().lower()


# --- Validação ------------------------------------------------------------


def validar(ev: dict, ajustes: dict) -> tuple[list[str], list[str]]:
    """Devolve (erros, avisos). Erro impede o build; aviso não."""
    erros: list[str] = []
    avisos: list[str] = []

    if ev.get("schema") != SCHEMA:
        erros.append(f"schema esperado {SCHEMA!r}, encontrado {ev.get('schema')!r}")

    escopo = ev.get("escopo") or {}
    for campo in ("slug", "rotulo", "tipo", "janela"):
        if not escopo.get(campo):
            erros.append(f"escopo.{campo} ausente")
    janela = escopo.get("janela") or {}
    de, ate = janela.get("de"), janela.get("ate")
    if not isinstance(de, int) or not isinstance(ate, int) or de > ate:
        erros.append(f"escopo.janela inválida: {janela!r}")

    # --- fontes
    fontes: dict[str, dict] = {}
    for f in ev.get("fontes") or []:
        fid = f.get("id")
        if not fid:
            erros.append("fonte sem id")
            continue
        if fid in fontes:
            erros.append(f"fonte com id duplicado: {fid}")
        fontes[fid] = f
        if f.get("tipo") not in ("edital", "prova", "plataforma"):
            erros.append(f"fonte {fid}: tipo inválido ({f.get('tipo')!r})")
        # Rastreabilidade é inegociável: sem URL e data de acesso, o número não vale.
        if not f.get("url"):
            erros.append(f"fonte {fid}: url ausente — todo número precisa ser rastreável")
        if not f.get("acessado_em"):
            erros.append(f"fonte {fid}: acessado_em ausente")
        ano = f.get("ano")
        if not isinstance(ano, int):
            erros.append(f"fonte {fid}: ano ausente ou não inteiro")
        elif isinstance(de, int) and isinstance(ate, int) and not (de <= ano <= ate):
            avisos.append(f"fonte {fid}: ano {ano} fora da janela {de}-{ate} (será ignorada)")
        if f.get("status") not in (None, "ok", "falha", "parcial"):
            erros.append(f"fonte {fid}: status inválido ({f.get('status')!r})")
    if not fontes:
        erros.append("nenhuma fonte declarada")

    # --- nós
    nos: dict[str, dict] = {}
    for n in ev.get("nos") or []:
        nid = n.get("id")
        if not nid:
            erros.append("nó sem id")
            continue
        if nid in nos:
            erros.append(f"nó com id duplicado: {nid}")
        nos[nid] = n
        if not n.get("rotulo"):
            erros.append(f"nó {nid}: rotulo ausente")
        if n.get("nivel") not in NIVEIS:
            erros.append(f"nó {nid}: nivel inválido ({n.get('nivel')!r}); use {NIVEIS}")
        if not n.get("origem"):
            erros.append(f"nó {nid}: origem ausente (edital, prova ou ambos)")
        for eid in (n.get("mencao") or {}):
            if eid not in fontes:
                erros.append(f"nó {nid}: mencao referencia fonte inexistente {eid}")
            elif fontes[eid].get("tipo") != "edital":
                erros.append(f"nó {nid}: mencao referencia {eid}, que não é edital")
        custo = n.get("custo_h")
        if custo is not None and (not isinstance(custo, (int, float)) or custo <= 0):
            erros.append(f"nó {nid}: custo_h inválido ({custo!r})")
    if not nos:
        erros.append("nenhum nó declarado")

    # --- hierarquia
    for nid, n in nos.items():
        pai = n.get("pai")
        if pai and pai not in nos:
            erros.append(f"nó {nid}: pai inexistente ({pai})")
    raizes = [nid for nid, n in nos.items() if not n.get("pai")]
    if nos and not raizes:
        erros.append("hierarquia sem raiz — há ciclo em 'pai'")
    for nid in nos:
        visto, atual = set(), nid
        while atual:
            if atual in visto:
                erros.append(f"ciclo na hierarquia envolvendo {nid}")
                break
            visto.add(atual)
            atual = nos.get(atual, {}).get("pai")
            if atual and atual not in nos:
                break

    # --- questões
    for i, q in enumerate(ev.get("questoes") or []):
        ref = f"questao[{i}]"
        fid = q.get("fonte")
        if fid not in fontes:
            erros.append(f"{ref}: fonte inexistente ({fid})")
        alvos = q.get("nos") or []
        if not alvos:
            erros.append(f"{ref}: sem nós atribuídos")
        for nid in alvos:
            if nid not in nos:
                erros.append(f"{ref}: nó inexistente ({nid})")
        peso = q.get("peso", 1)
        if not isinstance(peso, (int, float)) or peso <= 0:
            erros.append(f"{ref}: peso inválido ({peso!r})")

    # --- arestas declaradas
    for i, a in enumerate(ev.get("arestas") or []):
        ref = f"aresta[{i}]"
        if a.get("de") not in nos:
            erros.append(f"{ref}: nó de origem inexistente ({a.get('de')})")
        if a.get("para") not in nos:
            erros.append(f"{ref}: nó de destino inexistente ({a.get('para')})")
        tipo = a.get("tipo")
        if tipo not in TIPOS_ARESTA_DECLARAVEIS:
            erros.append(
                f"{ref}: tipo {tipo!r} inválido; declaráveis: {sorted(TIPOS_ARESTA_DECLARAVEIS)}"
                " ('contem' e 'coocorre' são derivadas pelo script)"
            )
        forca = a.get("forca")
        if not isinstance(forca, (int, float)) or not 0 < forca <= 1:
            erros.append(f"{ref}: forca deve estar em (0, 1], encontrado {forca!r}")
        if a.get("de") == a.get("para"):
            erros.append(f"{ref}: aresta de um nó para ele mesmo")

    # --- pré-requisitos precisam formar um DAG (é o que dá ordem ao plano de estudos)
    ciclo = detectar_ciclo(
        [(a["de"], a["para"]) for a in (ev.get("arestas") or [])
         if a.get("tipo") == "prerequisito" and a.get("de") in nos and a.get("para") in nos]
    )
    if ciclo:
        erros.append(f"ciclo em 'prerequisito': {' -> '.join(ciclo)} — o grafo precisa ser um DAG")

    # --- cobertura editalícia
    editais = [f for f in fontes.values() if f.get("tipo") == "edital" and f.get("status") != "falha"]
    for e in editais:
        if not any(e["id"] in (n.get("mencao") or {}) for n in nos.values()):
            erros.append(
                f"edital {e['id']} não é mencionado por nenhum nó — "
                "a cobertura do conteúdo programático precisa ser total"
            )
    for nid, n in nos.items():
        origem = n.get("origem") or []
        if "edital" in origem and not (n.get("mencao") or {}):
            erros.append(f"nó {nid}: origem inclui 'edital' mas não há mencao de nenhum edital")

    # --- ajustes
    for nid in (ajustes.get("nos") or {}):
        if nid not in nos:
            avisos.append(f"ajustes.json: nó inexistente ({nid}) — ignorado")

    # --- avisos de qualidade da amostra
    provas_ok = [f for f in fontes.values() if f.get("tipo") == "prova" and f.get("status") != "falha"]
    if len(provas_ok) < 5:
        avisos.append(f"apenas {len(provas_ok)} prova(s) utilizável(is) — confiança global ficará baixa")
    if not editais:
        avisos.append("nenhum edital utilizável — o grafo fica sem a taxonomia oficial")
    falhas = [f["id"] for f in fontes.values() if f.get("status") == "falha"]
    if falhas:
        avisos.append(f"fontes com falha de coleta (não contam): {', '.join(sorted(falhas))}")

    return erros, avisos


def detectar_ciclo(arestas: list[tuple[str, str]]) -> list[str]:
    """Devolve um ciclo (lista de nós) se houver, senão lista vazia. DFS com cores."""
    adj = defaultdict(list)
    for de, para in arestas:
        adj[de].append(para)
    BRANCO, CINZA, PRETO = 0, 1, 2
    cor: dict[str, int] = defaultdict(int)
    pilha: list[str] = []

    def visitar(n: str) -> list[str]:
        cor[n] = CINZA
        pilha.append(n)
        for m in adj[n]:
            if cor[m] == CINZA:
                return pilha[pilha.index(m):] + [m]
            if cor[m] == BRANCO:
                r = visitar(m)
                if r:
                    return r
        pilha.pop()
        cor[n] = PRETO
        return []

    for n in list(adj):
        if cor[n] == BRANCO:
            r = visitar(n)
            if r:
                return r
    return []


# --- Cálculo --------------------------------------------------------------


def calcular(ev: dict, ajustes: dict) -> dict:
    """Aplica todas as fórmulas e devolve a estrutura derivada completa."""
    par = dict(PADROES)
    par.update(ev.get("parametros") or {})
    par.update(ajustes.get("parametros") or {})

    escopo = ev["escopo"]
    janela = escopo["janela"]
    de, ate = janela["de"], janela["ate"]
    ano_ref = ate  # determinismo: nunca a data de execução
    bancas_alvo = {_norm(b) for b in (escopo.get("banca_alvo") or [])}

    fontes = {f["id"]: f for f in ev["fontes"]}
    nos = {n["id"]: n for n in ev["nos"]}
    ordem_decl = [n["id"] for n in ev["nos"]]

    filhos: dict[str, list[str]] = defaultdict(list)
    for nid in ordem_decl:
        pai = nos[nid].get("pai")
        if pai:
            filhos[pai].append(nid)

    def fonte_vale(f: dict) -> bool:
        return f.get("status") != "falha" and isinstance(f.get("ano"), int) and de <= f["ano"] <= ate

    def decaimento(ano: int) -> float:
        return 0.5 ** ((ano_ref - ano) / par["meia_vida_anos"])

    def peso_banca(f: dict) -> float:
        if not bancas_alvo:
            return 1.0
        return par["peso_banca_alvo"] if _norm(f.get("banca")) in bancas_alvo else par["peso_outras_bancas"]

    # 1) incidência direta e contagens cruas
    inc_dir: dict[str, float] = defaultdict(float)
    nq_dir: dict[str, float] = defaultdict(float)      # contagem crua (sem decaimento)
    nq_rec: dict[str, float] = defaultdict(float)      # metade recente da janela
    nq_ant: dict[str, float] = defaultdict(float)      # metade antiga
    questoes_por_no: dict[str, set] = defaultdict(set)  # para coocorrência
    corte_janela = (de + ate) / 2.0
    total_rec = total_ant = 0.0
    questoes_usadas = 0

    for i, q in enumerate(ev.get("questoes") or []):
        f = fontes.get(q["fonte"])
        if not f or not fonte_vale(f):
            continue
        alvos = q["nos"]
        k = len(alvos)
        pq = float(q.get("peso", 1))
        contrib = (pq / k) * decaimento(f["ano"]) * peso_banca(f)
        crua = pq / k
        recente = f["ano"] > corte_janela
        chave = (q["fonte"], q.get("n", i))
        questoes_usadas += 1
        for nid in alvos:
            inc_dir[nid] += contrib
            nq_dir[nid] += crua
            if recente:
                nq_rec[nid] += crua
            else:
                nq_ant[nid] += crua
            if not q.get("agregada"):
                questoes_por_no[nid].add(chave)
        if recente:
            total_rec += pq
        else:
            total_ant += pq

    # 2) cobertura editalícia direta
    editais = [f for f in fontes.values() if f.get("tipo") == "edital" and fonte_vale(f)]
    denom_ed = sum(decaimento(e["ano"]) * peso_banca(e) for e in editais)
    ed_dir: dict[str, float] = defaultdict(float)
    eds_por_no: dict[str, set] = defaultdict(set)
    for nid, n in nos.items():
        mencao = dict(n.get("mencao") or {})
        for eid in (n.get("editais") or []):      # forma abreviada equivale a explícita
            mencao.setdefault(eid, "explicita")
        for eid, forma in mencao.items():
            e = fontes.get(eid)
            if not e or not fonte_vale(e) or e.get("tipo") != "edital":
                continue
            m = par["mencao_generica"] if _norm(forma) == "generica" else par["mencao_explicita"]
            ed_dir[nid] += m * decaimento(e["ano"]) * peso_banca(e)
            eds_por_no[nid].add(eid)
        if denom_ed:
            ed_dir[nid] = min(1.0, ed_dir[nid] / denom_ed)

    # 3) agregação bottom-up (pós-ordem sobre a hierarquia)
    ordem_pos = pos_ordem(ordem_decl, nos, filhos)
    inc_sub: dict[str, float] = defaultdict(float)
    nq_sub: dict[str, float] = defaultdict(float)
    nqr_sub: dict[str, float] = defaultdict(float)
    nqa_sub: dict[str, float] = defaultdict(float)
    ed_sub: dict[str, float] = {}
    eds_sub: dict[str, set] = defaultdict(set)

    for nid in ordem_pos:
        inc_sub[nid] = inc_dir[nid] + sum(inc_sub[c] for c in filhos[nid])
        nq_sub[nid] = nq_dir[nid] + sum(nq_sub[c] for c in filhos[nid])
        nqr_sub[nid] = nq_rec[nid] + sum(nqr_sub[c] for c in filhos[nid])
        nqa_sub[nid] = nq_ant[nid] + sum(nqa_sub[c] for c in filhos[nid])
        # se qualquer descendente está no edital, o ramo está no edital
        ed_sub[nid] = max([ed_dir[nid]] + [ed_sub[c] for c in filhos[nid]])
        eds_sub[nid] = set(eds_por_no[nid]).union(*[eds_sub[c] for c in filhos[nid]]) if filhos[nid] else set(eds_por_no[nid])

    total_inc = sum(inc_dir.values()) or 1.0

    # 4) normalização POR NÍVEL (peso só é comparável dentro do mesmo nível)
    por_nivel: dict[str, list[str]] = defaultdict(list)
    for nid in ordem_decl:
        por_nivel[nos[nid]["nivel"]].append(nid)
    max_inc_nivel = {lv: (max((inc_sub[i] for i in ids), default=0.0) or 1.0)
                     for lv, ids in por_nivel.items()}
    inc_norm = {nid: inc_sub[nid] / max_inc_nivel[nos[nid]["nivel"]] for nid in ordem_decl}

    # 5) confiança
    n_ed = len(editais)
    conf: dict[str, float] = {}
    for nid in ordem_decl:
        amostra = nq_sub[nid] / (nq_sub[nid] + par["k_confianca"])
        if n_ed:
            conf[nid] = 0.7 * amostra + 0.3 * (len(eds_sub[nid]) / n_ed)
        else:
            conf[nid] = amostra

    # 6) encolhimento Beta-binomial dentro do ramo.
    #    Um nó que nunca caiu não é "sem dado": é zero ocorrência em N oportunidades. Estimar
    #    a fatia dele no ramo por (observado + m·uniforme) / (N_ramo + m) puxa o valor para a
    #    média sem apagar a evidência — e, principalmente, sem promover um tópico de
    #    incidência zero ao patamar dos irmãos fortes, que é o que uma média simples faz.
    m_prior = par["m_prior_ramo"]
    inc_aj_abs: dict[str, float] = {}
    for nid in ordem_decl:
        pai = nos[nid].get("pai")
        if not pai:
            inc_aj_abs[nid] = inc_sub[nid]
            continue
        irmaos = filhos[pai]
        n_ramo = sum(inc_sub[m] for m in irmaos)
        p_est = (inc_sub[nid] + m_prior / len(irmaos)) / (n_ramo + m_prior)
        inc_aj_abs[nid] = p_est * n_ramo      # preserva a massa total do ramo
    max_aj_nivel = {lv: (max((inc_aj_abs[i] for i in ids), default=0.0) or 1.0)
                    for lv, ids in por_nivel.items()}
    inc_aj = {nid: inc_aj_abs[nid] / max_aj_nivel[nos[nid]["nivel"]] for nid in ordem_decl}

    # 7) tendência (contagem crua, sem decaimento — senão seria dupla contagem)
    tend: dict[str, str] = {}
    mult: dict[str, float] = {}
    for nid in ordem_decl:
        if nq_sub[nid] < par["min_questoes_tendencia"] or not total_rec or not total_ant:
            tend[nid], mult[nid] = "indefinida", 1.0
            continue
        s_rec = nqr_sub[nid] / total_rec
        s_ant = nqa_sub[nid] / total_ant
        if s_ant == 0:
            tend[nid], mult[nid] = ("alta", par["mult_alta"]) if s_rec > 0 else ("indefinida", 1.0)
            continue
        delta = (s_rec - s_ant) / s_ant
        if delta > par["limiar_tendencia"]:
            tend[nid], mult[nid] = "alta", par["mult_alta"]
        elif delta < -par["limiar_tendencia"]:
            tend[nid], mult[nid] = "queda", par["mult_queda"]
        else:
            tend[nid], mult[nid] = "estavel", par["mult_estavel"]

    # 8) peso final, normalizado por nível
    bruto = {nid: (par["w_incidencia"] * inc_aj[nid] + par["w_edital"] * ed_sub[nid]) * mult[nid]
             for nid in ordem_decl}
    max_bruto_nivel = {lv: (max((bruto[i] for i in ids), default=0.0) or 1.0)
                       for lv, ids in por_nivel.items()}
    peso = {nid: round(100 * bruto[nid] / max_bruto_nivel[nos[nid]["nivel"]])
            for nid in ordem_decl}

    aj_nos = ajustes.get("nos") or {}
    peso_manual = set()
    for nid, ov in aj_nos.items():
        if nid in peso and "peso_manual" in ov:
            peso[nid] = int(ov["peso_manual"])
            peso_manual.add(nid)

    # 9) share (fração da carga total de questões do escopo)
    share = {nid: 100 * inc_sub[nid] / total_inc for nid in ordem_decl}

    # 10) classe por nível, Pareto sobre o share acumulado
    c1, c2, c3 = par["cortes_classe"]
    classe: dict[str, str] = {}
    flags: dict[str, list[str]] = defaultdict(list)
    for lv, ids in por_nivel.items():
        total_lv = sum(share[i] for i in ids) or 1.0
        acc = 0.0
        # O corte olha o acumulado ANTES do item (limite inferior da faixa). Somar primeiro
        # jogaria para a classe seguinte justamente o item grande que cruza a fronteira —
        # um tópico com 30% da prova cairia em C só por vir depois do líder.
        for nid in sorted(ids, key=lambda i: (-peso[i], i)):
            if acc <= c1:
                classe[nid] = "A"
            elif acc <= c2:
                classe[nid] = "B"
            elif acc <= c3:
                classe[nid] = "C"
            else:
                classe[nid] = "D"
            acc += share[nid] / total_lv
    # Empate no peso tem de significar empate na classe. O corte de Pareto pode cair no meio
    # de um grupo de peso idêntico, e ver dois nós com peso 97 em classes diferentes destrói
    # a confiança de quem lê o grafo. Vale a melhor classe do grupo.
    for lv, ids in por_nivel.items():
        grupos: dict[int, list[str]] = defaultdict(list)
        for nid in ids:
            grupos[peso[nid]].append(nid)
        for grupo in grupos.values():
            if len(grupo) > 1:
                melhor = min(classe[i] for i in grupo)   # "A" < "B" < "C" < "D"
                for i in grupo:
                    classe[i] = melhor
    for nid in ordem_decl:
        # guarda 1: quase todo edital cobra → nunca residual ("cai pouco, mas é obrigatório")
        if ed_sub[nid] >= par["limiar_edital_obrigatorio"] and classe[nid] == "D":
            classe[nid] = "C"
            flags[nid].append("piso-edital")
        # guarda 2: amostra fraca não sustenta classe A sozinha
        if conf[nid] < par["limiar_confianca_baixa"] and classe[nid] == "A":
            classe[nid] = "B"
            flags[nid].append("promover_se_confirmado")
    for nid, ov in aj_nos.items():
        if nid in classe and "classe_manual" in ov:
            classe[nid] = str(ov["classe_manual"]).upper()
            flags[nid].append("classe-manual")
    for nid in peso_manual:
        flags[nid].append("peso-manual")

    # 11) custo e ROI
    custo = {}
    for nid in ordem_decl:
        ov = aj_nos.get(nid) or {}
        custo[nid] = float(ov.get("custo_h") or nos[nid].get("custo_h") or par["custo_h_padrao"])
    roi_bruto = {nid: peso[nid] / custo[nid] for nid in ordem_decl}
    max_roi_nivel = {lv: (max((roi_bruto[i] for i in ids), default=0.0) or 1.0)
                     for lv, ids in por_nivel.items()}
    roi = {nid: round(100 * roi_bruto[nid] / max_roi_nivel[nos[nid]["nivel"]]) for nid in ordem_decl}

    # 12) arestas derivadas
    arestas: list[dict] = []
    for nid in ordem_decl:
        pai = nos[nid].get("pai")
        if pai:
            f = inc_sub[nid] / inc_sub[pai] if inc_sub[pai] else 0.0
            arestas.append({"de": pai, "para": nid, "tipo": "contem",
                            "forca": round(f, 3), "evidencia": "hierarquia"})
    for a in ev.get("arestas") or []:
        arestas.append({"de": a["de"], "para": a["para"], "tipo": a["tipo"],
                        "forca": round(float(a["forca"]), 3),
                        "evidencia": a.get("evidencia", "declarada")})
    ids_ord = sorted(questoes_por_no)
    for i, a in enumerate(ids_ord):
        for b in ids_ord[i + 1:]:
            qa, qb = questoes_por_no[a], questoes_por_no[b]
            inter = qa & qb
            if len(inter) < par["coocorrencia_min"]:
                continue
            j = len(inter) / len(qa | qb)
            if j >= par["jaccard_min"]:
                arestas.append({"de": a, "para": b, "tipo": "coocorre", "forca": round(j, 3),
                                "evidencia": f"{len(inter)} questões em comum"})

    # 13) agregados globais
    folhas = [nid for nid in ordem_decl if not filhos[nid]]
    conf_global = (sum(conf[n] * inc_sub[n] for n in folhas) / sum(inc_sub[n] for n in folhas)
                   if sum(inc_sub[n] for n in folhas) else
                   (sum(conf[n] for n in folhas) / len(folhas) if folhas else 0.0))
    cobertura = (len([n for n in ordem_decl if eds_sub[n]]) /
                 len([n for n in ordem_decl if "edital" in (nos[n].get("origem") or [])])
                 if any("edital" in (nos[n].get("origem") or []) for n in ordem_decl) else 0.0)

    derivado = {
        "escopo": escopo,
        "parametros": par,
        "ano_ref": ano_ref,
        "fontes": ev["fontes"],
        "nos": [],
        "arestas": arestas,
        "lacunas": ev.get("lacunas") or [],
        "totais": {
            "nos": len(ordem_decl),
            "folhas": len(folhas),
            "editais": n_ed,
            "provas": len([f for f in fontes.values() if f.get("tipo") == "prova" and fonte_vale(f)]),
            "plataformas": len([f for f in fontes.values() if f.get("tipo") == "plataforma" and fonte_vale(f)]),
            "fontes_com_falha": len([f for f in fontes.values() if f.get("status") == "falha"]),
            "questoes": round(sum(nq_dir.values()), 1),
            "registros_questao": questoes_usadas,
            "confianca_global": round(conf_global, 3),
            "cobertura_edital": round(cobertura, 3),
        },
    }
    for nid in ordem_decl:
        n = nos[nid]
        derivado["nos"].append({
            "id": nid,
            "rotulo": n["rotulo"],
            "nivel": n["nivel"],
            "pai": n.get("pai"),
            "peso": peso[nid],
            "classe": classe[nid],
            "share_pct": round(share[nid], 2),
            "n_questoes": round(nq_sub[nid], 1),
            "edital": round(ed_sub[nid], 3),
            "tendencia": tend[nid],
            "confianca": round(conf[nid], 3),
            "custo_h": custo[nid],
            "roi": roi[nid],
            "tipo_cobranca": n.get("tipo_cobranca") or [],
            "origem": n.get("origem") or [],
            "flags": flags.get(nid) or [],
            "incidencia_norm": round(inc_norm[nid], 4),
            "incidencia_ajustada": round(inc_aj[nid], 4),
            "obs": n.get("obs", ""),
        })
    return derivado


def pos_ordem(ordem_decl: list[str], nos: dict, filhos: dict) -> list[str]:
    """Pós-ordem iterativa: todo filho aparece antes do pai."""
    saida, visitados = [], set()
    raizes = [nid for nid in ordem_decl if not nos[nid].get("pai")]
    for r in raizes:
        pilha = [(r, False)]
        while pilha:
            nid, expandido = pilha.pop()
            if expandido:
                saida.append(nid)
                continue
            if nid in visitados:
                continue
            visitados.add(nid)
            pilha.append((nid, True))
            for c in reversed(filhos[nid]):
                pilha.append((c, False))
    for nid in ordem_decl:  # órfãos de hierarquia quebrada não somem silenciosamente
        if nid not in visitados:
            saida.append(nid)
    return saida


def ordem_topologica(derivado: dict) -> list[str]:
    """Ordem de estudo: respeita pré-requisitos, desempata por peso desc."""
    nos = {n["id"]: n for n in derivado["nos"]}
    dependencias = defaultdict(set)
    dependentes = defaultdict(set)
    for a in derivado["arestas"]:
        if a["tipo"] == "prerequisito":
            dependencias[a["para"]].add(a["de"])
            dependentes[a["de"]].add(a["para"])
    disponiveis = [nid for nid in nos if not dependencias[nid]]
    saida = []
    while disponiveis:
        disponiveis.sort(key=lambda i: (-nos[i]["peso"], i))
        atual = disponiveis.pop(0)
        saida.append(atual)
        for dep in sorted(dependentes[atual]):
            dependencias[dep].discard(atual)
            if not dependencias[dep]:
                disponiveis.append(dep)
    if len(saida) != len(nos):
        erro("ciclo em 'prerequisito' — rode 'validar' para localizar")
    return saida


# --- Render ---------------------------------------------------------------


def _tabela(cabecalho: list[str], linhas: list[list]) -> str:
    out = ["| " + " | ".join(cabecalho) + " |",
           "|" + "|".join("---" for _ in cabecalho) + "|"]
    for linha in linhas:
        out.append("| " + " | ".join("" if c is None else str(c) for c in linha) + " |")
    return "\n".join(out)


def _linha_no(n: dict) -> list:
    return [n["id"], n["rotulo"], n["nivel"], n["pai"] or "—", n["peso"], n["classe"],
            f"{n['share_pct']:.2f}", n["n_questoes"], f"{n['edital']:.2f}",
            n["tendencia"], f"{n['confianca']:.2f}", n["custo_h"], n["roi"],
            "/".join(n["tipo_cobranca"]) or "—", "+".join(n["origem"]),
            " ".join(n["flags"]) or ""]


CAB_NOS = ["id", "rótulo", "nível", "pai", "peso", "classe", "share%", "n_q", "edital",
           "tendência", "confiança", "custo_h", "roi", "cobrança", "origem", "flags"]


def render(derivado: dict) -> str:
    esc = derivado["escopo"]
    tot = derivado["totais"]
    par = derivado["parametros"]
    nos = derivado["nos"]
    por_id = {n["id"]: n for n in nos}
    janela = esc["janela"]

    p = [f"---",
         f"schema: {SCHEMA}",
         f"escopo: {esc['rotulo']}",
         f"slug: {esc['slug']}",
         f"tipo_escopo: {esc['tipo']}",
         f"banca_alvo: [{', '.join(esc.get('banca_alvo') or [])}]",
         f"orgaos_alvo: [{', '.join(esc.get('orgaos_alvo') or [])}]",
         f"janela: {janela['de']}-{janela['ate']}",
         f"ano_ref: {derivado['ano_ref']}",
         f"perfil: {esc.get('perfil', '—')}",
         f"gerado_em: {esc.get('gerado_em', '—')}",
         f"fontes: {{editais: {tot['editais']}, provas: {tot['provas']}, "
         f"plataformas: {tot['plataformas']}, falhas: {tot['fontes_com_falha']}}}",
         f"questoes: {tot['questoes']}",
         f"nos: {tot['nos']}",
         f"cobertura_edital: {tot['cobertura_edital']:.2f}",
         f"confianca_global: {tot['confianca_global']:.2f}",
         "parametros: {" + ", ".join(
             f"{k}: {par[k]}" for k in ("w_incidencia", "w_edital", "meia_vida_anos",
                                        "peso_banca_alvo", "peso_outras_bancas",
                                        "k_confianca", "m_prior_ramo")) + "}",
         "---",
         "",
         f"# Grafo de conteúdo ponderado — {esc['rotulo']}",
         "",
         "> **Artefato derivado. Não editar à mão.** Alterar `evidencias.json` (ou `ajustes.json`)",
         f"> e rodar `python3 .claude/skills/mapear-conteudo/scripts/grafo.py build {esc['slug']}`.",
         ""]

    # 1. como ler
    p += ["## 1. Como ler",
          "",
          "- **peso (0–100)** — prioridade relativa, normalizada **dentro de cada nível**. Só compare",
          "  tópico com tópico, disciplina com disciplina. O topo de cada nível é 100.",
          "- **classe** — **A** concentra os primeiros 50% da carga de questões do nível, **B** vai até 80%,",
          "  **C** até 95%, **D** o resto. É o \"focar mais ou menos\".",
          "- **share%** — fatia da carga total de questões do escopo. As folhas somam ~100%; um nó",
          "  interno mostra o peso do ramo inteiro.",
          "- **confiança** — tamanho e diversidade da amostra. Abaixo de "
          f"{par['limiar_confianca_baixa']:.2f} o número é frágil: trate como hipótese.",
          "- **tendência** — comparação entre as duas metades da janela, sem decaimento.",
          "  `alta`/`queda` movem o peso em ±15%/−12%.",
          "- **flags** — `promover_se_confirmado`: seria A, mas a amostra não sustenta.",
          "  `piso-edital`: cai pouco e mesmo assim é obrigatório. `peso-manual`/`classe-manual`:",
          "  valor sobrescrito em `ajustes.json`, fora da fórmula.",
          ""]

    # 2. prioridades
    folhas = [n for n in nos if not any(m["pai"] == n["id"] for m in nos)]
    top = sorted(folhas, key=lambda n: (-n["peso"], n["id"]))[:20]
    p += ["## 2. Prioridades",
          "",
          f"As {len(top)} folhas de maior peso. Ordem de estudo respeitando pré-requisitos: "
          "`grafo.py ordem`.",
          "",
          _tabela(["#", "id", "tópico", "peso", "classe", "share%", "n_q", "tend", "conf"],
                  [[i + 1, n["id"], n["rotulo"], n["peso"], n["classe"], f"{n['share_pct']:.2f}",
                    n["n_questoes"], n["tendencia"], f"{n['confianca']:.2f}"]
                   for i, n in enumerate(top)]),
          ""]

    # 3. nós
    p += ["## 3. Nós", ""]
    grande = len(nos) > par["max_nos_arquivo_unico"]
    if grande:
        p += [f"São {len(nos)} nós — as tabelas completas estão em `grafo/<disciplina>.md`.",
              "Abaixo, o agregado por disciplina.",
              "",
              _tabela(["id", "disciplina", "peso", "classe", "share%", "n_q", "conf", "nós"],
                      [[n["id"], n["rotulo"], n["peso"], n["classe"], f"{n['share_pct']:.2f}",
                        n["n_questoes"], f"{n['confianca']:.2f}",
                        sum(1 for m in nos if _descende(m, n["id"], por_id))]
                       for n in sorted([x for x in nos if x["nivel"] == "disciplina"],
                                       key=lambda x: (-x["peso"], x["id"]))]),
              ""]
    else:
        p += [_tabela(CAB_NOS, [_linha_no(n) for n in ordenar_hierarquico(nos)]), ""]

    # 4. arestas
    arestas = derivado["arestas"]
    nao_hier = [a for a in arestas if a["tipo"] != "contem"]
    p += ["## 4. Arestas", "",
          f"`contem` ({len(arestas) - len(nao_hier)}) é a hierarquia — a força é a fatia da carga do "
          "pai que o filho carrega; omitida aqui, está implícita na coluna `pai`.",
          ""]
    if nao_hier:
        p += [_tabela(["de", "para", "tipo", "força", "evidência"],
                      [[a["de"], a["para"], a["tipo"], f"{a['forca']:.2f}", a.get("evidencia", "")]
                       for a in sorted(nao_hier, key=lambda a: (a["tipo"], -a["forca"], a["de"]))]),
              ""]
    else:
        p += ["Nenhuma aresta além da hierarquia.", ""]

    # 5. mermaid — cada nó é declarado uma única vez, senão a primeira declaração vence
    # e o rótulo das demais é silenciosamente descartado.
    p += ["## 5. Mapa (classes A e B)", ""]
    destaque = {n["id"] for n in nos if n["classe"] in ("A", "B")}
    if destaque:
        p += ["```mermaid", "graph TD"]
        for n in nos:
            if n["id"] in destaque:
                p.append(f'  {_mid(n["id"])}["{n["rotulo"].replace(chr(34), chr(39))}'
                         f'<br/>{n["peso"]}"]')
        for a in arestas:
            if a["tipo"] == "contem" and a["de"] in destaque and a["para"] in destaque:
                p.append(f"  {_mid(a['de'])} --> {_mid(a['para'])}")
        for a in nao_hier:
            if a["tipo"] == "prerequisito" and a["de"] in destaque and a["para"] in destaque:
                p.append(f"  {_mid(a['de'])} -.pré.-> {_mid(a['para'])}")
        criticos = [_mid(n["id"]) for n in nos if n["classe"] == "A"]
        if criticos:
            p.append("  classDef prioridade fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;")
            p.append(f"  class {','.join(criticos)} prioridade;")
        p += ["```", ""]
    else:
        p += ["Nenhum nó em classe A ou B — amostra insuficiente para destacar prioridades.", ""]

    # 6. lacunas
    p += ["## 6. Lacunas e ressalvas", ""]
    if derivado["lacunas"]:
        for l in derivado["lacunas"]:
            p.append(f"- **{l.get('o_que', '?')}** — {l.get('impacto', '')}")
    else:
        p.append("Nenhuma lacuna registrada.")
    frageis = [n for n in nos if n["confianca"] < par["limiar_confianca_baixa"]]
    if frageis:
        p += ["", f"{len(frageis)} nó(s) com confiança abaixo de {par['limiar_confianca_baixa']:.2f}: "
              + ", ".join(n["id"] for n in sorted(frageis, key=lambda x: x["id"])[:30])
              + ("…" if len(frageis) > 30 else "")
              + ". O peso deles é hipótese, não medição."]
    if tot["fontes_com_falha"]:
        p += ["", f"{tot['fontes_com_falha']} fonte(s) falharam na coleta e **não** entraram no cálculo "
              "(ver seção 7). Nenhum valor foi estimado no lugar delas."]
    p.append("")

    # 7. fontes
    p += ["## 7. Fontes", "",
          _tabela(["id", "tipo", "banca", "órgão", "ano", "cargo", "n_q", "status", "url", "acessado"],
                  [[f["id"], f.get("tipo", ""), f.get("banca", "—"), f.get("orgao", "—"),
                    f.get("ano", "—"), f.get("cargo", "—"), f.get("n_questoes_escopo", "—"),
                    f.get("status", "ok"), f"[link]({f.get('url', '')})", f.get("acessado_em", "—")]
                   for f in sorted(derivado["fontes"], key=lambda f: (f.get("tipo", ""), -(f.get("ano") or 0), f["id"]))]),
          ""]

    # 8. contrato
    p += ["## 8. Contrato de consumo", "",
          "Skills consumidoras devem ler por script, não parseando este markdown:",
          "",
          "```bash",
          f"python3 .claude/skills/mapear-conteudo/scripts/grafo.py consultar {esc['slug']} --classe A --json   # nós prioritários",
          f"python3 .claude/skills/mapear-conteudo/scripts/grafo.py ordem {esc['slug']} --json                  # ordem de estudo (DAG)",
          f"python3 .claude/skills/mapear-conteudo/scripts/grafo.py no {esc['slug']} <id>                       # ficha de um nó",
          f"python3 .claude/skills/mapear-conteudo/scripts/grafo.py resumo {esc['slug']}                        # cobertura e confiança",
          "```",
          "",
          "Campos garantidos por nó: `id`, `rotulo`, `nivel`, `pai`, `peso`, `classe`, `share_pct`,",
          "`n_questoes`, `edital`, `tendencia`, `confianca`, `custo_h`, `roi`, `tipo_cobranca`,",
          "`origem`, `flags`. Os `id` são estáveis entre execuções enquanto o nó existir em",
          "`evidencias.json` — use `id`, nunca o rótulo, como chave.",
          ""]
    return "\n".join(p) + "\n"


def _mid(nid: str) -> str:
    """Id seguro para mermaid (sem pontos)."""
    return "n" + nid.replace(".", "_").replace("-", "_")


def _descende(no: dict, ancestral: str, por_id: dict) -> bool:
    atual = no.get("pai")
    while atual:
        if atual == ancestral:
            return True
        atual = (por_id.get(atual) or {}).get("pai")
    return False


def ordenar_hierarquico(nos: list[dict]) -> list[dict]:
    """Pré-ordem por peso: pai, depois filhos do mais pesado ao mais leve."""
    por_pai = defaultdict(list)
    for n in nos:
        por_pai[n["pai"]].append(n)
    saida: list[dict] = []

    def desce(pai):
        for n in sorted(por_pai[pai], key=lambda x: (-x["peso"], x["id"])):
            saida.append(n)
            desce(n["id"])

    desce(None)
    vistos = {n["id"] for n in saida}
    saida.extend(n for n in nos if n["id"] not in vistos)
    return saida


def render_disciplinas(derivado: dict, destino: Path) -> list[Path]:
    """Para escopos grandes: uma tabela completa por disciplina."""
    nos = derivado["nos"]
    por_id = {n["id"]: n for n in nos}
    escritos = []
    destino.mkdir(parents=True, exist_ok=True)
    for d in [n for n in nos if n["nivel"] == "disciplina"]:
        ramo = [d] + [n for n in nos if _descende(n, d["id"], por_id)]
        slug = _slug(d["rotulo"])
        caminho = destino / f"{slug}.md"
        caminho.write_text(
            f"# {d['rotulo']} — peso {d['peso']} ({d['classe']})\n\n"
            f"Recorte de `../grafo.md`. Artefato derivado, não editar à mão.\n\n"
            + _tabela(CAB_NOS, [_linha_no(n) for n in ordenar_hierarquico(ramo)]) + "\n",
            encoding="utf-8")
        escritos.append(caminho)
    return escritos


def _slug(texto: str) -> str:
    base = _norm(texto)
    return "".join(c if c.isalnum() else "-" for c in base).strip("-").replace("--", "-") or "sem-nome"


# --- Comandos -------------------------------------------------------------


def cmd_init(args) -> None:
    d = dir_grafo(args.slug, args.raiz)
    alvo = d / "evidencias.json"
    if alvo.exists() and not args.forcar:
        erro(f"{alvo} já existe — use --forcar para sobrescrever")
    de, ate = (int(x) for x in args.janela.split("-"))
    d.mkdir(parents=True, exist_ok=True)
    (d / "fontes").mkdir(exist_ok=True)
    esqueleto = {
        "schema": SCHEMA,
        "escopo": {
            "slug": args.slug,
            "rotulo": args.escopo,
            "tipo": args.tipo,
            "banca_alvo": args.banca or [],
            "orgaos_alvo": args.orgao or [],
            "janela": {"de": de, "ate": ate},
            "perfil": args.perfil,
            "gerado_em": args.data or "",
        },
        "parametros": {},
        "fontes": [],
        "nos": [],
        "questoes": [],
        "arestas": [],
        "lacunas": [],
    }
    alvo.write_text(json.dumps(esqueleto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"criado: {alvo}")
    print(f"  escopo ....... {args.escopo} ({args.tipo})")
    print(f"  janela ....... {de}-{ate}   ano_ref={ate}")
    print(f"  banca-alvo ... {', '.join(args.banca or []) or '(nenhuma — todas pesam igual)'}")


def cmd_validar(args) -> None:
    _, ev, ajustes = carregar(args.slug, args.raiz)
    erros, avisos = validar(ev, ajustes)
    for a in avisos:
        print(f"aviso: {a}", file=sys.stderr)
    if erros:
        for e in erros:
            print(f"ERRO: {e}", file=sys.stderr)
        print(f"\n{len(erros)} erro(s), {len(avisos)} aviso(s) — build bloqueado.", file=sys.stderr)
        raise SystemExit(1)
    print(f"validação OK — {len(ev.get('nos') or [])} nós, {len(ev.get('fontes') or [])} fontes, "
          f"{len(ev.get('questoes') or [])} registros de questão, {len(avisos)} aviso(s)")


def cmd_build(args) -> None:
    d, ev, ajustes = carregar(args.slug, args.raiz)
    erros, avisos = validar(ev, ajustes)
    for a in avisos:
        print(f"aviso: {a}", file=sys.stderr)
    if erros:
        for e in erros:
            print(f"ERRO: {e}", file=sys.stderr)
        erro(f"{len(erros)} erro(s) de validação — corrija evidencias.json antes do build")

    derivado = calcular(ev, ajustes)
    (d / "grafo.md").write_text(render(derivado), encoding="utf-8")
    (d / "derivado.json").write_text(
        json.dumps(derivado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    extras = []
    if derivado["totais"]["nos"] > derivado["parametros"]["max_nos_arquivo_unico"]:
        extras = render_disciplinas(derivado, d / "grafo")

    tot = derivado["totais"]
    print(f"grafo: {d / 'grafo.md'}")
    print(f"  nós ................ {tot['nos']} ({tot['folhas']} folhas)")
    print(f"  fontes ............. {tot['editais']} editais, {tot['provas']} provas, "
          f"{tot['plataformas']} plataformas"
          + (f", {tot['fontes_com_falha']} com falha" if tot['fontes_com_falha'] else ""))
    print(f"  questões ........... {tot['questoes']}")
    print(f"  cobertura edital ... {tot['cobertura_edital']:.2f}")
    print(f"  confiança global ... {tot['confianca_global']:.2f}")
    for c in ("A", "B", "C", "D"):
        n = len([x for x in derivado["nos"] if x["classe"] == c])
        print(f"  classe {c} .......... {n} nó(s)")
    if extras:
        print(f"  recortes ........... {len(extras)} arquivo(s) em {d / 'grafo'}")
    if tot["confianca_global"] < 0.4:
        print("  >> confiança global baixa: amplie a amostra de provas antes de usar "
              "este grafo para decidir o que estudar.", file=sys.stderr)


def _filtrar(derivado: dict, args) -> list[dict]:
    por_id = {n["id"]: n for n in derivado["nos"]}
    saida = derivado["nos"]
    if args.classe:
        classes = {c.upper() for c in args.classe}
        saida = [n for n in saida if n["classe"] in classes]
    if args.nivel:
        saida = [n for n in saida if n["nivel"] in set(args.nivel)]
    if args.disciplina:
        alvo = _norm(args.disciplina)
        raizes = [n["id"] for n in derivado["nos"]
                  if _norm(n["rotulo"]) == alvo or n["id"] == args.disciplina]
        if not raizes:
            erro(f"disciplina não encontrada: {args.disciplina}")
        saida = [n for n in saida
                 if n["id"] in raizes or any(_descende(n, r, por_id) for r in raizes)]
    if args.folhas:
        com_filho = {n["pai"] for n in derivado["nos"] if n["pai"]}
        saida = [n for n in saida if n["id"] not in com_filho]
    saida = sorted(saida, key=lambda n: (-n["peso"], n["id"]))
    if args.top:
        saida = saida[:args.top]
    return saida


def cmd_consultar(args) -> None:
    _, ev, ajustes = carregar(args.slug, args.raiz)
    derivado = calcular(ev, ajustes)
    sel = _filtrar(derivado, args)
    if args.json:
        print(json.dumps(sel, ensure_ascii=False, indent=2))
        return
    if not sel:
        print("nenhum nó corresponde ao filtro")
        return
    print(_tabela(["id", "rótulo", "nível", "peso", "classe", "share%", "n_q", "conf", "custo_h", "roi"],
                  [[n["id"], n["rotulo"], n["nivel"], n["peso"], n["classe"], f"{n['share_pct']:.2f}",
                    n["n_questoes"], f"{n['confianca']:.2f}", n["custo_h"], n["roi"]] for n in sel]))


def cmd_no(args) -> None:
    _, ev, ajustes = carregar(args.slug, args.raiz)
    derivado = calcular(ev, ajustes)
    por_id = {n["id"]: n for n in derivado["nos"]}
    n = por_id.get(args.id)
    if not n:
        erro(f"nó não encontrado: {args.id}")
    if args.json:
        vizinhos = [a for a in derivado["arestas"] if args.id in (a["de"], a["para"])]
        print(json.dumps({**n, "arestas": vizinhos}, ensure_ascii=False, indent=2))
        return
    print(f"{n['id']} — {n['rotulo']}")
    print(f"  nível .......... {n['nivel']}" + (f"  (pai: {n['pai']})" if n["pai"] else ""))
    print(f"  peso ........... {n['peso']} (classe {n['classe']}, roi {n['roi']})")
    print(f"  share .......... {n['share_pct']:.2f}% da carga de questões")
    print(f"  amostra ........ {n['n_questoes']} questões, confiança {n['confianca']:.2f}")
    print(f"  edital ......... {n['edital']:.2f}   tendência: {n['tendencia']}")
    print(f"  custo estimado . {n['custo_h']} h")
    if n["tipo_cobranca"]:
        print(f"  cobrança ....... {', '.join(n['tipo_cobranca'])}")
    if n["flags"]:
        print(f"  flags .......... {', '.join(n['flags'])}")
    if n["obs"]:
        print(f"  obs ............ {n['obs']}")
    pre = [a["de"] for a in derivado["arestas"] if a["tipo"] == "prerequisito" and a["para"] == n["id"]]
    if pre:
        print(f"  pré-requisitos . {', '.join(f'{p} ({por_id[p]['rotulo']})' for p in pre)}")
    co = [(a["para"] if a["de"] == n["id"] else a["de"], a["forca"])
          for a in derivado["arestas"] if a["tipo"] == "coocorre" and n["id"] in (a["de"], a["para"])]
    if co:
        print("  cai junto com .. " + ", ".join(f"{i} ({f:.2f})" for i, f in sorted(co, key=lambda x: -x[1])[:5]))


def cmd_ordem(args) -> None:
    _, ev, ajustes = carregar(args.slug, args.raiz)
    derivado = calcular(ev, ajustes)
    por_id = {n["id"]: n for n in derivado["nos"]}
    seq = ordem_topologica(derivado)
    if args.folhas:
        com_filho = {n["pai"] for n in derivado["nos"] if n["pai"]}
        seq = [i for i in seq if i not in com_filho]
    if args.json:
        print(json.dumps([por_id[i] for i in seq], ensure_ascii=False, indent=2))
        return
    acc = 0.0
    for i, nid in enumerate(seq, 1):
        n = por_id[nid]
        acc += n["share_pct"]
        print(f"{i:3d}. [{n['classe']}] {nid:<12} {n['rotulo'][:52]:<52} "
              f"peso {n['peso']:>3}  {n['custo_h']:>4}h  acum {acc:5.1f}%")


def cmd_resumo(args) -> None:
    _, ev, ajustes = carregar(args.slug, args.raiz)
    erros, avisos = validar(ev, ajustes)
    derivado = calcular(ev, ajustes)
    esc, tot = derivado["escopo"], derivado["totais"]
    if args.json:
        print(json.dumps({"escopo": esc, "totais": tot, "erros": erros, "avisos": avisos},
                         ensure_ascii=False, indent=2))
        return
    print(f"{esc['rotulo']} ({esc['tipo']}) — janela {esc['janela']['de']}-{esc['janela']['ate']}")
    print(f"  banca-alvo ......... {', '.join(esc.get('banca_alvo') or []) or '—'}")
    print(f"  nós ................ {tot['nos']} ({tot['folhas']} folhas)")
    print(f"  fontes ............. {tot['editais']} editais, {tot['provas']} provas, "
          f"{tot['plataformas']} plataformas, {tot['fontes_com_falha']} falhas")
    print(f"  questões ........... {tot['questoes']}")
    print(f"  cobertura edital ... {tot['cobertura_edital']:.2f}")
    print(f"  confiança global ... {tot['confianca_global']:.2f}")
    for c in ("A", "B", "C", "D"):
        ids = [x for x in derivado["nos"] if x["classe"] == c]
        share = sum(x["share_pct"] for x in ids if not any(m["pai"] == x["id"] for m in derivado["nos"]))
        print(f"  classe {c} .......... {len(ids):>3} nó(s), {share:5.1f}% da carga")
    frageis = [n for n in derivado["nos"] if n["confianca"] < derivado["parametros"]["limiar_confianca_baixa"]]
    print(f"  confiança frágil ... {len(frageis)} nó(s)")
    for l in derivado["lacunas"]:
        print(f"  lacuna ............. {l.get('o_que', '')}")
    if erros:
        print(f"\n>> {len(erros)} erro(s) de validação pendente(s) — rode 'validar'.", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="grafo.py",
        description="Motor determinístico do grafo de conteúdo ponderado para concursos.")
    ap.add_argument("--raiz", type=Path, default=None,
                    help="raiz do projeto (padrão: deduzida do caminho do script)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="cria o evidencias.json esqueleto")
    s.add_argument("slug")
    s.add_argument("--escopo", required=True, help="rótulo legível, ex: 'Direito Constitucional'")
    s.add_argument("--tipo", default="disciplina", choices=["disciplina", "cargo", "area"])
    s.add_argument("--banca", action="append", help="banca-alvo (repetível)")
    s.add_argument("--orgao", action="append", help="órgão-alvo (repetível)")
    s.add_argument("--janela", default="2021-2026", help="ex: 2021-2026")
    s.add_argument("--perfil", default="profundo", choices=["rapido", "padrao", "profundo"])
    s.add_argument("--data", help="data de geração (AAAA-MM-DD)")
    s.add_argument("--forcar", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("validar", help="checa schema, DAG, rastreabilidade e cobertura")
    s.add_argument("slug")
    s.set_defaults(func=cmd_validar)

    s = sub.add_parser("build", help="calcula os pesos e escreve grafo.md")
    s.add_argument("slug")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("consultar", help="recorte de nós para skills consumidoras")
    s.add_argument("slug")
    s.add_argument("--classe", action="append", help="A, B, C ou D (repetível)")
    s.add_argument("--nivel", action="append", choices=NIVEIS)
    s.add_argument("--disciplina", help="limita ao ramo de uma disciplina (id ou rótulo)")
    s.add_argument("--top", type=int)
    s.add_argument("--folhas", action="store_true", help="só nós sem filhos")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_consultar)

    s = sub.add_parser("no", help="ficha completa de um nó")
    s.add_argument("slug")
    s.add_argument("id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_no)

    s = sub.add_parser("ordem", help="ordem de estudo (topológica pelos pré-requisitos)")
    s.add_argument("slug")
    s.add_argument("--folhas", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_ordem)

    s = sub.add_parser("resumo", help="estatísticas, cobertura, confiança e lacunas")
    s.add_argument("slug")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_resumo)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
