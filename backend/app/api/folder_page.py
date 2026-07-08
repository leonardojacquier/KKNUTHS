"""Folder de divulgação — UMA página A4, síntese comercial do KKNuths.

Servido em /folder (compartilhável) e exportado em PDF (asset) para envio
direto por WhatsApp/Telegram ou impressão em clube.
"""
from __future__ import annotations

from app.api.manual_page import BOT_URL, _img

_CSS = """
*{box-sizing:border-box}
:root{--bg:#0F1512;--card:#161D18;--ink:#EDF1ED;--mut:#9AA69F;--felt:#43A97C;
--felt2:#2E7D5B;--gold:#D2A55C;--line:#243029;
--serif:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif}
@page{size:A4;margin:0}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;
print-color-adjust:exact;-webkit-print-color-adjust:exact}
.page{width:210mm;height:296mm;margin:0 auto;padding:10mm 13mm 8mm;overflow:hidden;
display:flex;flex-direction:column;gap:5mm;
background:radial-gradient(ellipse at top,#1A2620 0%,var(--bg) 62%)}
.brand{display:flex;align-items:baseline;gap:10px;justify-content:center;
color:var(--mut);font-size:13px;letter-spacing:.18em;text-transform:uppercase}
.brand b{font-family:var(--serif);font-size:21px;color:var(--ink);
letter-spacing:0;text-transform:none}
h1{font-family:var(--serif);font-size:41px;margin:0;text-align:center;
letter-spacing:-.01em;line-height:1.12}
h1 em{color:var(--gold);font-style:normal}
.sub{color:var(--mut);text-align:center;max-width:150mm;margin:0 auto;font-size:13.5px}
.sub b{color:var(--ink)}
.mid{display:grid;grid-template-columns:1.15fr .85fr;gap:6mm;align-items:stretch;flex:1}
.feats{display:flex;flex-direction:column;gap:3mm;justify-content:space-between}
.feat{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--felt2);
border-radius:10px;padding:7px 12px}
.feat h3{margin:0 0 2px;font-size:14.5px}
.feat h3 small{color:var(--gold);font-size:10px;letter-spacing:.12em;
text-transform:uppercase;margin-left:6px}
.feat p{margin:0;color:var(--mut);font-size:12px}
.proof{background:#0B100D;border:1px solid var(--line);border-radius:12px;
padding:10px;display:flex;flex-direction:column;gap:6px;justify-content:center}
.proof img{width:100%;border-radius:8px;display:block}
.proof figcaption{font-size:11px;color:var(--mut);text-align:center}
.sci{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.nobel{display:flex;align-items:center;gap:12px;text-align:left;
background:linear-gradient(135deg,#232D22,#161D18);
border:1px solid #7A6136;border-radius:14px;padding:9px 18px 9px 10px;
box-shadow:inset 0 1px 0 rgba(232,192,131,.14)}
.medal{width:44px;height:44px;border-radius:50%;flex:none;
background:radial-gradient(circle at 32% 28%,#F6E3B4,#D9AC5F 52%,#8C6B33 96%);
border:1px solid #F1D9A7;box-shadow:0 2px 6px rgba(0,0,0,.45);
display:flex;flex-direction:column;align-items:center;justify-content:center;
color:#3A2C12;line-height:1.05}
.medal i{font-style:normal;font-size:7.5px;font-weight:800;letter-spacing:.08em}
.medal b{font-family:var(--serif);font-size:15px;font-weight:700}
.nobel .who{font-size:14.5px;font-weight:700;color:var(--ink)}
.nobel .what{display:block;font-size:11.5px;color:var(--mut)}
.chips{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:3mm}
.chip{display:flex;align-items:center;gap:7px;background:var(--card);
border:1px solid var(--line);border-radius:99px;padding:6px 15px;font-size:12.5px;
color:var(--mut)}
.chip b{color:var(--ink)}
.scitit{color:var(--gold);font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;
text-align:center;font-weight:700;margin-bottom:2mm}
.ctabar{margin-top:auto;background:linear-gradient(120deg,#1B2A22,#16211B);
border:1px solid var(--felt2);border-radius:14px;padding:11px 18px;
display:flex;align-items:center;gap:16px;justify-content:space-between;flex-wrap:wrap}
.ctabar .go{font-family:var(--serif);font-size:21px}
.ctabar .go em{color:var(--gold);font-style:normal}
.ctabar .link{background:var(--felt);color:#08120D;font-weight:800;font-size:15px;
padding:10px 22px;border-radius:10px;white-space:nowrap}
.ctabar small{display:block;color:var(--mut);font-size:11.5px}
.foot{color:var(--mut);font-size:10.5px;text-align:center}
"""


