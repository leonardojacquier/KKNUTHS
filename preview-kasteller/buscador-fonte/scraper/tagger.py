"""Normalização + tageamento automático dos produtos raspados."""
import re, unicodedata

def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()

LOOKS = [
    ("mármol",  r"marm|marbre|calacat|carrara|statuar|onix|onyx|travert|breccia|venatin|pulpis|athos|ambar|noir|paonazz"),
    ("piedra",  r"pietra|stone|piedra|ceppo|basalt|granit|ardosia|slate|quartz|limest|toronto"),
    ("madera",  r"legno|wood|mader|carvalho|roble|oak|noce|teca|amendoa|freijo|campestre"),
    ("cemento", r"cement|concret|beton|urban|soho|space|loft"),
    ("metal",   r"metal|oxid|iron|steel|corten"),
    ("ladrillo",r"brick|tijol|mattone"),
    ("artesanal", r"artisan|zellige|craft|manual|subway"),
]
ACABADOS = [
    ("polido",    r"\bpol\b|polid|lux|brilh|gloss"),
    ("mate",      r"\bmatte?\b|\bmate\b|fosco"),
    ("acetinado", r"acetin|satin|soft"),
    ("natural",   r"\bnat\b|natural"),
    ("externo",   r"\bext\b|antiderrap|antislip|grip|out"),
]
COLORES = [
    ("blanco", r"\bwh\b|white|blanc|bianco|branco"),
    ("negro",  r"\bbk\b|black|nero|preto|noir"),
    ("gris",   r"\bgr\b|grey|gray|gris|cinza|grigio"),
    ("beige",  r"\bbe\b|beige|bege|sand|creme|ivory|marfim"),
    ("dorado", r"gold|oro|dourad"),
]

def etiquetar(marca, nombre, slug="", url="", img=None, formatos=None):
    base = _norm(f"{nombre} {slug}").lower()
    fmt = (formatos[0] if formatos else None) or \
          (re.search(r"(\d{2,3})\s*[xX]\s*(\d{2,3})", base) or [None])
    formato = f"{fmt.group(1)}X{fmt.group(2)}" if hasattr(fmt, "group") else (fmt or "VARIOS")

    def pick(tabla, default):
        for nome, rx in tabla:
            if re.search(rx, base):
                return nome
        return default

    look    = pick(LOOKS, "otros")
    acabado = pick(ACABADOS, "natural")
    color   = pick(COLORES, None)
    tipo = "revestimiento especial" if look in ("ladrillo", "artesanal") else \
           ("cerámica" if "ceram" in base else "porcelanato")
    usos = ["pared"] if look in ("ladrillo", "artesanal") else ["piso", "pared"]
    if acabado == "externo":
        usos.append("externo")

    tags = [t for t in [marca.lower(), tipo, look, acabado, color,
                        formato.lower() if formato != "VARIOS" else None] if t]
    tags += [w for w in re.findall(r"[a-z]{4,}", base) if w not in tags][:4]

    return dict(
        id=f"{marca.lower()}-{re.sub(r'[^a-z0-9]+', '-', _norm(nombre).lower()).strip('-')}",
        nombre=_norm(nombre).title(), marca=marca, linea=_norm(nombre).title(),
        tipo=tipo, look=look, acabado=acabado, formato=formato,
        usos=usos, tags=list(dict.fromkeys(tags)), img=img, url=url)

def dedupe(productos):
    vistos, out = set(), []
    for p in productos:
        k = (p.get("marca"), p.get("nombre", "").lower(), p.get("formato"))
        if k not in vistos:
            vistos.add(k)
            out.append(p)
    return out
