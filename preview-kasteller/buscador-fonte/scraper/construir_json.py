#!/usr/bin/env python3
"""Monta buscador/productos.json a partir dos dados brutos raspados (raw_*.txt)."""
import json, re, unicodedata, sys
from pathlib import Path

HERE = Path(__file__).parent

def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()

LOOKS = [
 ("mármol", r"marm|marble|calacat|carrara|statuar|onice|onix|travert|breccia|venatin|pulpis|nero|noir|paonazz|emperad|marfil|marmo|arcobalen|cristallo|bianco onice|thassos|sahara|crema|onice"),
 ("piedra", r"pietra|stone|piedra|ceppo|basalt|granit|ardosia|slate|quartz|arenit|arenaria|toronto|caminho|patagonia|limestone|rupestre|moledo|puglia|negresco"),
 ("madera", r"legno|wood|mader|carvalho|roble|oak|noce|teca|freij|campestre|assoalho|madeyra|arden|house|linho"),
 ("cemento", r"cement|cimentati|concret|beton|urban|soho|space|loft|brutalist|oxidato|rammed|matéria|materia|stucco|concrete"),
 ("metal", r"metal|metálico|oxid|iron|steel|corten|fire|fulmine"),
 ("ladrillo", r"brick|tijol|ecobrick|mattone|adobe|colonna|etrusco"),
 ("artesanal", r"artisan|zellige|craft|manual|subway|maiolica|mosaico|azulejo|artesano|ladrilho|tijoleta"),
]
ACAB = [
 ("polido", r"\bpol\b|polid|\blux\b|brilh|gloss|lux\b"),
 ("mate", r"\bmatte?\b|\bmate\b|fosco|nat\b|natural|hard\b|out\b|grezzo"),
 ("acetinado", r"acetin|satin|satiny|soft|acetinado"),
 ("natural", r"\bnat\b|natural"),
]
COR = {
 "WH":"blanco","BW":"gris","SGR":"gris","GR":"gris","BK":"negro","BL":"azul","BE":"beige",
 "SBE":"beige","NO":"marrom","OG":"laranja","GN":"verde","DGR":"gris","OFW":"blanco","RD":"rojo",
 "SPK":"gris","GRAFITE":"negro","BRANCO":"blanco","PRETO":"negro","CINZA":"gris","AZUL":"azul",
 "BEGE":"beige","BRANCO POLAR":"blanco","NERO":"negro","GRAY":"gris","SNOW":"blanco","DARK":"negro",
}
SUP = {"POLIDO":"polido","NATURAL":"natural","ACETINADO":"acetinado","MATTE":"mate","RÚSTICO":"mate",
 "HARD":"externo","LUX":"polido","MLX":"mate","MATTE/LUX":"mate","SATINY":"acetinado","OUT":"externo",
 "NAT":"natural","ACT":"acetinado","MAT":"mate","POL":"polido"}

def classifica(base, superficie=None, cor_raw=None, categoria=""):
    look = next((n for n, rx in LOOKS if re.search(rx, base)), "otros")
    if superficie and superficie.strip().upper() in SUP:
        acab = SUP[superficie.strip().upper()]
    else:
        acab = next((n for n, rx in ACAB if re.search(rx, base)), "natural")
    color = COR.get((cor_raw or "").strip().upper()) or \
            next((v for k, v in COR.items() if len(k) > 3 and k.lower() in base), None)
    tipo = "revestimiento especial" if look in ("ladrillo", "artesanal") or "PISCINA" in categoria else \
           ("cerámica" if "ceram" in base else "porcelanato")
    usos = ["pared"] if look in ("ladrillo", "artesanal") else ["piso", "pared"]
    if acab == "externo" or "PISCINA" in categoria or "FACHADA" in base.upper():
        usos.append("externo")
    if "GRANDE" in categoria: usos.append("gran formato")
    return look, acab, color, tipo, list(dict.fromkeys(usos))

