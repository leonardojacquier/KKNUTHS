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
--felt2:#2E7D5B;--gold:#D2A55C;--goldink:#E8C083;--line:#243029;
--serif:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.65;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;font-size:16px;
print-color-adjust:exact;-webkit-print-color-adjust:exact}
a{color:var(--felt);text-decoration:none}
.wrap{max-width:900px;margin:0 auto;padding:0 20px}
.hero{padding:64px 0 46px;text-align:center;
background:radial-gradient(ellipse at top,#1A2620 0%,var(--bg) 70%)}
h1{font-family:var(--serif);font-size:clamp(30px,5.5vw,46px);margin:10px 0 8px;
letter-spacing:-.01em;text-wrap:balance}
h1 em{color:var(--gold);font-style:normal}
.tag{color:var(--mut);max-width:620px;margin:0 auto 24px}
.cta{display:inline-block;background:var(--felt);color:#08120D;font-weight:700;
padding:13px 30px;border-radius:10px;font-size:16px}
h2{font-family:var(--serif);font-size:clamp(22px,3.8vw,31px);margin:0 0 6px;
text-align:center;letter-spacing:-.01em;text-wrap:balance}
h2 .n{color:var(--gold)}
.eyebrow{display:block;text-align:center;color:var(--gold);font-size:11.5px;
letter-spacing:.24em;text-transform:uppercase;font-weight:700;margin:0 0 10px}
section{padding:46px 0}
.lead{color:var(--mut);text-align:center;max-width:660px;margin:0 auto 28px}
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
.final h2{font-size:clamp(24px,4vw,34px)}
.top{font-size:13.5px;display:block;padding:14px 20px}
.strip{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin:28px auto 0;max-width:760px}
.stat{background:rgba(22,29,24,.75);border:1px solid var(--line);border-radius:12px;
padding:12px 24px;min-width:150px}
.stat b{display:block;font-family:var(--serif);font-size:27px;color:var(--gold);line-height:1.2}
.stat span{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em}
.cta2{text-align:center;margin:28px 0 0}
.sci{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:10px}
.sci-row{display:flex;gap:14px;align-items:baseline;background:var(--card);
border:1px solid var(--line);border-radius:10px;padding:13px 17px;flex-wrap:wrap}
.sci-row b{font-size:15px;white-space:nowrap}
.sci-row span{color:var(--mut);font-size:13.5px;flex:1;min-width:220px}
.badge{font-size:11.5px;font-weight:800;letter-spacing:.1em;color:#2E2210;
background:linear-gradient(160deg,#F1D9A7,#D2A55C 60%,#B8873F);
border:1px solid #F1D9A7;border-radius:6px;padding:3px 11px;white-space:nowrap;
box-shadow:0 1px 4px rgba(0,0,0,.4)}
.badge.q{background:transparent;color:var(--goldink);border:1px solid #7A6136;
box-shadow:none;font-weight:700}
.sci-row.gold{border-color:#7A6136;background:linear-gradient(135deg,#232D22,#161D18);
box-shadow:inset 0 1px 0 rgba(232,192,131,.14)}
@media print{
  .top,.cta{display:none}
  .hero{padding:30px 0 22px}
  section,.final{padding:22px 0}
  h2,.eyebrow,.lead{break-after:avoid;page-break-after:avoid}
  .card,.shot,.msg,.sci-row,.faq details,tr,figure,.chat{break-inside:avoid;
  page-break-inside:avoid}
  .grid,.shots{grid-auto-rows:min-content}
}
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
  chega no seu Telegram. Movido pelo <b>Motor KKN</b>: matemática de solver,
  estatística bayesiana e dois Prêmios Nobel de Economia na fundação.</p>
  <a class="cta" href="{BOT_URL}">Abrir o bot agora →</a>
  <div class="strip">
    <div class="stat"><b>5</b><span>motores matemáticos</span></div>
    <div class="stat"><b>2</b><span>Prêmios Nobel na base</span></div>
    <div class="stat"><b>100</b><span>análises grátis / mês</span></div>
  </div>
</div>

<section>
  <div class="wrap">
    <span class="eyebrow">Como começar</span>
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
    <span class="eyebrow">Na prática</span>
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
    <span class="eyebrow">A artilharia</span>
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
    <span class="eyebrow">O diferencial</span>
    <h2>Motor KKN — engenharia de análise, <span class="n">não achismo</span></h2>
    <p class="lead">Cada veredito do coach nasce de motores matemáticos — equilíbrio
    de Nash, inferência bayesiana, simulação Monte Carlo e a teoria da perspectiva
    de Kahneman. A inteligência artificial entra no final, para traduzir o cálculo
    em conversa de mesa.</p>
    <div class="grid">
      <div class="card"><h3>📏 Estatística com rigor científico</h3><p>Suas taxas
      são estimadas por inferência bayesiana, com intervalo de confiança — como
      num estudo de verdade. Amostra curta? O Motor KKN reporta <b>“3-bet entre
      5 e 14%”</b> e vai fechando o intervalo a cada torneio, até cravar.</p></div>
      <div class="card"><h3>💸 Leaks precificados</h3><p>Não é “você folda demais”:
      é <b>“esse leak custa ~4bb a cada 100 mãos”</b>. Cada vazamento do seu jogo
      é detectado, medido e rankeado pelo que devolve mais dinheiro primeiro —
      direto no <code>/stats</code>.</p></div>
      <div class="card"><h3>🚨 KKN Tilt Detector</h3><p>Exclusividade KKNuths: o motor
      monitora seu jogo depois dos potes grandes — perdidos <b>e</b> ganhos. Se o
      padrão muda (<b>“você abre 42% das mãos após uma perda; sua base é
      24%”</b>), ele mostra o desvio e o custo em BB. Nenhum HUD do mercado mede
      isso.</p></div>
      <div class="card"><h3>🔮 Leitura de vilão</h3><p>Pergunte <i>“ele tava
      blefando?”</i> e receba a leitura em odds — <b>“o sizing derrubou blefe de
      40% pra 20%: 4 pra 1 que é valor”</b> — comparada com o preço do seu
      call.</p></div>
      <div class="card"><h3>⚖️ Decisão ≠ resultado</h3><p>Cada mão do relatório
      leva dois selos independentes: <b>decisão</b> (julgada pelo preço na hora)
      e <b>resultado</b>. Ganhar com decisão ruim continua ruim — perder com
      decisão boa é variância. É assim que profissional evolui.</p></div>
      <div class="card"><h3>🌱 Aprende com a base</h3><p>O Motor KKN é calibrado
      com o jogo real da base: cada torneio enviado afia as leituras para
      <b>todos</b> os jogadores. Quanto mais gente estuda, mais forte o coach
      fica.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <span class="eyebrow">As referências</span>
    <h2>A ciência por trás — <span class="n">incluindo dois Prêmios Nobel</span></h2>
    <p class="lead">Um chatbot genérico responde de memória. O KKNuths calcula —
    sobre metodologias publicadas, testadas por décadas e premiadas.</p>
    <div class="sci">
      <div class="sci-row gold"><span class="badge">🏅 NOBEL · 2002</span>
        <b>Teoria da Perspectiva — Daniel Kahneman</b>
        <span>a ciência de como decidimos sob risco (e por que perder dói em
        dobro). É a base do KKN Tilt Detector.</span></div>
      <div class="sci-row gold"><span class="badge">🏅 NOBEL · 1994</span>
        <b>Equilíbrio de Nash — John Nash</b>
        <span>a teoria dos jogos que resolve o all-in: os ranges de shove/call
        do <code>/range</code> saem desse equilíbrio.</span></div>
      <div class="sci-row"><span class="badge q">SÉC. XVIII</span>
        <b>Inferência Bayesiana — Thomas Bayes</b>
        <span>o padrão-ouro de decisão sob incerteza, usado por fundos
        quantitativos e ciência de dados: alimenta a leitura de vilão e as suas
        estatísticas com intervalo.</span></div>
      <div class="sci-row"><span class="badge q">SOLVER</span>
        <b>CFR — Counterfactual Regret Minimization</b>
        <span>o algoritmo dos solvers modernos de poker, rodando nas decisões
        de river.</span></div>
      <div class="sci-row"><span class="badge q">SIMULAÇÃO</span>
        <b>Método de Monte Carlo</b>
        <span>toda equity é calculada por simulação massiva de mãos — nunca
        estimada “de cabeça” pela IA.</span></div>
    </div>
    <p class="cta2"><a class="cta" href="{BOT_URL}">Testar o Motor KKN grátis →</a></p>
  </div>
</section>

<section>
  <div class="wrap">
    <span class="eyebrow">Guia rápido</span>
    <h2>🎮 Comandos</h2>
    <p class="lead"></p>
    <div class="tbl"><table>
      <tr><th style="width:170px">Comando</th><th>O que faz</th></tr>
      <tr><td><code>/stats</code></td><td>Seu perfil de estilo (VPIP, agressividade,
      3-bet) — e com <b>qual grande jogador</b> seu jogo parece (Yuri, Akkari,
      Dwan, Negreanu…). Com o Motor KKN: <b>o que está te custando mais</b>
      (leaks em bb/100) e o <b>KKN Tilt Detector</b>.</td></tr>
      <tr><td><code>/evolucao</code></td><td><b>Sua linha do tempo</b>: gráfico da
      evolução do estilo e do resultado + o caderno de observações que o coach
      mantém sobre o seu jogo. Toque nos botões (VPIP · PFR · 3-bet · AF · BB)
      para ampliar um indicador.</td></tr>
      <tr><td><code>/estilo</code></td><td><b>Cartão de estilo</b>: suas stats
      lado a lado com o arquétipo dos grandes (Yuri, Akkari, Dwan, Negreanu…) e
      botões para traçar a transição — “quero virar LAG” vira meta acompanhada
      pelo coach.</td></tr>
      <tr><td><code>/torneio</code></td><td><b>Quadro do campeonato</b>: KPIs e a
      curva do seu stack mão a mão no último torneio enviado — a história do
      campeonato num olhar (chega automático após o upload).</td></tr>
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
    <span class="eyebrow">Investimento</span>
    <h2>💎 Planos</h2>
    <p class="lead">Uma hora de coach humano custa R$200+. O KKNuths revisa o
    torneio inteiro em minutos — e durante o beta está tudo liberado no Grátis.
    Os melhores testadores ganham benefícios no lançamento. 🎁</p>
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
    <span class="eyebrow">Dúvidas</span>
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
    <p>Suas mãos ficam na sua conta e alimentam as suas análises e o seu perfil.
    De forma <b>agregada e anônima</b>, elas também deixam o Motor KKN mais
    esperto para todo mundo. Seus dados individuais nunca são compartilhados.</p></details>
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
