#!/usr/bin/env python3
"""Cliente da conta QConcursos (Playwright + Chrome persistente).

Baixa o que a sessão autenticada já libera: questões, gabaritos, videoaulas,
editais/provas e Raio X. Credenciais só de .env / ambiente — nunca impressas.

    qc.py status
    qc.py login
    qc.py raiox [--banca] [--disciplina] [--de] [--ate]
    qc.py questoes [--disciplina] [--assunto] [--banca] [--ano] [--orgao] [--max N] [--pagina N]
    qc.py questao <id>
    qc.py aulas [--disciplina] [--assunto] [--max N]
    qc.py editais [--orgao] [--ano] [--max N]
    qc.py prova --id SLUG
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse


def raiz_projeto() -> Path:
    return Path(__file__).resolve().parents[4]


def _reexec_venv() -> None:
    venv = raiz_projeto() / ".venv" / "bin" / "python"
    if venv.is_file() and Path(sys.executable).resolve() != venv.resolve():
        os.execv(str(venv), [str(venv), *sys.argv])


try:
    from playwright.sync_api import TimeoutError as PwTimeout
    from playwright.sync_api import sync_playwright
except ImportError:
    _reexec_venv()
    print(
        "ERRO: Playwright ausente. Na raiz do projeto:\n"
        "  uv venv .venv && uv pip install --python .venv/bin/python playwright\n"
        "  .venv/bin/playwright install chromium",
        file=sys.stderr,
    )
    raise SystemExit(1)


CACHE = Path.home() / ".cache" / "concurso"
PERFIL = CACHE / "qc-profile"
DADOS = CACHE / "qconcursos"
BASE_PADRAO = "https://www.qconcursos.com"
STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR','pt','en-US']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = window.chrome || { runtime: {} };
"""


def erro(msg: str) -> None:
    print(f"ERRO: {msg}", file=sys.stderr)
    raise SystemExit(1)


def aviso(msg: str) -> None:
    print(f"aviso: {msg}", file=sys.stderr)


def emitir(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def slugificar(texto: str) -> str:
    n = unicodedata.normalize("NFKD", texto or "")
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n.lower()).strip("-")
    return n