def make(marca, nombre, url, img, formato="VARIOS", superficie=None, cor=None, categoria="", extra=None):
    base = norm(nombre).lower()
    fmt = re.search(r"(\d{2,3})\s*[xX]\s*(\d{2,3})", nombre + " " + (url or ""))
    formato = f"{fmt.group(1)}X{fmt.group(2)}" if fmt else formato
    look, acab, color, tipo, usos = classifica(base, superficie, cor, categoria)
    tags = [t for t in [marca.lower(), tipo, look, acab, color,
            formato.lower() if formato != "VARIOS" else None] if t]
    tags += [w for w in re.findall(r"[a-z]{4,}", base) if w not in tags][:4]
    if extra: tags += extra
    pid = f"{marca.lower()}-" + re.sub(r"[^a-z0-9]+", "-", norm(nombre).lower()).strip("-")
    return dict(id=pid, nombre=norm(nombre).title(), marca=marca, linea=norm(nombre).title(),
                tipo=tipo, look=look, acabado=acab, formato=formato, usos=usos,
                tags=list(dict.fromkeys(tags)), img=img, url=url)

productos = []

# ---- Ceusa (API rica, 9 campos) ----
CEUSA_IMG = "https://ceusa-site-strapi.prd.cloud.dex.co/assets/"
for ln in (HERE / "raw_ceusa.txt").read_text(encoding="utf-8").splitlines():
    p = ln.split("|")
    if len(p) < 9 or not p[0]:
        continue
    nome, slug, formato, superficie, cor, tipo, uso, categoria, img = p[:9]
    img = img.replace("@", CEUSA_IMG) if img and img not in ("NONE", "") else None
    productos.append(make("Ceusa", nome, "https://www.ceusa.com.br/pt/produtos/" + slug, img,
                          superficie=superficie, cor=cor, categoria=categoria))

# ---- Portinari (API, 5 campos compactos: nome|slug|acabamento|cor|imgfile) ----
PORT_IMG = "https://portinari-site-strapi.prd.cloud.dex.co/assets/"
for ln in (HERE / "raw_portinari.txt").read_text(encoding="utf-8").splitlines():
    p = ln.split("|")
    if len(p) < 5 or not p[0]:
        continue
    nome, slug, acab, cor, imgfile = p[:5]
    img = PORT_IMG + imgfile if imgfile and imgfile not in ("NONE", "") else None
    productos.append(make("Portinari", nome, "https://www.portinarirevestimentos.com.br/produtos/" + slug,
                          img, superficie=acab, cor=cor))

# ---- Roca e Incepa (imagem por padrão fixo .../ambientes/mini/{slug}.jpg) ----
for marca, arq, dom in [
    ("Roca", "raw_roca.txt", "https://www.rocaceramica.com.br"),
    ("Incepa", "raw_incepa.txt", "https://www.incepa.com.br")]:
    for item in (HERE / arq).read_text(encoding="utf-8").strip().split(";"):
        if "|" not in item:
            continue
        nome, slug = item.split("|", 1)
        productos.append(make(marca, nome, f"{dom}/serie/{slug}",
                              f"{dom}/produtos/imagens/ambientes/mini/{slug}.jpg"))

# ---- Castelatto (nome|slug + imagem por índice) ----
ns = [x for x in (HERE / "raw_castelatto_ns.txt").read_text(encoding="utf-8").strip().split(";") if "|" in x]
imgs = (HERE / "raw_castelatto_img.txt").read_text(encoding="utf-8").strip().split(";")
for i, item in enumerate(ns):
    nome, slug = item.split("|", 1)
    img = (f"https://castelatto.com.br/wp-content/uploads/{imgs[i]}-495x730.jpg.webp"
           if i < len(imgs) and imgs[i] else None)
    productos.append(make("Castelatto", nome, f"https://castelatto.com.br/produto/{slug}/", img))

# ---- Castelli (nome+código|slug; imagem via página do produto -> optimizador) ----
for item in (HERE / "raw_castelli.txt").read_text(encoding="utf-8").strip().split(";"):
    if "|" not in item:
        continue
    raw, slug = item.split("|", 1)
    nome = re.sub(r"\s+(CT|CR|CA|CN|CP|CG|P|CE)?\d{4,}[A-Z0-9]*$", "", raw).strip()
    productos.append(make("Castelli", nome, f"https://castelliporcelanato.com.br/produto/{slug}", None))

# dedupe por id
vis, fin = set(), []
for p in productos:
    if p["id"] not in vis:
        vis.add(p["id"]); fin.append(p)

out = HERE.parent / "buscador" / "productos.json"
json.dump({"generado": "raspagem-completa-7-fabricas", "total": len(fin), "productos": fin},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

from collections import Counter
print("TOTAL:", len(fin))
print("por marca:", dict(Counter(p["marca"] for p in fin)))
print("com imagem:", sum(1 for p in fin if p.get("img")), "/", len(fin))
print("por look:", dict(Counter(p["look"] for p in fin).most_common()))
