"""Manual do jogador — versão comercial, com as imagens REAIS do produto.

Os gráficos embutidos (base64) são gerados pelo próprio motor de ranges do
KKNuths (app/api/assets/*.png, regeneráveis via chart_for_query) — o manual
mostra exatamente o que o usuário vai receber no Telegram.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

BOT_URL = "https://t.me/KKNUts_BOT?start=manual"
_ASSETS = Path(__file__).parent / "assets"


@lru_cache
def _img(name: str) -> str:
    try:
        data = base64.standard_b64encode((_ASSETS / name).read_bytes()).decode()
        return f"data:image/png;base64,{data}"
    except Exception:
        return ""


_CSS = """
*{box-sizing:border-box}
:root{--bg:#0F1512;--card:#161D18;--ink:#EDF1ED;--mut:#9AA69F;--felt:#43A97C;
--felt2:#2E7D5B;--gold:#D2A55C;--line:#243029}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.65;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;font-size:16px;
print-color-adjust:exact;-webkit-print-color-adjust:exact}
a{color:var(--felt);text-decoration:none}
.wrap{max-width:900px;margin:0 auto;padding:0 20px}
.hero{padding:56px 0 40px;text-align:center;
background:radial-gradient(ellipse at top,#1A2620 0%,var(--bg) 70%)}
h1{font-size:clamp(26px,5vw,38px);margin:10px 0 6px}
h1 em{color:var(--gold);font-style:normal}
.tag{color:var(--mut);max-width:600px;margin:0 auto 22px}
.cta{display:inline-block;background:var(--felt);color:#08120D;font-weight:700;
padding:13px 30px;border-radius:10px;font-size:16px}
h2{font-size:clamp(20px,3.5vw,26px);margin:0 0 4px;text-align:center}
h2 .n{color:var(--gold)}
section{padding:38px 0}
.lead{color:var(--mut);text-align:center;max-width:640px;margin:0 auto 26px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:18px 20px;border-top:3px solid var(--felt2)}
.card h3{margin:0 0 6px;font-size:15.5px}
.card p{margin:0;color:var(--mut);font-size:14px}
.chat{max-width:560px;margin:0 auto;background:#0B100D;border:1px solid var(--line);
border-radius:16px;padding:18px}
.msg{max-width:86%;padding:10px 14px;border-radius:14px;margin:8px 0;font-size:14px}
.me{background:var(--felt2);color:#EDF6EF;margin-left:auto;border-bottom-right-radius:4px}
.bot{background:#1C2620;border:1px solid var(--line);border-bottom-left-radius:4px}
.bot b{color:var(--gold)}
.msg img{width:100%;border-radius:8px;margin-top:6px;display:block}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.shot{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.shot img{width:100%;border-radius:8px;display:block}
.shot figcaption{font-size:13px;color:var(--mut);padding:10px 4px 2px}
.shot figcaption b{color:var(--ink)}
figure{margin:0}
table{border-collapse:collapse;width:100%;font-size:14.5px;background:var(--card)}
th,td{border:1px solid var(--line);padding:10px 13px;text-align:left;vertical-align:top}
th{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.05em;background:#131916}
td code{background:#0B100D;border:1px solid var(--line);padding:1px 7px;border-radius:6px;
font-size:13.5px;color:var(--gold);white-space:nowrap}
.tbl{overflow-x:auto;border-radius:10px}
.faq details{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:13px 17px;margin-bottom:9px;max-width:760px;margin-left:auto;margin-right:auto}
.faq summary{cursor:pointer;font-weight:600;font-size:15px}
.faq p{color:var(--mut);font-size:14px;margin:9px 0 2px}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:620px){.duo{grid-template-columns:1fr}}
.pill{display:inline-block;background:#1C2620;border:1px solid var(--felt2);
border-radius:99px;padding:3px 12px;font-size:12px;color:var(--felt);margin:2px}
footer{border-top:1px solid var(--line);padding:30px 0;text-align:center;
color:var(--mut);font-size:13.5px}
.final{padding:52px 0;text-align:center;
background:radial-gradient(ellipse at bottom,#1A2620 0%,var(--bg) 70%)}
.top{font-size:13.5px;display:block;padding:14px 20px}
"""


def build_manual_html() -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manual do Jogador — KKNuths ♠ Coach de Poker com IA</title>
<meta name="description" content="Guia completo do KKNuths: como enviar mãos, o que a análise entrega, gráficos de range e EV, simulador, quiz diário e comandos.">
<style>{_CSS}</style>
</head>
<body>
<a class="top" href="/">← voltar ao site</a>

<div class="hero">
  <div style="font-size:40px">♠️</div>
  <h1>Manual do <em>Jogador</em></h1>
  <p class="tag">Tudo que o KKNuths faz por você — com as imagens REAIS do que
  chega no seu Telegram. Cinco minutos de leitura, anos de leak a menos.</p>
  <a class="cta" href="{BOT_URL}">Abrir o bot agora →</a>
</div>

<section>
  <div class="wrap">
    <h2>📥 Envie suas mãos <span class="n">do seu jeito</span></h2>
    <p class="lead">Qualquer formato. De qualquer sala. Sem configurar nada.</p>
    <div class="grid">
      <div class="card"><h3>📸 Print ou foto</h3><p>Print do replay ou da mesa — o
      KKNuths lê cartas, stacks, posições e a ação completa. Funciona para
      <b>qualquer</b> sala.</p></div>
      <div class="card"><h3>📄 Arquivo de mãos (.txt)</h3><p>GGPoker (PokerCraft →
      download), PokerStars — inclusive Zoom —, Winamax, PartyPoker e 888poker.
      Um torneio inteiro de uma vez.</p></div>
      <div class="card"><h3>📋 Texto colado</h3><p>Cole a sessão direto no chat. O
      Telegram cortou em partes? Cole em sequência que o bot <b>remonta tudo
      sozinho</b> — e responda “analisar” se quiser fechar a conta.</p></div>
      <div class="card"><h3>📊 CSV do tracker</h3><p>Hold'em Manager, PokerTracker
      e afins — os resumos entram no seu perfil e nos relatórios.</p></div>
      <div class="card"><h3>🎙️ Áudio</h3><p>Grave a pergunta por voz. O coach
      entende e responde — no seu contexto, com as suas mãos.</p></div>
      <div class="card"><h3>📑 PDF</h3><p>Relatórios em PDF também são lidos.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>💬 Assim é <span class="n">uma análise</span></h2>
    <p class="lead">Números calculados — nunca estimados — e o gráfico junto, na conversa.</p>
    <div class="chat">
      <div class="msg me">cola o hand history do torneio 📄</div>
      <div class="msg bot"><b>📊 54 mãos lidas de GGPoker.</b><br><br>
      No river do A3o, você precisava de <b>31,2% de equity</b> para pagar —
      contra o range do vilão você tinha <b>45,5%</b>: call correto e lucrativo.
      A extração no turn+river foi valor máximo (+22,4 BB). Seu leak está nos
      opens de posição inicial…</div>
      <div class="msg me">e se eu tivesse só dado call no turn?</div>
      <div class="msg bot">Aí você deixa <b>~1.900 fichas</b> na mesa: com 71% de
      equity no flop e o vilão pagando duas streets com TT, a linha agressiva
      domina. Quer ver o equilíbrio de all-in para o seu stack?</div>
      <div class="msg me">me passa a tabela 👊</div>
      <div class="msg bot">Segue o equilíbrio calculado 👇
      <img src="{_img('nash_sb10.png')}" alt="Range Nash SB 10bb"></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>📊 Os gráficos que <span class="n">só o KKNuths</span> te manda</h2>
    <p class="lead">Matriz 13×13 clássica — gerada na hora, do equilíbrio calculado,
    para o SEU stack. Peça na conversa ou use <code style="background:#0B100D;
    border:1px solid var(--line);padding:1px 7px;border-radius:6px;color:var(--gold)">/range</code>.</p>
    <div class="shots">
      <figure class="shot"><img src="{_img('btn_open.png')}" alt="Range de open BTN">
      <figcaption><b>Open-raise por posição</b> · <code>/range btn</code> — o range de
      referência para cada assento da mesa.</figcaption></figure>
      <figure class="shot"><img src="{_img('nash_sb10.png')}" alt="Nash SB 10bb">
      <figcaption><b>Equilíbrio Nash de all-in</b> · <code>/range sb 10</code> — jam/fold
      resolvido de verdade, com frequências mistas.</figcaption></figure>
      <figure class="shot"><img src="{_img('ev_sb10.png')}" alt="EV por mão (fichas)">
      <figcaption><b>EV de cada mão em fichas</b> · <code>/range sb 10 ev</code> — verde:
      empurrar rende mais que foldar; vermelho: fold é melhor. Em BB, mão por mão.</figcaption></figure>
      <figure class="shot"><img src="{_img('icm_sb10.png')}" alt="EV por mão sob ICM">
      <figcaption><b>O mesmo, sob pressão de ICM</b> · <code>/range sb 10 icm 1.5</code> —
      perto da bolha o dinheiro muda a conta. Compare com o chip-EV ao lado.</figcaption></figure>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>🎮 Comandos</h2>
    <p class="lead"></p>
    <div class="tbl"><table>
      <tr><th style="width:170px">Comando</th><th>O que faz</th></tr>
      <tr><td><code>/stats</code></td><td>Seu perfil de estilo (VPIP, agressividade,
      3-bet) — e com <b>qual grande jogador</b> seu jogo parece (Yuri, Akkari,
      Dwan, Negreanu…).</td></tr>
      <tr><td><code>/evolucao</code></td><td><b>Sua linha do tempo</b>: gráfico da
      evolução do estilo e do resultado + o caderno de observações que o coach
      mantém sobre o seu jogo.</td></tr>
      <tr><td><code>/simular</code></td><td><b>Simulador</b>: jogue uma mão SUA de novo,
      decisão a decisão, com botões — no final o coach compara sua linha com a real
      e dá o veredito do “e se”.</td></tr>
      <tr><td><code>/treino</code></td><td>Drill rápido: um spot seu — o que você faria?</td></tr>
      <tr><td><code>/range btn</code><br><code>/range sb 10</code><br>
      <code>/range sb 10 ev</code><br><code>/range sb 10 icm 1.5</code></td>
      <td>Os gráficos da galeria acima: open por posição, Nash de all-in/call por
      stack, EV por mão em fichas e sob ICM.</td></tr>
      <tr><td><code>/ask</code> + pergunta</td><td>Busca no seu histórico:
      <i>“/ask minhas maiores perdas no river”</i>.</td></tr>
      <tr><td><code>/plano</code></td><td>Seu plano e limites do mês.</td></tr>
    </table></div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="duo">
      <div class="card"><h3>🃏 Quiz do dia — 19h</h3><p>Um spot REAL das suas mãos:
      “o que você faz?”. Responda no botão e veja na hora se acertou. Estudo diário
      sem esforço.</p></div>
      <div class="card"><h3>📅 Resumo da semana — domingo</h3><p>Suas mãos, resultado,
      evolução das estatísticas e o <b>leak da semana</b> — o erro que mais custou,
      para focar o estudo.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>💎 Planos</h2>
    <p class="lead">Durante o beta, tudo liberado no Grátis. Os melhores testadores
    ganham benefícios no lançamento. 🎁</p>
    <div class="tbl"><table>
      <tr><th></th><th>Grátis</th><th>Pro <i style="color:var(--mut)">(em breve)</i></th></tr>
      <tr><td>Análises por mês</td><td><b>100</b></td><td>Ilimitadas</td></tr>
      <tr><td>Torneio completo + história</td><td>✔️</td><td>✔️</td></tr>
      <tr><td>Simulador, quiz e gráficos</td><td>✔️</td><td>✔️</td></tr>
      <tr><td>Voz, prints, todos os formatos</td><td>✔️</td><td>✔️</td></tr>
      <tr><td>Relatório semanal</td><td>✔️</td><td>✔️</td></tr>
      <tr><td>Solver e exploit avançados</td><td>—</td><td>✔️</td></tr>
    </table></div>
  </div>
</section>

<section>
  <div class="wrap faq">
    <h2>❓ Perguntas frequentes</h2>
    <p class="lead"></p>
    <details><summary>Isso é permitido pelas salas de poker?</summary>
    <p>Sim. O KKNuths analisa <b>depois da sessão</b>, sobre arquivos que a própria
    sala exporta para você — a mesma categoria dos trackers usados há 15+ anos. Ele
    não se conecta à sua conta e não dá assistência em tempo real (RTA), que é o
    que as salas proíbem.</p></details>
    <details><summary>O coach pode errar?</summary>
    <p>Os números são calculados — esses não erram. A leitura estratégica é opinião
    técnica de alto nível: use como um coach humano, questionando e discutindo — é
    para isso que a conversa existe.</p></details>
    <details><summary>Meus dados estão seguros?</summary>
    <p>Suas mãos ficam na sua conta, usadas só para as suas análises e o seu
    perfil. Não compartilhamos seus dados individuais.</p></details>
    <details><summary>Colei o histórico e o Telegram cortou no meio.</summary>
    <p>Cole as partes em sequência que o KKNuths remonta tudo sozinho. Se ele ficar
    aguardando, responda “analisar”.</p></details>
    <details><summary>Não achei minha sala na lista.</summary>
    <p>Manda um print que funciona para qualquer sala — e nos avise qual é a sua:
    adicionamos suporte rapidinho.</p></details>
  </div>
</section>

<div class="final">
  <div class="wrap">
    <h2>Pare de achar. <span class="n">Calcule.</span> ♠</h2>
    <p class="lead">Grátis, no Telegram, em 30 segundos.</p>
    <a class="cta" href="{BOT_URL}">Começar agora →</a>
    <p style="color:var(--mut);font-size:13px;margin-top:14px">Convide a galera:
    compartilhe <a href="https://t.me/KKNUts_BOT?start=convite">t.me/KKNUts_BOT</a> —
    poker se estuda melhor em grupo.</p>
  </div>
</div>

<footer>KKNuths ♠ — pare de achar. Calcule.</footer>
</body>
</html>"""
