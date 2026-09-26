#!/usr/bin/env python3
"""
KASTELLER — Raspador de catálogos das fábricas representadas.
Gera/atualiza buscador/productos.json no formato do buscador.

Uso:
  pip install -r requirements.txt
  playwright install chromium
  python scrape.py --site all
  python scrape.py --site ceusa,incepa --out ../buscador/productos.json

Sites e estratégia (mapeado em reconhecimento real):
  ceusa      Next.js/Strapi, 209 produtos, listagem paginada SSR  -> requests
  incepa     WordPress, sitemap + /serie/{slug}                   -> requests
  roca       WordPress com proteção de redirect                   -> playwright
  castelli   SPA renderizada por JS ({{templates}})               -> playwright
  castelatto WordPress/Woo com 403 anti-bot                       -> playwright
  portinari  Plataforma Dexco (mesma da Ceusa) com 403            -> playwright
  pasinato   403 anti-bot                                         -> playwright

Coletamos apenas DADOS FACTUAIS de catálogo (nome, formato, categoria,
link e URL da imagem oficial) para indexação/busca, sempre apontando o
cliente para a página oficial da fábrica — não copiamos textos descritivos.
"""
import argparse, json, re, sys, time, unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from tagger import etiquetar, dedupe

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})


def get(url, **kw):
    r = S.get(url, timeout=30, **kw)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- CEUSA
def scrape_ceusa():
    """Listagem SSR paginada: /pt/produtos?page=N (12 por página)."""
    out, page = [], 1
    while page <= 30:
        r = get(f"https://www.ceusa.com.br/pt/produtos?page={page}")
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select('a[href*="/pt/produtos/"]')
        vistos = 0
        for a in cards:
            href = a.get("href", "")
            slug = href.rstrip("/").split("/")[-1]
            if not re.search(r"\d+x\d+$", slug):
                continue
            img = a.select_one("img")
            nombre = (a.get_text(" ", strip=True) or slug.replace("-", " ")).strip()
            out.append(etiquetar(
                marca="Ceusa", nombre=nombre, slug=slug,
                url="https://www.ceusa.com.br" + href,
                img=(img.get("src") or img.get("data-src")) if img else None))
            vistos += 1
        print(f"  ceusa p.{page}: {vistos}")
        if vistos == 0:
            break
        page += 1
        time.sleep(1)
    return out


# --------------------------------------------------------------- INCEPA
def scrape_incepa():
    """Sitemap do WordPress -> páginas /serie/{slug} -> og:image + formatos."""
    out = []
    urls = set()
    for sm in ("https://www.incepa.com.br/sitemap_index.xml",
               "https://www.incepa.com.br/sitemap.xml"):
        try:
            xml = get(sm).text
            urls |= set(re.findall(r"<loc>([^<]+)</loc>", xml))
        except Exception:
            pass
    series = sorted(u for u in urls if "/serie/" in u)
    if not series:  # fallback: raspa a página de produtos
        soup = BeautifulSoup(get("https://www.incepa.com.br/produtos/").text, "html.parser")
        series = sorted({a["href"] for a in soup.select('a[href*="/serie/"]')})
    for u in series:
        # sub-sitemaps
        if u.endswith(".xml"):
            urls2 = re.findall(r"<loc>([^<]+)</loc>", get(u).text)
            series += [x for x in urls2 if "/serie/" in x]
            continue
        try:
            soup = BeautifulSoup(get(u).text, "html.parser")
            og = soup.select_one('meta[property="og:image"]')
            title = soup.select_one('meta[property="og:title"]') or soup.title
            nombre = re.sub(r"\s*[-|–].*$", "", title.get("content", title.get_text())
                            if hasattr(title, "get") else str(title)).strip()
            fmts = sorted(set(re.findall(r"(\d{2,3}[xX]\d{2,3})", soup.get_text())))[:4]
            out.append(etiquetar(
                marca="Incepa", nombre=nombre, slug=u.rstrip("/").split("/")[-1],
                url=u, img=og.get("content") if og else None,
                formatos=fmts))
            print(f"  incepa: {nombre}")
            time.sleep(0.7)
        except Exception as e:
            print(f"  incepa ERRO {u}: {e}", file=sys.stderr)
    return out


# ------------------------------------------------- SITES COM PLAYWRIGHT
def _browser():
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent=UA, locale="pt-BR",
                        viewport={"width": 1440, "height": 900})
    return p, b, ctx


