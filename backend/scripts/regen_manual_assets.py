#!/usr/bin/env python3
"""Refaz as imagens do manual (manual_design.html): troca os `blob:null/...`
mortos (sobras da sessão do Claude Design) por imagens REAIS embutidas como
data-URI — todas com a logo KKNuths. Gera QR do bot e os selos Nobel.

Uso: PYTHONPATH=. python scripts/regen_manual_assets.py
Depois, regenerar o PDF a partir de /manual (chromium --print-to-pdf).
"""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "app" / "api" / "assets"
DESIGN = ASSETS / "manual_design.html"
LOGO = ASSETS / "logo_avatar.png"
DEJAVU = "/usr/share/fonts/truetype/dejavu/"
PAPER = (251, 250, 247)
INK = (22, 33, 26)
GOLD = (166, 126, 53)


def _font(name, size):
    try:
        return ImageFont.truetype(DEJAVU + name, size)
    except Exception:
        return ImageFont.load_default()


def _b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    return "data:image/png;base64," + base64.standard_b64encode(
        buf.getvalue()).decode()


def _stamp_logo(img: Image.Image, right: int, top: int, size: int) -> None:
    logo = Image.open(LOGO).convert("RGBA").resize((size, size), Image.LANCZOS)
    img.paste(logo, (int(right - size), int(top)), logo)


def chart_with_logo(fname: str) -> str:
    """Embute o asset do gráfico. Os assets já carregam a logo (stampada uma vez
    na geração), então aqui NÃO estampamos de novo — mantém idempotente."""
    return _b64(Image.open(ASSETS / fname).convert("RGBA"))


def branded_qr() -> str:
    """QR do bot com a logo no centro (correção de erro H aguenta a oclusão)."""
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=12, border=2)
    qr.add_data("https://t.me/KKNUts_BOT")
    qr.make(fit=True)
    img = qr.make_image(fill_color=INK, back_color=PAPER).convert("RGBA")
    W = img.size[0]
    lw = W // 4
    pad = Image.new("RGBA", (lw + 18, lw + 18), PAPER + (255,))
    img.paste(pad, ((W - pad.size[0]) // 2, (W - pad.size[1]) // 2))
    logo = Image.open(LOGO).convert("RGBA").resize((lw, lw), Image.LANCZOS)
    img.paste(logo, ((W - lw) // 2, (W - lw) // 2), logo)
    return _b64(img)


def nobel_badge(year: str) -> str:
    """Selo dourado 'NOBEL <ano>' com um ♠ discreto — marca KKNuths."""
    S = 4
    D = 128
    img = Image.new("RGBA", (D * S, D * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = D * S / 2
    d.ellipse([6 * S, 6 * S, (D - 6) * S, (D - 6) * S], fill=(198, 158, 74),
              outline=(120, 90, 40), width=3 * S)
    d.ellipse([16 * S, 16 * S, (D - 16) * S, (D - 16) * S], outline=(232, 206, 150),
              width=2 * S)
    fn = _font("DejaVuSerif-Bold.ttf", 20 * S)
    fy = _font("DejaVuSerif-Bold.ttf", 26 * S)
    fs = _font("DejaVuSans-Bold.ttf", 22 * S)
    for txt, f, yy, col in (("NOBEL", fn, 34 * S, (60, 42, 12)),
                            (year, fy, 58 * S, (40, 28, 8)),
                            ("♠", fs, 88 * S, (90, 66, 24))):
        w = d.textlength(txt, font=f)
        d.text((c - w / 2, yy), txt, font=f, fill=col)
    img = img.resize((D, D), Image.LANCZOS)
    return _b64(img)


def main() -> None:
    html = DESIGN.read_text()
    # cada <img> tem um data-dc-tpl único: casamos por ele (robusto, não depende
    # de decorar UUID do blob). tpl -> gerador da imagem real.
    by_tpl = {
        "173": lambda: nobel_badge("2002"),          # Nobel Kahneman
        "178": lambda: nobel_badge("1994"),          # Nobel Nash
        "205": lambda: chart_with_logo("btn_open.png"),
        "209": lambda: chart_with_logo("nash_sb10.png"),
        "213": lambda: chart_with_logo("ev_sb10.png"),
        "217": lambda: chart_with_logo("icm_sb10.png"),
        "351": branded_qr,
    }
    n = 0
    for tpl, gen in by_tpl.items():
        datauri = gen()
        # casa QUALQUER src (blob morto na 1ª rodada; data-URI nas seguintes)
        # — o script fica re-executável quando os gráficos mudam de tema
        pat = re.compile(
            r'(<img data-dc-tpl="' + tpl + r'"[^>]*?src=")[^"]*(")')
        html, cnt = pat.subn(lambda m: m.group(1) + datauri + m.group(2), html)
        if cnt != 1:
            print(f"AVISO tpl {tpl}: {cnt} substituições (esperado 1)")
        n += cnt
    DESIGN.write_text(html)
    left = html.count("blob:null")
    print(f"trocados: {n}/7 · blobs restantes: {left} · tamanho: {len(html)} bytes")


if __name__ == "__main__":
    main()