def ler_env() -> dict:
    out = {}
    env_path = raiz_projeto() / ".env"
    if env_path.is_file():
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            s = linha.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("QCONCURSOS_LOGIN", "QCONCURSOS_PASSWORD", "QCONCURSOS_URL"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    return out


def qps_delay() -> None:
    try:
        qps = float(os.environ.get("QC_QPS", "0.4"))
    except ValueError:
        qps = 0.4
    if qps <= 0:
        return
    time.sleep((1.0 / qps) + random.uniform(0.15, 0.6))


def gravar_cache(tipo: str, chave: str, dados) -> Path:
    d = DADOS / tipo
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{slugificar(chave) or 'item'}.json"
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return p


# --- Navegador ------------------------------------------------------------


def chrome_channel() -> str | None:
    for c in ("/usr/bin/google-chrome-stable", "/usr/bin/google-chrome",
              "/opt/google/chrome/chrome"):
        if Path(c).is_file():
            return "chrome"
    return None


def abrir_contexto(headed: bool | None = None):
    PERFIL.mkdir(parents=True, exist_ok=True)
    DADOS.mkdir(parents=True, exist_ok=True)
    if headed is None:
        headed = os.environ.get("QC_HEADED", "1") not in ("0", "false", "False")
    canal = chrome_channel()
    kwargs = dict(
        user_data_dir=str(PERFIL),
        headless=not headed,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        viewport={"width": 1366, "height": 768},
        args=["--disable-blink-features=AutomationControlled", "--no-first-run"],
        ignore_default_args=["--enable-automation"],
    )
    if canal:
        kwargs["channel"] = canal
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(**kwargs)
    ctx.add_init_script(STEALTH)
    return pw, ctx


def pagina(ctx):
    return ctx.pages[0] if ctx.pages else ctx.new_page()


def ir(page, url: str, espera: float = 2.0):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    esperar_cloudflare(page)
    if espera:
        page.wait_for_timeout(int(espera * 1000))


def esperar_cloudflare(page, teto: float = 40.0) -> None:
    fim = time.time() + teto
    while time.time() < fim:
        titulo = (page.title() or "").lower()
        corpo = ""
        try:
            corpo = page.inner_text("body")[:400].lower()
        except Exception:
            pass
        if "just a moment" in titulo or "performing security verification" in corpo:
            page.wait_for_timeout(1500)
            continue
        return
    erro("Cloudflare não liberou a página. Rode `qc.py login` em modo headed (QC_HEADED=1).")


def base_url() -> str:
    return (ler_env().get("QCONCURSOS_URL") or BASE_PADRAO).rstrip("/")


def logado(page) -> bool:
    try:
        if page.locator("#login_email").count():
            return False
        corpo = page.inner_text("body")
    except Exception:
        return False
    marcas = ("Sair", "Meu Painel", "ASSINATURA", "Mesa de estudos", "Meus benefícios")
    return any(m in corpo for m in marcas)


def garantir_login(page, obrigatorio: bool = True) -> bool:
    ir(page, f"{base_url()}/usuario", espera=1.5)
    if logado(page):
        return True
    env = ler_env()
    user, senha = env.get("QCONCURSOS_LOGIN"), env.get("QCONCURSOS_PASSWORD")
    if not user or not senha:
        if obrigatorio:
            erro("sem QCONCURSOS_LOGIN/PASSWORD no .env — caindo fora. Use a web pública.")
        return False
    ir(page, f"{base_url()}/conta/entrar", espera=2.0)
    if page.locator("#login_email").count() == 0:
        ir(page, f"{base_url()}/usuario", espera=1.5)
        return logado(page)
    page.fill("#login_email", user)
    page.fill("#login_password", senha)
    page.click("#btnLogin")
    page.wait_for_timeout(4000)
    esperar_cloudflare(page)
    if not logado(page):
        ir(page, f"{base_url()}/usuario", espera=1.5)
    if not logado(page):
        if obrigatorio:
            erro("login recusado ou paywall. Confira a conta; senha nunca é exibida.")
        return False
    return True


def perfil_conta(page) -> dict:
    corpo = page.inner_text("body")
    plano = None
    m = re.search(r"ASSINATURA\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+)", corpo)
    if m:
        plano = m.group(1).strip()
    nome = None
    if "Paulo" in corpo:
        m2 = re.search(r"(Paulo[^\n|]{0,40})", corpo)
        nome = m2.group(1).strip() if m2 else None
    return {"logado": True, "plano": plano, "nome": nome, "url": page.url}


# --- Extração de questões -------------------------------------------------


JS_CARDS = """
() => Array.from(document.querySelectorAll('.js-question-item')).map(el => {
  const q = el.querySelector('.js-question');
  const a = el.querySelector('a[href*="/questoes/"]');
  const texto = el.innerText || '';
  const ano = (texto.match(/Ano:\\s*(\\d{4})/) || [])[1] || null;
  const banca = (texto.match(/Banca:\\s*([^\\n]+?)(?:\\s+Órgão:|$)/) || [])[1] || null;
  const orgao = (texto.match(/Órgão:\\s*([^\\n]+?)(?:\\s+Prova:|$)/) || [])[1] || null;
  const prova = (texto.match(/Prova:\\s*([^\\n]+)/) || [])[1] || null;
  const codigo = (texto.match(/Q\\d+/) || [])[0] || null;
  return {
    id: q ? (q.dataset.questionId || null) : null,
    disciplina_id: q ? (q.dataset.disciplineId || null) : null,
    url: a ? a.getAttribute('href') : null,
    codigo,
    ano: ano ? Number(ano) : null,
    banca: banca && banca.trim(),
    orgao: orgao && orgao.trim(),
    prova: prova && prova.trim(),
    texto,
  };
})
"""


def parse_card(bruto: dict, hoje: str) -> dict:
    texto = bruto.get("texto") or ""
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    disciplina = None
    assuntos: list[str] = []
    enunciado_linhas: list[str] = []
    alts: dict[str, str] = {}
    fase = "meta"
    letra_atual = None
    for ln in linhas:
        if re.fullmatch(r"Q\d+", ln) or re.fullmatch(r"\d+", ln):
            continue
        if ln.startswith("Ano:") or ln.startswith("Banca:"):
            fase = "enunciado"
            continue
        if ln == "Alternativas":
            fase = "alts"
            continue
        if ln in ("Responder", "Gabarito Comentado", "Estatísticas", "Cadernos",
                  "Criar anotações", "Notificar Erro") or ln.startswith("Aulas") or ln.startswith("Comentários"):
            fase = "fim"
            continue
        if fase == "meta":
            if disciplina is None and not ln.endswith(","):
                disciplina = ln.rstrip(",")
            else:
                assuntos.append(ln.rstrip(" ,"))
        elif fase == "enunciado":
            enunciado_linhas.append(ln)
        elif fase == "alts":
            if re.fullmatch(r"[A-E]", ln):
                letra_atual = ln
                alts[letra_atual] = ""
            elif letra_atual:
                alts[letra_atual] = (alts[letra_atual] + " " + ln).strip()
    url = bruto.get("url") or ""
    if url and url.startswith("/"):
        url = urljoin(base_url() + "/", url.lstrip("/"))
    slug = None
    m = re.search(r"/questoes/([^/?#]+)", url or "")
    if m:
        slug = m.group(1)
    return {
        "id": bruto.get("id") or slug,
        "slug": slug,
        "codigo": bruto.get("codigo"),
        "url": url,
        "disciplina": disciplina,
        "assuntos": [a for a in assuntos if a],
        "ano": bruto.get("ano"),
        "banca": bruto.get("banca"),
        "orgao": bruto.get("orgao"),
        "prova": bruto.get("prova"),
        "enunciado": " ".join(enunciado_linhas).strip() or None,
        "alternativas": alts or None,
        "coletado_em": hoje,
    }


def url_questoes(args) -> str:
    root = base_url() + "/questoes-de-concursos"
    disciplina = getattr(args, "disciplina", None)
    assunto = getattr(args, "assunto", None)
    banca = getattr(args, "banca", None)
    orgao = getattr(args, "orgao", None)
    if disciplina:
        slug = slug_disciplina(disciplina)
        if assunto:
            return f"{root}/disciplinas/{slug}/{slugificar(assunto)}"
        return f"{root}/disciplinas/{slug}/questoes"
    if banca:
        return f"{root}/bancas/{slugificar(banca)}/questoes"
    if orgao:
        return f"{root}/institutos/{slugificar(orgao)}/questoes"
    return f"{root}/questoes"


def slug_disciplina(nome: str) -> str:
    s = slugificar(nome)
    # QConcursos prefixa a área: direito-direito-constitucional, letras-portugues
    conhecidos = {
        "direito-constitucional": "direito-direito-constitucional",
        "direito-administrativo": "direito-direito-administrativo",
        "portugues": "letras-portugues",
        "lingua-portuguesa": "letras-portugues",
        "raciocinio-logico": "exatas-raciocinio-logico",
        "matematica": "exatas-matematica",
        "informatica": "informatica-informatica",
    }
    return conhecidos.get(s, s)


def coletar_pagina_questoes(page) -> list[dict]:
    try:
        brutos = page.evaluate(JS_CARDS)
    except Exception:
        brutos = []
    hoje = date.today().isoformat()
    return [parse_card(b, hoje) for b in brutos]


def cmd_questoes(args) -> None:
    pw, ctx = abrir_contexto()
    try:
        page = pagina(ctx)
        garantir_login(page)
        url = url_questoes(args)
        if args.pagina and args.pagina > 1:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}page={args.pagina}"
        ir(page, url, espera=2.5)
        itens: list[dict] = []
        visto: set[str] = set()
        teto = args.max or 20
        pagina_n = args.pagina or 1
        while len(itens) < teto:
            lote = coletar_pagina_questoes(page)
            if not lote:
                break
            for it in lote:
                chave = str(it.get("id") or it.get("url"))
                if chave in visto:
                    continue
                visto.add(chave)
                itens.append(it)
                if len(itens) >= teto:
                    break
            if len(itens) >= teto:
                break
            prox = page.locator("a[rel=next], a:has-text('Próxima'), a:has-text('proxima')")
            if prox.count() == 0:
                pagina_n += 1
                sep = "&" if "?" in url.split("?")[0] else "?"
                base = re.sub(r"[?&]page=\d+", "", url)
                ir(page, f"{base}{sep}page={pagina_n}", espera=2.0)
                qps_delay()
                if not coletar_pagina_questoes(page):
                    break
                continue
            href = prox.first.get_attribute("href")
            if not href:
                break
            qps_delay()
            ir(page, urljoin(page.url, href), espera=2.0)
        for it in itens:
            if it.get("id"):
                gravar_cache("questoes", str(it["id"]), it)
        emitir({
            "fonte": page.url,
            "filtro": {k: getattr(args, k) for k in
                       ("disciplina", "assunto", "banca", "ano", "orgao")
                       if getattr(args, k, None)},
            "n": len(itens),
            "questoes": itens[:teto],
        })
    finally:
        ctx.close()
        pw.stop()