def _colecta_generica(page, marca, base, sel_card, sel_nombre=None, sel_img="img"):
    """Extrai cards genéricos: nome + link + imagem."""
    out = []
    for el in page.query_selector_all(sel_card):
        try:
            a = el if el.get_attribute("href") else el.query_selector("a")
            href = a.get_attribute("href") if a else None
            nom_el = el.query_selector(sel_nombre) if sel_nombre else el
            nombre = (nom_el.inner_text() if nom_el else "").strip().split("\n")[0]
            img = el.query_selector(sel_img)
            src = img.get_attribute("src") or img.get_attribute("data-src") if img else None
            if nombre and len(nombre) > 2:
                out.append(etiquetar(marca=marca, nombre=nombre,
                                     slug=(href or nombre).rstrip("/").split("/")[-1],
                                     url=(href if (href or "").startswith("http")
                                          else base + (href or "")), img=src))
        except Exception:
            continue
    return out


def scrape_playwright(site):
    cfg = {
        "roca": dict(marca="Roca", url="https://www.rocaceramica.com.br/produtos/",
                     base="https://www.rocaceramica.com.br",
                     card='a[href*="/produto"], .produto, article'),
        "castelli": dict(marca="Castelli", url="https://castelliporcelanato.com.br/produtos",
                         base="https://castelliporcelanato.com.br",
                         card='[class*="produto"] a, .card-produto, a[href*="/produto"]'),
        "castelatto": dict(marca="Castelatto",
                           url="https://castelatto.com.br/tipo-produto/revestimentos/",
                           base="https://castelatto.com.br",
                           card='li.product a.woocommerce-LoopProduct-link, .product a'),
        "portinari": dict(marca="Portinari",
                          url="https://www.portinarirevestimentos.com.br/produtos",
                          base="https://www.portinarirevestimentos.com.br",
                          card='a[href*="/produtos/"]'),
        "pasinato": dict(marca="Pasinato", url="https://www.pasinato.com.br/",
                         base="https://www.pasinato.com.br",
                         card='a[href*="produto"], .produto a'),
    }[site]
    p, b, ctx = _browser()
    out = []
    try:
        page = ctx.new_page()
        page.goto(cfg["url"], wait_until="networkidle", timeout=60000)
        # rola para carregar lazy-load / infinite scroll
        for _ in range(12):
            page.mouse.wheel(0, 2400)
            page.wait_for_timeout(700)
        out = _colecta_generica(page, cfg["marca"], cfg["base"], cfg["card"])
        # paginação "próximo" quando existir
        for _ in range(40):
            nxt = page.query_selector('a[rel="next"], .next, button:has-text("PRÓXIMO")')
            if not nxt:
                break
            nxt.click()
            page.wait_for_timeout(1800)
            out += _colecta_generica(page, cfg["marca"], cfg["base"], cfg["card"])
        print(f"  {site}: {len(out)} itens")
    finally:
        ctx.close(); b.close(); p.stop()
    return out


# ------------------------------------------------------------------ CLI
SITES = {
    "ceusa": scrape_ceusa,
    "incepa": scrape_incepa,
    "roca": lambda: scrape_playwright("roca"),
    "castelli": lambda: scrape_playwright("castelli"),
    "castelatto": lambda: scrape_playwright("castelatto"),
    "portinari": lambda: scrape_playwright("portinari"),
    "pasinato": lambda: scrape_playwright("pasinato"),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="all", help="all ou lista: ceusa,incepa,...")
    ap.add_argument("--out", default="../buscador/productos.json")
    ap.add_argument("--merge", action="store_true",
                    help="mantém itens já existentes no JSON de saída")
    args = ap.parse_args()

    alvo = list(SITES) if args.site == "all" else args.site.split(",")
    productos = []
    if args.merge and Path(args.out).exists():
        productos = json.load(open(args.out, encoding="utf-8")).get("productos", [])

    for s in alvo:
        print(f"== {s} ==")
        try:
            productos += SITES[s]()
        except Exception as e:
            print(f"  FALHOU {s}: {e}", file=sys.stderr)

    productos = dedupe(productos)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"generado": time.strftime("%Y-%m-%d"), "total": len(productos),
               "productos": productos},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nOK -> {args.out} ({len(productos)} productos)")

if __name__ == "__main__":
    main()
