#!/usr/bin/env python3
"""Baixa e otimiza as fotos do productos.json em paralelo -> buscador/img/*.webp"""
import io, json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
from PIL import Image

HERE = Path(__file__).parent
JSON = HERE.parent / "buscador" / "productos.json"
OUT = HERE.parent / "buscador" / "img"
OUT.mkdir(parents=True, exist_ok=True)
W, H, Q = 800, 920, 74
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept": "image/webp,image/*,*/*"}
SKIP_HOST = ("castelatto.com.br",)  # bloqueia download server-side

data = json.load(open(JSON, encoding="utf-8"))
prods = data["productos"]

def proc(p):
    dest = OUT / f"{p['id']}.webp"
    rel = f"buscador/img/{p['id']}.webp"
    if dest.exists():
        p["img_origen"] = p.get("img_origen") or p.get("img"); p["img"] = rel
        return ("skip", p["id"])
    url = p.get("img")
    if not url or not str(url).startswith("http") or any(h in url for h in SKIP_HOST):
        return ("no", p["id"])
    try:
        r = requests.get(url, headers=UA, timeout=30); r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio = W / H; w, h = im.size
        if w / h > ratio:
            nw = int(h * ratio); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
        else:
            nh = int(w / ratio); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
        im = im.resize((W, H), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "WEBP", quality=Q)
        dest.write_bytes(buf.getvalue())
        p["img_origen"] = url; p["img"] = rel
        return ("ok", p["id"])
    except Exception as e:
        return ("err", f"{p['id']}: {str(e)[:40]}")

ok = skip = no = err = 0
errs = []
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = {ex.submit(proc, p): p for p in prods}
    for i, f in enumerate(as_completed(futs), 1):
        st, info = f.result()
        if st == "ok": ok += 1
        elif st == "skip": skip += 1
        elif st == "no": no += 1
        else: err += 1; errs.append(info)
        if i % 100 == 0:
            print(f"  {i}/{len(prods)} — ok:{ok} skip:{skip} sem-url:{no} erro:{err}", flush=True)

json.dump(data, open(JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
total_kb = sum(f.stat().st_size for f in OUT.glob("*.webp")) // 1024
print(f"\nFIM: {ok} baixadas, {skip} já existiam, {no} sem foto/skip, {err} erros")
print(f"pasta img/: {total_kb} KB em {len(list(OUT.glob('*.webp')))} arquivos")
if errs[:8]: print("amostra de erros:", errs[:8])