def cmd_questao(args) -> None:
    pw, ctx = abrir_contexto()
    try:
        page = pagina(ctx)
        garantir_login(page)
        ident = args.id
        if ident.startswith("http"):
            url = ident
        elif re.fullmatch(r"Q?\d+", ident):
            # código Q4237344 — busca na listagem não resolve o slug; tenta o uuid se parecer
            url = f"{base_url()}/questoes-de-concursos/questoes/{ident.lstrip('Qq')}"
        else:
            url = f"{base_url()}/questoes-de-concursos/questoes/{ident}"
        ir(page, url, espera=2.5)
        # gabarito comentado, se o botão existir
        botao = page.locator("text=Gabarito Comentado")
        if botao.count():
            try:
                botao.first.click(timeout=3000)
                page.wait_for_timeout(1500)
            except Exception:
                pass
        texto = page.inner_text("body")
        aulas = []
        for a in page.locator("a[href*='/aulas'], a[href*='/playlist'], a[href*='/cursos']").all()[:15]:
            href = a.get_attribute("href") or ""
            tit = (a.inner_text() or "").strip()
            if href and tit:
                aulas.append({"titulo": tit[:200], "url": urljoin(page.url, href)})
        item = {
            "id": ident,
            "url": page.url,
            "titulo": page.title(),
            "texto": texto[:12000],
            "aulas_relacionadas": aulas,
            "coletado_em": date.today().isoformat(),
        }
        # tenta reaproveitar o parser de card se a página tiver o mesmo markup
        cards = coletar_pagina_questoes(page)
        if cards:
            item.update({k: v for k, v in cards[0].items() if v})
        gravar_cache("questoes", ident, item)
        emitir(item)
    finally:
        ctx.close()
        pw.stop()