def build_folder_html() -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KKNuths ♠ — Coach de Poker com IA no Telegram</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <div class="brand">♠ <b>KKNuths</b> · coach de poker com IA · no seu Telegram</div>

  <h1>Pare de achar.<br><em>Calcule.</em></h1>
  <p class="sub">Mande o print da mesa ou o arquivo do torneio e receba, em minutos,
  a leitura de um coach profissional — com <b>matemática de solver</b> por trás de
  cada veredito. Movido pelo <b>Motor KKN</b>.</p>

  <div class="mid">
    <div class="feats">
      <div class="feat"><h3>💸 Leaks em dinheiro</h3>
        <p>“Esse erro custa ~4bb a cada 100 mãos.” Cada vazamento do seu jogo é
        detectado, medido e rankeado pelo que devolve mais grana primeiro.</p></div>
      <div class="feat"><h3>🚨 KKN Tilt Detector <small>exclusivo</small></h3>
        <p>O motor percebe quando o pote grande muda o seu jogo — e mostra o
        desvio e o custo. Nenhum HUD do mercado mede isso.</p></div>
      <div class="feat"><h3>🔮 Leitura de vilão em odds</h3>
        <p>“O sizing derrubou blefe de 40% pra 20% — 4 pra 1 que é valor.”
        A leitura do pro, com número e história.</p></div>
      <div class="feat"><h3>📊 Ranges de solver na conversa</h3>
        <p>Nash de all-in, EV mão a mão e pressão de ICM — gerados na hora,
        para o SEU stack, dentro do chat.</p></div>
      <div class="feat"><h3>🃏 Relatório mão a mão + evolução</h3>
        <p>O torneio inteiro analisado, quiz diário com as suas mãos e a linha
        do tempo do seu estilo contra os grandes nomes.</p></div>
    </div>
    <figure class="proof" style="margin:0">
      <img src="{_img('nash_sb10.png')}" alt="Range Nash de all-in SB 10bb">
      <figcaption>Imagem real do produto: equilíbrio Nash de all-in
      calculado para 10bb — direto no Telegram.</figcaption>
    </figure>
  </div>

  <div>
    <div class="scitit">A ciência por trás — incluindo dois Prêmios Nobel</div>
    <div class="sci">
      <span class="nobel"><span class="medal"><i>NOBEL</i><b>2002</b></span>
        <span><span class="who">Daniel Kahneman</span>
        <span class="what">Teoria da Perspectiva → KKN Tilt Detector</span></span></span>
      <span class="nobel"><span class="medal"><i>NOBEL</i><b>1994</b></span>
        <span><span class="who">John Nash</span>
        <span class="what">Teoria dos Jogos → ranges de all-in</span></span></span>
    </div>
    <div class="chips">
      <span class="chip"><b>Bayes</b> · leitura de vilão</span>
      <span class="chip"><b>CFR</b> · solver de river</span>
      <span class="chip"><b>Monte Carlo</b> · equity</span>
    </div>
  </div>

  <div class="ctabar">
    <div class="go">Grátis: <em>100 análises por mês</em>
      <small>30 segundos para a primeira análise — sem instalar nada.</small></div>
    <a class="link" href="{BOT_URL}">t.me/KKNUts_BOT →</a>
  </div>

  <div class="foot">KKNuths ♠ vorte369.com.br · análise pós-sessão sobre arquivos
  exportados pela sala — sem conexão com sua conta, sem RTA.</div>
</div>
</body>
</html>"""
