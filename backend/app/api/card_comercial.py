"""Card comercial em imagem — a peça que o dono manda no WhatsApp/Telegram.

Diferente do `site_card.png` (que é um DESAFIO de quiz: um spot para o
parceiro responder), este vende a ferramenta. Formato 1080x1350 porque é o
que o WhatsApp e o Telegram exibem inteiro, sem cortar as bordas.

Mesma tese do folder — "a IA não faz a conta" — e a mesma prova: o placar
street a street, que é o formato de saída do produto. Quem vê o card já sabe
o que vai receber.

Renderiza com o Chromium (o mesmo caminho que gera o PDF do folder). Se o
navegador não estiver disponível, devolve None e quem chama decide — nunca
levanta exceção no caminho de quem só queria um asset.
"""
from __future__ import annotations

from app.api.manual_page import _img

LARGURA, ALTURA = 1080, 1350


def build_card_html() -> str:
    """O HTML do card. Separado do render para dar para testar sem navegador."""
    return f"""<!doctype html><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0}}
body{{width:1080px;height:1350px;overflow:hidden;
background:radial-gradient(ellipse at 50% 0%,#1A4732 0%,#0C2318 55%,#081A12 100%);
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#EDEBE4;
display:flex;flex-direction:column;padding:62px 62px 54px}}
.serif{{font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif}}
.topo{{display:flex;align-items:center;gap:18px;justify-content:center}}
.topo img{{width:74px;height:74px;border-radius:50%;box-shadow:0 3px 14px rgba(0,0,0,.5)}}
.topo b{{font-size:38px;font-weight:400;letter-spacing:-.01em}}
.topo span{{color:#8FA898;font-size:16px;letter-spacing:.2em;text-transform:uppercase;
display:block;margin-top:3px}}
h1{{font-size:92px;line-height:.97;font-weight:400;text-align:center;
margin-top:54px;letter-spacing:-.025em}}
h1 em{{color:#D9AC5F;font-style:italic}}
.sub{{text-align:center;color:#A8BCAE;font-size:25px;line-height:1.42;
margin:26px auto 0;max-width:830px}}
.sub b{{color:#fff;font-weight:600}}
.placar{{margin-top:44px;background:rgba(255,255,255,.055);
border:1px solid rgba(217,172,95,.3);border-radius:20px;overflow:hidden}}
.cab{{background:rgba(217,172,95,.14);padding:13px 26px;font-size:16px;
letter-spacing:.19em;text-transform:uppercase;color:#F1D9A7;
display:flex;justify-content:space-between}}
.cab i{{font-style:normal;color:#8FA898;letter-spacing:.05em;text-transform:none;
font-family:ui-monospace,monospace}}
.ln{{display:grid;grid-template-columns:44px 108px 1fr;gap:16px;align-items:baseline;
padding:15px 26px;font-size:22px;line-height:1.36}}
.ln+.ln{{border-top:1px solid rgba(255,255,255,.07)}}
.ln .r{{font-size:15px;letter-spacing:.13em;text-transform:uppercase;color:#D9AC5F;
font-family:ui-monospace,monospace}}
.ln p{{color:#C6D4CA}}
.ln b{{color:#fff}}
.medalhas{{display:flex;gap:16px;justify-content:center;margin-top:40px}}
.med{{display:flex;align-items:center;gap:13px;background:rgba(255,255,255,.055);
border:1px solid rgba(255,255,255,.1);border-radius:15px;padding:12px 22px 12px 14px}}
.disco{{width:56px;height:56px;border-radius:50%;flex:none;color:#221904;
background:radial-gradient(circle at 34% 28%,#F1D9A7,#B38D24 72%);
border:2px solid #D9AC5F;display:flex;flex-direction:column;
align-items:center;justify-content:center;line-height:1}}
.disco i{{font-style:normal;font-size:9px;font-weight:800;letter-spacing:.06em}}
.disco b{{font-size:19px;font-family:'Iowan Old Style',Georgia,serif}}
.med .q{{font-size:20px;font-weight:700;display:block}}
.med .o{{font-size:16px;color:#8FA898}}
.faixa{{display:flex;flex-wrap:wrap;gap:13px;justify-content:center;margin-top:38px}}
.faixa span{{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.11);
border-radius:999px;padding:11px 21px;font-size:19px;color:#C6D4CA}}
.pe{{margin-top:auto;text-align:center}}
.btn{{display:inline-block;background:linear-gradient(160deg,#F1D9A7,#D9AC5F);
color:#22190A;font-size:32px;font-weight:800;padding:22px 54px;border-radius:16px;
box-shadow:0 6px 24px rgba(0,0,0,.4)}}
.btn small{{display:block;font-family:ui-monospace,monospace;font-size:19px;
font-weight:600;color:#5C4A1E;margin-top:5px;letter-spacing:-.01em}}
.mini{{color:#7E9689;font-size:17px;margin-top:22px}}
</style>
<div class="topo"><img src="{_img('logo_avatar.png')}">
  <div><b class="serif">KKNuths</b><span>coach de poker · no Telegram</span></div></div>

<h1 class="serif">A IA n&atilde;o faz<br>a <em>conta</em>.</h1>
<p class="sub">Ela l&ecirc; a m&atilde;o, julga a jogada e explica.
<b>Quem calcula &eacute; a matem&aacute;tica</b> — equity, ICM, Nash,
o pre&ccedil;o exato de cada call.</p>

<div class="placar">
  <div class="cab"><span>O que chega no seu Telegram</span><i>K&#9830;Q&#9830; · BTN · 18.7bb</i></div>
  <div class="ln"><span>&#128993;</span><span class="r">Pr&eacute;</span>
    <p>abriu 2.8bb: com 18.7bb &eacute; territ&oacute;rio de jam —
    <b>jammar rende +1.49bb</b>.</p></div>
  <div class="ln"><span>&#9989;</span><span class="r">Flop</span>
    <p>9&#9829;J&#9830;2&#9824; — c-bet 3.9bb: <b>40% de equity</b>, semi-blefe correto.</p></div>
  <div class="ln"><span>&#9989;</span><span class="r">Turn</span>
    <p>5&#9830; — check behind: nada feito, preserva o pote com K high.</p></div>
  <div class="ln"><span>&#9989;</span><span class="r">River</span>
    <p>3&#9827; — check behind: sem valor pra apostar nem fold equity pra blefar.</p></div>
</div>

<div class="medalhas">
  <div class="med"><span class="disco"><i>NOBEL</i><b>2002</b></span>
    <span><span class="q">Kahneman</span><span class="o">Tilt Detector</span></span></div>
  <div class="med"><span class="disco"><i>NOBEL</i><b>1994</b></span>
    <span><span class="q">Nash</span><span class="o">ranges de all-in</span></span></div>
</div>

<div class="faixa">
  <span>&#128279; Cola o link do replay</span><span>&#127916; O filme da m&atilde;o</span>
  <span>&#128200; Gr&aacute;fico de range</span><span>&#129504; Tilt Detector</span>
  <span>&#9878; ICM autom&aacute;tico</span><span>&#128269; Torneio m&atilde;o a m&atilde;o</span>
</div>

<div class="pe">
  <div class="btn">Manda a primeira m&atilde;o<small>t.me/KKNUts_BOT</small></div>
  <div class="mini">Gr&aacute;tis no piloto · an&aacute;lise p&oacute;s-sess&atilde;o, sem RTA</div>
</div>"""


def render_card_png(escala: int = 2) -> bytes | None:
    """PNG do card, em `escala`x (2 = 2160x2700, bom para retina e impressão)."""
    import tempfile
    from pathlib import Path

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp) / "card.html"
        alvo.write_text(build_card_html(), encoding="utf-8")
        # o Chromium do container fica num caminho fixo; em outra máquina o
        # launch() acha sozinho. Tentar só o primeiro devolvia None calado.
        import os

        caminho = os.getenv("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
        try:
            with sync_playwright() as p:
                nav = (p.chromium.launch(executable_path=caminho)
                       if os.path.exists(caminho) else p.chromium.launch())
                pag = nav.new_page(
                    viewport={"width": LARGURA, "height": ALTURA},
                    device_scale_factor=escala)
                pag.goto(f"file://{alvo}")
                pag.wait_for_timeout(600)
                png = pag.screenshot(clip={"x": 0, "y": 0,
                                           "width": LARGURA, "height": ALTURA})
                nav.close()
                return png
        except Exception:
            return None