# --- Aulas / Raio X / Editais --------------------------------------------


def _tokens(texto: str) -> set[str]:
    return {t for t in slugificar(texto).split("-") if len(t) > 3}


def cmd_aulas(args) -> None:
    pw, ctx = abrir_contexto()
    try:
        page = pagina(ctx)
        garantir_login(page)
        consulta = " ".join(x for x in (args.disciplina, args.assunto) if x)
        ir(page, f"{base_url()}/questoes-de-concursos/aulas", espera=2.5)
        if consulta:
            caixa = page.locator("input[type=search], input[placeholder*='Busca'], input[placeholder*='busca']")
            if caixa.count():
                caixa.first.fill(consulta)
                caixa.first.press("Enter")
                page.wait_for_timeout(2500)
        alvo = _tokens(consulta)
        aulas = []
        visto = set()
        ruido = ("banco-do-brasil", "seguridade-social-concurso-inss",
                 "concurso-prf-", "planos-de-assinatura", "/aulas/ao-vivo")
        for a in page.locator("a[href*='/playlist/']").all():
            href = a.get_attribute("href") or ""
            tit = re.sub(r"\s+", " ", (a.inner_text() or "").strip())
            if not href or href in visto or len(tit) < 8:
                continue
            if any(r in href for r in ruido):
                continue
            if alvo:
                bag = _tokens(tit) | _tokens(href)
                if not (alvo & bag):
                    continue
            visto.add(href)
            aulas.append({
                "origem": "qconcursos",
                "titulo": tit[:240],
                "url": urljoin(page.url, href),
                "disciplina": args.disciplina,
                "assunto": args.assunto,
                "verificado_em": date.today().isoformat(),
            })
            if args.max and len(aulas) >= args.max:
                break
        # fallback: abrir 2–3 questões do recorte e colher o bloco "Aulas"
        if len(aulas) < (args.max or 5) and args.disciplina:
            qps_delay()
            ir(page, url_questoes(args), espera=2.2)
            cards = coletar_pagina_questoes(page)
            for it in cards[:3]:
                if not it.get("url"):
                    continue
                qps_delay()
                ir(page, it["url"], espera=2.0)
                botao = page.get_by_text("Aulas", exact=False)
                if botao.count():
                    try:
                        botao.first.click(timeout=2500)
                        page.wait_for_timeout(1600)
                    except Exception:
                        pass
                for a in page.locator("a[href*='/playlist/'], a[href*='/aulas/']").all():
                    href = a.get_attribute("href") or ""
                    tit = re.sub(r"\s+", " ", (a.inner_text() or "").strip())
                    if not href or href in visto or any(r in href for r in ruido):
                        continue
                    if alvo and not (_tokens(tit) | _tokens(href)) & alvo:
                        continue
                    if len(tit) < 4:
                        tit = href.rstrip("/").split("/")[-1].replace("-", " ")
                    visto.add(href)
                    aulas.append({
                        "origem": "qconcursos",
                        "titulo": tit[:240],
                        "url": urljoin(page.url, href),
                        "disciplina": args.disciplina,
                        "assunto": args.assunto,
                        "verificado_em": date.today().isoformat(),
                    })
                    if args.max and len(aulas) >= args.max:
                        break
                if args.max and len(aulas) >= args.max:
                    break
        for a in aulas:
            gravar_cache("aulas", a["url"], a)
        emitir({"fonte": page.url, "consulta": consulta, "n": len(aulas),
                "aulas": aulas[: args.max or len(aulas)]})
    finally:
        ctx.close()
        pw.stop()


