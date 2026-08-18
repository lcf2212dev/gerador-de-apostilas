#!/usr/bin/env python3
"""Cliente do PCI Concursos — provas e gabaritos em PDF.

A tabela de /provas/<cargo|orgao|banca> é HTML estático. O PDF mora um pulo
depois, em /provas/download/<slug>, atrás de verificação + clique JS.

    pci.py buscar --cargo "Oficial de Justiça" --banca FGV --ano 2022 --max 20
    pci.py pagina --cargo oficial-de-justica
    pci.py baixar <slug> [--para DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path


def raiz_projeto() -> Path:
    return Path(__file__).resolve().parents[4]


def _reexec_venv() -> None:
    venv = raiz_projeto() / ".venv" / "bin" / "python"
    if venv.is_file() and Path(sys.executable).resolve() != venv.resolve():
        os.execv(str(venv), [str(venv), *sys.argv])


BASE = "https://www.pciconcursos.com.br"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CACHE = Path.home() / ".cache" / "concurso" / "pci"
PERFIL = Path.home() / ".cache" / "concurso" / "pci-profile"


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
    return re.sub(r"[^a-zA-Z0-9]+", "-", n.lower()).strip("-")


def get(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9",
                 "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        erro(f"HTTP {e.code} em {url}")
    except urllib.error.URLError as e:
        erro(f"falha de rede em {url}: {e.reason}")
    return ""


class TabelaProvas(HTMLParser):
    """Extrai linhas da tabela Prova / Ano / Órgão / Organizadora."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.itens: list[dict] = []
        self._em_tabela = False
        self._em_tr = False
        self._em_td = False
        self._td_i = -1
        self._celulas: list[dict] = []
        self._texto: list[str] = []
        self._href: str | None = None
        self._hrefs_td: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._em_tabela = True
        elif self._em_tabela and tag == "tr":
            self._em_tr = True
            self._celulas = []
            self._td_i = -1
        elif self._em_tr and tag == "td":
            self._em_td = True
            self._td_i += 1
            self._texto = []
            self._href = None
            self._hrefs_td = []
        elif self._em_td and tag == "a" and a.get("href"):
            href = a["href"]
            self._hrefs_td.append(href)
            if "/provas/download/" in href and self._href is None:
                self._href = href

    def handle_endtag(self, tag):
        if tag == "table":
            self._em_tabela = False
        elif tag == "tr" and self._em_tr:
            self._em_tr = False
            self._fechar_linha()
        elif tag == "td" and self._em_td:
            self._em_td = False
            self._celulas.append({
                "texto": " ".join("".join(self._texto).split()),
                "href": self._href,
                "hrefs": list(self._hrefs_td),
            })

    def handle_data(self, data):
        if self._em_td:
            self._texto.append(data)

    def _fechar_linha(self) -> None:
        if len(self._celulas) < 4:
            return
        prova, ano, orgao, banca = self._celulas[:4]
        href = prova.get("href") or ""
        m = re.search(r"/provas/download/([^/?#]+)", href)
        if not m:
            return
        try:
            ano_i = int(re.search(r"\d{4}", ano["texto"] or "").group())
        except (AttributeError, ValueError):
            ano_i = None
        self.itens.append({
            "titulo": prova["texto"],
            "ano": ano_i,
            "orgao": orgao["texto"],
            "banca": banca["texto"],
            "slug": m.group(1),
            "url": urllib.parse.urljoin(BASE + "/", href.lstrip("/")),
        })


def parse_tabela(html: str) -> list[dict]:
    p = TabelaProvas()
    p.feed(html)
    p.close()
    return p.itens


def paginas_total(html: str) -> int:
    m = re.search(r"Mostrando p[aá]gina\s+\*?\*?(\d+)\*?\*?\s+de\s+\*?\*?(\d+)", html, re.I)
    if m:
        return int(m.group(2))
    m = re.search(r"página\s+(\d+)\s+de\s+(\d+)", html, re.I)
    return int(m.group(2)) if m else 1


