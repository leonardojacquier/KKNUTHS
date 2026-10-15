#!/usr/bin/env python3
"""
Baixa as fotos dos produtos do productos.json e converte para WebP leve,
servido do NOSSO domínio (performance + design consistente).

Uso (depois do scrape.py):
  pip install pillow requests
  python optimizar_imagenes.py --json ../buscador/productos.json --out ../buscador/img

O que faz por imagem:
  - download da URL original (Drive/CDNs das fábricas)
  - corta/redimensiona para 800x920 (proporção dos cards do buscador)
  - converte para WebP qualidade 74 (~40-60 KB por foto)
  - grava em img/{id}.webp e reescreve o campo "img" do JSON
  - guarda a URL original em "img_origen" (para refazer no futuro)
Idempotente: pula o que já foi baixado. Falhou? mantém a URL original.
"""
import argparse, io, json, time
from pathlib import Path

import requests
from PIL import Image

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
W, H, CALIDAD = 800, 920, 74


def procesar(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=40)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    # crop central na proporção do card, depois redimensiona
    ratio = W / H
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
    else:
        nh = int(w / ratio); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
    im = im.resize((W, H), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=CALIDAD)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="../buscador/productos.json")
    ap.add_argument("--out", default="../buscador/img")
    args = ap.parse_args()

    data = json.load(open(args.json, encoding="utf-8"))
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    ok = fail = skip = 0

    for p in data["productos"]:
        destino = out / f"{p['id']}.webp"
        rel = f"buscador/img/{p['id']}.webp"
        if destino.exists():
            p.setdefault("img_origen", p.get("img"))
            p["img"] = rel; skip += 1; continue
        url = p.get("img")
        if not url or not str(url).startswith("http"):
            continue
        try:
            destino.write_bytes(procesar(url))
            p["img_origen"] = url
            p["img"] = rel
            ok += 1
            print(f"  ok  {p['id']} ({destino.stat().st_size // 1024} KB)")
            time.sleep(0.4)
        except Exception as e:
            fail += 1
            print(f"  ERR {p['id']}: {e}")

    json.dump(data, open(args.json, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total = sum(f.stat().st_size for f in out.glob("*.webp")) // 1024
    print(f"\n{ok} baixadas, {skip} já existiam, {fail} falharam — {total} KB em {out}")


if __name__ == "__main__":
    main()