def cmd_raiox(args) -> None:
    pw, ctx = abrir_contexto()
    try:
        page = pagina(ctx)
        garantir_login(page)
        ir(page, f"{base_url()}/usuario/ferramentas/raio-x", espera=2.5)
        links = []
        for a in page.locator("a[href*='/usuario/ferramentas/raio-x/']").all():
            href = a.get_attribute("href") or ""
            if re.search(r"/raio-x/\d+", href):
                links.append(urljoin(page.url, href))
        # unique, keep order
        seen, uniq = set(), []
        for u in links:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        assuntos = []
        alvos = uniq[:8] or [page.url]
        for u in alvos:
            qps_delay()
            ir(page, u, espera=2.2)
            texto = page.inner_text("body")
            # linhas "Assunto  12  4,3%"
            for m in re.finditer(
                r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\\n]{3,80}?)\s+(\d{1,5})\s+(\d{1,2}[,.]\d+)\s*%",
                texto,
            ):
                assuntos.append({
                    "assunto": m.group(1).strip(),
                    "n": int(m.group(2)),
                    "pct": float(m.group(3).replace(",", ".")),
                    "fonte": page.url,
                })
            # tabelas
            for tr in page.locator("table tr").all()[:80]:
                cols = [c.inner_text().strip() for c in tr.locator("td").all()]
                if len(cols) >= 2 and re.search(r"\d", cols[-1]):
                    n = None
                    pct = None
                    for c in cols[1:]:
                        if re.fullmatch(r"\d+", c):
                            n = int(c)
                        elif re.search(r"\d+[,.]\d+\s*%", c):
                            pct = float(re.search(r"(\d+[,.]\d+)", c).group(1).replace(",", "."))
                    if cols[0] and (n is not None or pct is not None):
                        assuntos.append({
                            "assunto": cols[0],
                            "n": n,
                            "pct": pct,
                            "fonte": page.url,
                        })
        # filtro textual pedido
        if args.disciplina:
            chave = slugificar(args.disciplina)
            filtrado = [a for a in assuntos if chave in slugificar(a.get("assunto") or "")]
            if filtrado:
                assuntos = filtrado
        out = {
            "banca": args.banca,
            "disciplina": args.disciplina,
            "de": args.de,
            "ate": args.ate,
            "n": len(assuntos),
            "assuntos": assuntos,
            "coletado_em": date.today().isoformat(),
        }
        gravar_cache("raiox", f"{args.banca or 'todas'}-{args.disciplina or 'todas'}", out)
        emitir(out)
    finally:
        ctx.close()
        pw.stop()


def cmd_editais(args) -> None:
    pw, ctx = abrir_contexto()
    try:
        page = pagina(ctx)
        garantir_login(page)
        q = " ".join(x for x in (args.orgao, args.ano and str(args.ano), "edital") if x)
        ir(page, f"{base_url()}/questoes-de-concursos/provas", espera=2.0)
        caixa = page.locator("#search-header, input[name=q]").first
        if caixa.count():
            caixa.fill(q)
            caixa.press("Enter")
            page.wait_for_timeout(2500)
        provas = []
        for a in page.locator("a[href*='/provas/'], a[href*='/concursos/']").all()[: args.max or 20]:
            href = a.get_attribute("href") or ""
            tit = re.sub(r"\s+", " ", (a.inner_text() or "").strip())
            if not tit or len(tit) < 6:
                continue
            provas.append({
                "titulo": tit[:240],
                "url": urljoin(page.url, href),
                "orgao": args.orgao,
                "ano": args.ano,
            })
        emitir({"consulta": q, "n": len(provas), "itens": provas})
    finally:
        ctx.close()
        pw.stop()


