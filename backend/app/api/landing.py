"""Landing page pública — a porta de entrada comercial do KKNuths.

Servida na raiz do serviço web (mesmo uvicorn do portal /admin), pensada para
ficar atrás do domínio próprio via Caddy. Conteúdo espelha o MANUAL.md
comercial; sem dependências externas (CSS inline, zero JS).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

router = APIRouter()

BOT_URL = "https://t.me/KKNUts_BOT?start=site"

_CSS = """
*{box-sizing:border-box}
:root{--bg:#0F1512;--card:#161D18;--ink:#EDF1ED;--mut:#9AA69F;--felt:#43A97C;
--felt2:#2E7D5B;--gold:#D2A55C;--line:#243029}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;font-size:16px;line-height:1.6}
a{color:var(--felt);text-decoration:none}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
.hero{padding:72px 0 56px;text-align:center;
background:radial-gradient(ellipse at top,#1A2620 0%,var(--bg) 70%)}
.hero .spade{font-size:44px}
h1{font-size:clamp(28px,5vw,44px);margin:12px 0 8px;letter-spacing:-.5px}
h1 em{color:var(--gold);font-style:normal}
.tag{color:var(--mut);font-size:clamp(15px,2.5vw,19px);max-width:640px;margin:0 auto 28px}
.cta{display:inline-block;background:var(--felt);color:#08120D;font-weight:700;
padding:15px 34px;border-radius:10px;font-size:17px;box-shadow:0 6px 24px #43A97C44}
.cta:hover{background:#4FC08D}
.cta.ghost{background:transparent;color:var(--felt);border:1px solid var(--felt);
box-shadow:none;margin-left:10px}
.sub{color:var(--mut);font-size:13px;margin-top:12px}
section{padding:48px 0}
h2{font-size:clamp(21px,3.5vw,28px);margin:0 0 6px;text-align:center}
.lead{color:var(--mut);text-align:center;max-width:620px;margin:0 auto 32px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:22px;border-top:3px solid var(--felt2)}
.card h3{margin:0 0 8px;font-size:16.5px}
.card h3 .ico{margin-right:8px}
.card p{margin:0;color:var(--mut);font-size:14.5px}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;
counter-reset:st}
.step{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px}
.step::before{counter-increment:st;content:counter(st);display:inline-block;
width:30px;height:30px;line-height:30px;text-align:center;border-radius:50%;
background:var(--gold);color:#0F1512;font-weight:800;margin-bottom:10px}
.vs{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:26px;max-width:760px;margin:0 auto}
.vs b{color:var(--gold)}
.faq{max-width:760px;margin:0 auto}
.faq details{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:14px 18px;margin-bottom:10px}
.faq summary{cursor:pointer;font-weight:600}
.faq p{color:var(--mut);font-size:14.5px;margin:10px 0 2px}
footer{border-top:1px solid var(--line);padding:34px 0;text-align:center;
color:var(--mut);font-size:13.5px}
.final{padding:64px 0;text-align:center;
background:radial-gradient(ellipse at bottom,#1A2620 0%,var(--bg) 70%)}
@media(max-width:520px){.cta.ghost{margin:10px 0 0}}
"""

_HTML = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KKNuths — Coach de Poker com IA no Telegram | Análise de mãos que calcula, não acha</title>
<meta name="description" content="Mande suas mãos de poker (print, arquivo, texto ou áudio) e receba análise profissional: equity vs range, ICM, equilíbrio Nash e solver de river. Grátis no Telegram.">
<meta property="og:title" content="KKNuths — pare de achar. Calcule. ♠">
<meta property="og:description" content="Seu coach de poker com IA no Telegram: números calculados, gráficos de range e plano de estudo. 100 análises grátis por mês.">
<meta property="og:type" content="website">
<style>{_CSS}</style>
</head>
<body>

<div class="hero">
  <div class="wrap">
    <div class="spade">♠️</div>
    <h1>Seu coach de poker profissional<br>mora no <em>Telegram</em></h1>
    <p class="tag">Mande a mão do jeito que for mais fácil — print, arquivo, texto colado ou
    áudio — e receba em segundos uma análise técnica de verdade: onde você ganhou,
    onde deixou dinheiro na mesa e o que treinar.</p>
    <a class="cta" href="{BOT_URL}">Começar grátis no Telegram →</a>
    <a class="cta ghost" href="#como">Como funciona</a>
    <div class="sub">100 análises grátis por mês · sem cartão · leva 30 segundos</div>
  </div>
</div>

<section>
  <div class="wrap">
    <div class="vs">
      <h2 style="text-align:left;margin-bottom:10px">A diferença para “perguntar pro ChatGPT”?</h2>
      <p style="color:var(--mut);margin:0">O KKNuths <b>não estima números — ele calcula</b>.
      Equity contra o range real do vilão, pressão de ICM na mesa final, preço exato de cada
      call. All-ins de stack curto saem de <b>equilíbrio Nash computado</b>, rivers importantes
      passam por um <b>solver de verdade</b> — e o gráfico de range 13×13 chega como imagem,
      para você VER o que o coach está falando.</p>
    </div>
  </div>
</section>

<section id="como">
  <div class="wrap">
    <h2>Como funciona</h2>
    <p class="lead">Sem instalar nada, sem configurar nada.</p>
    <div class="steps">
      <div class="step"><b>Abra o bot</b><br>
      <span style="color:var(--mut);font-size:14.5px">t.me/KKNUts_BOT no Telegram e toque em Iniciar.</span></div>
      <div class="step"><b>Mande suas mãos</b><br>
      <span style="color:var(--mut);font-size:14.5px">Print do replay, hand history (.txt), CSV do tracker,
      PDF, texto colado ou áudio. Um torneio inteiro de uma vez.</span></div>
      <div class="step"><b>Receba a análise — e discuta</b><br>
      <span style="color:var(--mut);font-size:14.5px">Leitura street a street com números calculados e plano
      de estudo. Discorde, pergunte, peça a tabela — o coach recalcula.</span></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>O que tem dentro</h2>
    <p class="lead">Ferramentas de nível profissional, em português claro — todo termo técnico explicado.</p>
    <div class="grid">
      <div class="card"><h3><span class="ico">🎯</span>Equity vs range</h3>
      <p>Sua chance real de ganhar contra o conjunto de mãos do vilão — como um profissional pensa, não “vs mão aleatória”.</p></div>
      <div class="card"><h3><span class="ico">🏆</span>ICM e bolha</h3>
      <p>Quanto suas fichas valem em dinheiro real (Malmuth-Harville), bubble factor e o preço certo de cada all-in em torneio.</p></div>
      <div class="card"><h3><span class="ico">⚖️</span>Equilíbrio Nash calculado</h3>
      <p>Jam/fold de stack curto resolvido de verdade — com gráfico de frequências e de EV por mão, em fichas ou sob ICM.</p></div>
      <div class="card"><h3><span class="ico">📊</span>Gráficos de range 13×13</h3>
      <p>A matriz clássica chega como imagem na conversa. Peça “me passa a tabela” e ela vem.</p></div>
      <div class="card"><h3><span class="ico">🎮</span>Simulador e quiz diário</h3>
      <p>Rejogue suas mãos decisão a decisão, compare sua linha com a real e receba um spot seu todo dia às 19h.</p></div>
      <div class="card"><h3><span class="ico">📈</span>Perfil que evolui</h3>
      <p>VPIP, agressividade, 3-bet e o leak da semana — cada mão enviada deixa o coaching mais personalizado.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap faq">
    <h2>Perguntas frequentes</h2>
    <p class="lead"></p>
    <details><summary>Isso é permitido pelas salas de poker?</summary>
    <p>Sim. O KKNuths analisa depois da sessão, sobre arquivos que a própria sala exporta
    para você — a mesma categoria dos trackers usados há 15+ anos. Ele não se conecta à sua
    conta e não dá assistência em tempo real durante o jogo (RTA), que é o que as salas proíbem.</p></details>
    <details><summary>Quais salas são suportadas?</summary>
    <p>GGPoker, PokerStars (inclusive Zoom), Winamax, PartyPoker e 888poker por arquivo ou
    texto — e qualquer sala via print do replay. Cash game e torneio.</p></details>
    <details><summary>Meus dados estão seguros?</summary>
    <p>Suas mãos ficam na sua conta, usadas só para as suas análises e o seu perfil.
    Não compartilhamos seus dados individuais.</p></details>
    <details><summary>Quanto custa?</summary>
    <p>O plano grátis dá 100 análises por mês — com simulador, quiz, gráficos e relatório
    semanal incluídos. Durante o beta, está tudo liberado.</p></details>
  </div>
</section>

<div class="final">
  <div class="wrap">
    <h2>Pare de achar. <em style="color:var(--gold);font-style:normal">Calcule.</em></h2>
    <p class="lead">Sua próxima sessão já pode ser analisada hoje.</p>
    <a class="cta" href="{BOT_URL}">Abrir o KKNuths no Telegram ♠</a>
  </div>
</div>

<footer>
  <div class="wrap">KKNuths ♠ — coach de poker com IA ·
  <a href="{BOT_URL}">t.me/KKNUts_BOT</a> · <a href="/manual">Manual do jogador</a></div>
</footer>

</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing() -> str:
    return _HTML


@router.get("/manual", response_class=HTMLResponse, include_in_schema=False)
async def manual() -> str:
    """Manual do jogador — versão comercial com as imagens reais do produto."""
    from app.api.manual_page import build_manual_html

    return build_manual_html()


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots() -> str:
    # landing indexável; portal de gestão fora dos buscadores
    return "User-agent: *\nAllow: /$\nDisallow: /admin\n"