def url_lista(args) -> str:
    if getattr(args, "url", None):
        return args.url
    for chave, attr in (("cargo", "cargo"), ("orgao", "orgao"), ("banca", "banca")):
        val = getattr(args, attr, None)
        if val:
            return f"{BASE}/provas/{slugificar(val)}"
    q = getattr(args, "q", None)
    if q:
        return f"{BASE}/provas/?q={urllib.parse.quote(q)}"
    return f"{BASE}/provas/"


def filtrar(itens: list[dict], args) -> list[dict]:
    out = itens
    if getattr(args, "ano", None):
        out = [i for i in out if i.get("ano") == args.ano]
    if getattr(args, "banca", None) and (
        getattr(args, "cargo", None) or getattr(args, "orgao", None) or getattr(args, "q", None)
    ):
        chave = slugificar(args.banca)
        out = [i for i in out if chave in slugificar(i.get("banca") or "")]
    if getattr(args, "orgao", None) and getattr(args, "cargo", None):
        chave = slugificar(args.orgao)
        out = [i for i in out if chave in slugificar(i.get("orgao") or "")]
    return out


def coletar_lista(url: str, args, max_paginas: int = 8) -> list[dict]:
    todos: list[dict] = []
    visto: set[str] = set()
    teto = getattr(args, "max", None) or 50
    html = get(url)
    n_pags = min(paginas_total(html), max_paginas)
    for pag in range(1, n_pags + 1):
        if pag > 1:
            time.sleep(0.4 + random.uniform(0, 0.3))
            html = get(url.rstrip("/") + f"/{pag}")
        for it in filtrar(parse_tabela(html), args):
            if it["slug"] in visto:
                continue
            visto.add(it["slug"])
            todos.append(it)
            if len(todos) >= teto:
                return todos
    return todos