def cmd_prova(args) -> None:
    pw, ctx = abrir_contexto()
    try:
        page = pagina(ctx)
        garantir_login(page)
        ident = args.id
        url = ident if ident.startswith("http") else f"{base_url()}/questoes-de-concursos/provas/{ident}"
        ir(page, url, espera=2.5)
        dest = DADOS / "provas" / slugificar(ident)
        dest.mkdir(parents=True, exist_ok=True)
        pdfs = []
        for a in page.locator("a[href$='.pdf'], a:has-text('PDF'), a:has-text('Download'), a:has-text('Baixar')").all():
            href = a.get_attribute("href")
            if not href:
                continue
            full = urljoin(page.url, href)
            nome = Path(urlparse(full).path).name or "arquivo.pdf"
            if not nome.lower().endswith(".pdf"):
                nome += ".pdf"
            alvo = dest / nome
            try:
                with page.expect_download(timeout=15000) as dl:
                    a.click()
                dl.value.save_as(str(alvo))
                pdfs.append(str(alvo))
            except Exception:
                # link direto
                try:
                    resp = page.request.get(full)
                    if resp.ok and "pdf" in (resp.headers.get("content-type") or "").lower():
                        alvo.write_bytes(resp.body())
                        pdfs.append(str(alvo))
                except Exception:
                    pass
        meta = {
            "id": ident,
            "url": page.url,
            "titulo": page.title(),
            "pdfs": pdfs,
            "texto": page.inner_text("body")[:8000],
            "coletado_em": date.today().isoformat(),
        }
        gravar_cache("provas", ident, meta)
        emitir(meta)
    finally:
        ctx.close()
        pw.stop()


def cmd_status(_args) -> None:
    env = ler_env()
    tem_env = bool(env.get("QCONCURSOS_LOGIN") and env.get("QCONCURSOS_PASSWORD"))
    info = {
        "env": tem_env,
        "url": env.get("QCONCURSOS_URL") or BASE_PADRAO,
        "perfil": str(PERFIL),
        "cache": str(DADOS),
        "perfil_existe": PERFIL.exists(),
        "logado": False,
        "plano": None,
    }
    if not tem_env:
        emitir(info)
        raise SystemExit(2)
    pw, ctx = abrir_contexto(headed=os.environ.get("QC_HEADED", "1") not in ("0", "false"))
    try:
        page = pagina(ctx)
        if garantir_login(page, obrigatorio=False):
            ir(page, f"{base_url()}/usuario", espera=1.5)
            info.update(perfil_conta(page))
            info["logado"] = True
        emitir(info)
        if not info["logado"]:
            raise SystemExit(2)
    finally:
        ctx.close()
        pw.stop()


def cmd_login(_args) -> None:
    os.environ["QC_HEADED"] = "1"
    pw, ctx = abrir_contexto(headed=True)
    try:
        page = pagina(ctx)
        ok = garantir_login(page, obrigatorio=True)
        ir(page, f"{base_url()}/usuario", espera=1.5)
        info = perfil_conta(page)
        info["ok"] = ok
        emitir(info)
    finally:
        ctx.close()
        pw.stop()


def main() -> None:
    ap = argparse.ArgumentParser(description="Cliente da conta QConcursos.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("login")

    p = sub.add_parser("raiox")
    p.add_argument("--banca")
    p.add_argument("--disciplina")
    p.add_argument("--de", type=int)
    p.add_argument("--ate", type=int)

    p = sub.add_parser("questoes")
    p.add_argument("--disciplina")
    p.add_argument("--assunto")
    p.add_argument("--banca")
    p.add_argument("--ano", type=int)
    p.add_argument("--orgao")
    p.add_argument("--max", type=int, default=20)
    p.add_argument("--pagina", type=int)

    p = sub.add_parser("questao")
    p.add_argument("id")

    p = sub.add_parser("aulas")
    p.add_argument("--disciplina")
    p.add_argument("--assunto")
    p.add_argument("--max", type=int, default=10)

    p = sub.add_parser("editais")
    p.add_argument("--orgao")
    p.add_argument("--ano", type=int)
    p.add_argument("--max", type=int, default=15)

    p = sub.add_parser("prova")
    p.add_argument("--id", required=True)

    args = ap.parse_args()
    cmds = {
        "status": cmd_status,
        "login": cmd_login,
        "raiox": cmd_raiox,
        "questoes": cmd_questoes,
        "questao": cmd_questao,
        "aulas": cmd_aulas,
        "editais": cmd_editais,
        "prova": cmd_prova,
    }
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