def cmd_buscar(args) -> None:
    url = url_lista(args)
    itens = coletar_lista(url, args)
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "ultima-busca.json").write_text(
        json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    emitir({
        "fonte": url,
        "filtro": {k: getattr(args, k) for k in ("cargo", "orgao", "banca", "ano", "q")
                   if getattr(args, k, None)},
        "n": len(itens),
        "provas": itens,
    })


def cmd_pagina(args) -> None:
    url = url_lista(args)
    html = get(url)
    itens = parse_tabela(html)
    emitir({"fonte": url, "paginas": paginas_total(html), "n": len(itens), "provas": itens})


# --- download -------------------------------------------------------------


def classificar_arquivo(nome: str) -> str:
    n = slugificar(nome)
    if "gabarito" in n or n.startswith("gab"):
        return "gabarito"
    if "edital" in n or "retific" in n:
        return "edital"
    return "prova"


def eh_pdf(caminho: Path) -> bool:
    try:
        cab = caminho.read_bytes()[:5]
    except OSError:
        return False
    return cab == b"%PDF-"


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def converter_txt(pdf: Path) -> Path | None:
    txt = pdf.with_suffix(".txt")
    try:
        r = subprocess.run(
            ["pdftotext", "-layout", str(pdf), str(txt)],
            capture_output=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        aviso(f"pdftotext falhou em {pdf.name}")
        return None
    if r.returncode != 0 or not txt.is_file() or txt.stat().st_size == 0:
        aviso(f"PDF sem camada de texto: {pdf.name}")
        return None
    return txt


def _playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        _reexec_venv()
        erro("Playwright ausente. Instale no .venv do projeto (ver AGENTS.md).")


def chrome_channel() -> str | None:
    for c in ("/usr/bin/google-chrome-stable", "/usr/bin/google-chrome",
              "/opt/google/chrome/chrome"):
        if Path(c).is_file():
            return "chrome"
    return None


def baixar_com_navegador(url: str, dest: Path) -> list[dict]:
    sync_playwright = _playwright()
    PERFIL.mkdir(parents=True, exist_ok=True)
    dest.mkdir(parents=True, exist_ok=True)
    headed = os.environ.get("PCI_HEADED", "1") not in ("0", "false", "False")
    arquivos: list[dict] = []
    kwargs = dict(
        user_data_dir=str(PERFIL),
        headless=not headed,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        accept_downloads=True,
        args=["--disable-blink-features=AutomationControlled", "--no-first-run"],
        ignore_default_args=["--enable-automation"],
    )
    canal = chrome_channel()
    if canal:
        kwargs["channel"] = canal
    pw = sync_playwright().start()
    try:
        ctx = pw.chromium.launch_persistent_context(**kwargs)
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        # Turnstile: o POST /provas/link só preenche href http depois do captcha.
        try:
            page.wait_for_function(
                """() => [...document.querySelectorAll('a.prova-pdf-link[data-acao="baixar"]')]
                    .some(a => (a.getAttribute('href') || '').startsWith('http'))""",
                timeout=90000,
            )
        except Exception:
            erro("Turnstile do PCI não liberou os links. Rode headed (PCI_HEADED=1), "
                 "complete a verificação na janela e tente de novo.")
        itens = page.eval_on_selector_all(
            'a.prova-pdf-link[data-acao="baixar"]',
            """els => els.map(a => ({
                href: a.getAttribute('href'),
                arquivo: a.dataset.arquivo || '',
                texto: (a.innerText || '').trim()
            })).filter(x => x.href && x.href.startsWith('http'))""",
        )
        if not itens:
            erro("captcha passou mas nenhum href http apareceu — atualize superficie.md")
        for item in itens:
            nome = os.path.basename(item.get("arquivo") or item["href"].split("?")[0])
            if not nome.lower().endswith(".pdf"):
                nome += ".pdf"
            alvo = dest / nome
            if alvo.is_file() and eh_pdf(alvo):
                arquivos.append(_meta_arquivo(alvo, url))
                continue
            try:
                resp = page.request.get(item["href"], timeout=60000)
                corpo = resp.body()
            except Exception as e:
                aviso(f"GET falhou ({nome}): {e}")
                continue
            if not corpo.startswith(b"%PDF-"):
                aviso(f"{nome} não é PDF (content-type {resp.headers.get('content-type', '?')})")
                continue
            alvo.write_bytes(corpo)
            arquivos.append(_meta_arquivo(alvo, item["href"]))
            time.sleep(0.4)
        ctx.close()
    finally:
        pw.stop()
    return arquivos


def _meta_arquivo(caminho: Path, url: str) -> dict:
    tipo = classificar_arquivo(caminho.name)
    txt = converter_txt(caminho)
    return {
        "tipo": tipo,
        "arquivo": str(caminho),
        "txt": str(txt) if txt else None,
        "bytes": caminho.stat().st_size,
        "sha256": sha256(caminho),
        "url": url,
    }


def cmd_baixar(args) -> None:
    slug = args.slug
    if slug.startswith("http"):
        url = slug
        slug = slug.rstrip("/").split("/")[-1]
    else:
        url = f"{BASE}/provas/download/{slug}"
    dest = Path(args.para) if args.para else (CACHE / slug)
    dest.mkdir(parents=True, exist_ok=True)
    arquivos = baixar_com_navegador(url, dest)
    out = {
        "slug": slug,
        "url": url,
        "destino": str(dest),
        "acessado_em": date.today().isoformat(),
        "status": "ok" if arquivos else "falha",
        "arquivos": arquivos,
    }
    if not arquivos:
        out["obs"] = "nenhum PDF baixado"
    (dest / "manifest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    emitir(out)
    if not arquivos:
        raise SystemExit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description="PCI Concursos — provas e gabaritos.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("buscar")
    p.add_argument("--cargo")
    p.add_argument("--orgao")
    p.add_argument("--banca")
    p.add_argument("--ano", type=int)
    p.add_argument("--q", help="busca livre (se o site aceitar ?q=)")
    p.add_argument("--max", type=int, default=20)

    p = sub.add_parser("pagina")
    p.add_argument("--cargo")
    p.add_argument("--orgao")
    p.add_argument("--banca")
    p.add_argument("--url")

    p = sub.add_parser("baixar")
    p.add_argument("slug")
    p.add_argument("--para", help="diretório de destino (padrão: ~/.cache/concurso/pci/<slug>)")

    args = ap.parse_args()
    {"buscar": cmd_buscar, "pagina": cmd_pagina, "baixar": cmd_baixar}[args.cmd](args)


if __name__ == "__main__":
    main()
