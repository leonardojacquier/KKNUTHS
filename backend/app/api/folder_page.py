"""Folder de divulgação — duas páginas A4, síntese comercial do KKNuths.

Servido em /folder (compartilhável) e exportado em PDF (asset) para envio
direto por WhatsApp/Telegram ou impressão em clube.

VERSÃO PILOTO (convite): SEM link do bot. O acesso é dado a dedo, um a um —
o dono chama os testadores pessoalmente. Folder que circula com link vira
cadastro aleatório e o piloto perde o controle da amostra. Se um dia o
acesso abrir, é só voltar o BOT_URL no rodapé e nas barras de CTA.
"""
from __future__ import annotations

from app.api.manual_page import _img

_CSS = """
*{box-sizing:border-box}
:root{--bg:#FBFAF6;--card:#FFFFFF;--ink:#16211A;--mut:#5A665E;--felt:#124A30;
--felt2:#2E7D5B;--gold:#B38D24;--line:#E2E6E0;
--serif:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif}
@page{size:A4;margin:0}
body{margin:0;background:#fff;color:var(--ink);line-height:1.5;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;
print-color-adjust:exact;-webkit-print-color-adjust:exact}
.page{width:210mm;height:296mm;margin:0 auto;padding:8mm 12mm 6mm;overflow:hidden;
display:flex;flex-direction:column;gap:3.5mm;
background:radial-gradient(ellipse at top,#EEF3EC 0%,var(--bg) 62%)}
.brand{display:flex;align-items:center;gap:10px;justify-content:center;
color:var(--mut);font-size:13px;letter-spacing:.18em;text-transform:uppercase}
.brand b{font-family:var(--serif);font-size:22px;color:var(--ink);
letter-spacing:0;text-transform:none}
.brand .logo{width:34px;height:34px;border-radius:50%;align-self:center;
box-shadow:0 1px 4px rgba(0,0,0,.25)}
h1{font-family:var(--serif);font-size:34px;margin:0;text-align:center;
letter-spacing:-.01em;line-height:1.12}
h1 em{color:var(--gold);font-style:normal}
.sub{color:var(--mut);text-align:center;max-width:155mm;margin:0 auto;font-size:12.5px}
.sub b{color:var(--ink)}
.mid{display:grid;grid-template-columns:1.15fr .85fr;gap:6mm;align-items:stretch;flex:1}
.feats{display:flex;flex-direction:column;gap:2.2mm;justify-content:space-between}
.feat{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--felt);
box-shadow:0 1px 3px rgba(0,0,0,.05);
border-radius:10px;padding:5px 11px}
.feat h3{margin:0 0 1px;font-size:13px}
.feat h3 small{color:var(--gold);font-size:10px;letter-spacing:.12em;
text-transform:uppercase;margin-left:6px}
.feat p{margin:0;color:var(--mut);font-size:11px}
.proof{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:10px;display:flex;flex-direction:column;gap:6px;justify-content:center}
.proof img{width:100%;border-radius:8px;display:block}
.proof figcaption{font-size:11px;color:var(--mut);text-align:center}
.sci{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.nobel{display:flex;align-items:center;gap:12px;text-align:left;
background:linear-gradient(135deg,#FDF9EE,#F6EFDD);
border:1px solid #D9C489;border-radius:14px;padding:9px 18px 9px 10px;
box-shadow:0 1px 4px rgba(0,0,0,.06)}
.medal{width:44px;height:44px;border-radius:50%;flex:none;
background:radial-gradient(circle at 32% 28%,#F6E3B4,#D9AC5F 52%,#8C6B33 96%);
border:1px solid #F1D9A7;box-shadow:0 2px 6px rgba(0,0,0,.45);
display:flex;flex-direction:column;align-items:center;justify-content:center;
color:#3A2C12;line-height:1.05}
.medal i{font-style:normal;font-size:7.5px;font-weight:800;letter-spacing:.08em}
.medal b{font-family:var(--serif);font-size:15px;font-weight:700}
.nobel .who{font-size:13.5px;font-weight:700;color:#3A2C12}
.nobel .what{display:block;font-size:11.5px;color:#7A6136}
.chips{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:3mm}
.chip{display:flex;align-items:center;gap:7px;background:var(--card);
border:1px solid var(--line);border-radius:99px;padding:4px 13px;font-size:11.5px;
color:var(--mut)}
.chip b{color:var(--ink)}
.scitit{color:var(--gold);font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;
text-align:center;font-weight:700;margin-bottom:2mm}
.ctabar{margin-top:auto;background:linear-gradient(120deg,#124A30,#0D3A25);
border:1px solid #0D3A25;color:#F3F7F2;border-radius:14px;padding:9px 16px;
display:flex;align-items:center;gap:16px;justify-content:space-between;flex-wrap:wrap}
.ctabar .go{font-family:var(--serif);font-size:19px}
.ctabar .go em{color:#F1D9A7;font-style:normal}
.ctabar .link{background:#F1D9A7;color:#3A2C12;font-weight:800;font-size:15px;
padding:10px 22px;border-radius:10px;white-space:nowrap}
.ctabar small{display:block;color:#BFD3C6;font-size:11.5px}
.foot{color:var(--mut);font-size:10.5px;text-align:center}
.sec{font-family:var(--serif);font-size:23px;margin:0;text-align:center}
.sec em{color:var(--gold);font-style:normal}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:4mm;flex:1}
.grp{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:9px 13px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.grp h4{margin:0 0 4px;font-size:12px;color:var(--felt);letter-spacing:.14em;
text-transform:uppercase;font-family:'IBM Plex Mono',monospace}
.grp ul{margin:0;padding-left:15px;font-size:11px;color:var(--mut);line-height:1.55}
.grp li b{color:var(--ink)}
.x{font-size:8.5px;font-weight:800;letter-spacing:.1em;color:#3A2C12;
background:linear-gradient(160deg,#F1D9A7,#D9AC5F);border-radius:4px;
padding:1px 6px;margin-left:5px;vertical-align:middle}
.cmds{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:8px 13px;font-size:10.5px;color:var(--mut);text-align:center}
.cmds code{font-family:'IBM Plex Mono',monospace;color:var(--felt);font-weight:600;
background:#EFF2EB;border-radius:5px;padding:1px 6px;margin:0 2px;white-space:nowrap}
.steps2{display:flex;gap:4mm}
.step2{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:8px 12px;font-size:11px;color:var(--mut)}
.step2 b{display:block;color:var(--ink);font-size:12.5px;margin-bottom:2px}
.step2 .n{display:inline-block;width:20px;height:20px;border-radius:50%;
background:var(--gold);color:#fff;text-align:center;line-height:20px;
font-weight:800;font-size:11px;margin-right:6px}
.invite{background:#F1D9A7;color:#3A2C12;font-weight:800;font-size:14px;
padding:9px 18px;border-radius:10px;white-space:nowrap;text-align:center;
line-height:1.25}
.invite small{display:block;font-weight:600;font-size:10.5px;color:#6B5525}
.ask{background:linear-gradient(135deg,#FDF9EE,#F6EFDD);border:1px solid #D9C489;
border-radius:12px;padding:9px 14px}
.ask h4{margin:0 0 3px;font-size:12px;color:#7A6136;letter-spacing:.14em;
text-transform:uppercase;font-family:'IBM Plex Mono',monospace}
.ask ul{margin:0;padding-left:15px;font-size:11px;color:#5A4A28;line-height:1.5}
.ask li b{color:#3A2C12}
.two{display:grid;grid-template-columns:1fr 1fr;gap:4mm}
.talk{background:#F4F7F3;border:1px solid var(--line);border-radius:10px;
padding:8px 11px;font-size:11px;color:var(--mut);line-height:1.45}
.talk p{margin:0 0 5px}
.talk p:last-child{margin:0}
.talk b{color:var(--ink)}
.talk .k b{color:var(--gold)}
.proof img+img{margin-top:6px}

"""


def build_folder_html() -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KKNuths &#9824; — Coach de Poker com IA no Telegram</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <div class="brand"><img class="logo" src="{_img('logo_avatar.png')}" alt="KKNuths"><b>KKNuths</b> · coach de poker com IA · no seu Telegram</div>

  <h1>Pare de achar.<br><em>Calcule.</em></h1>
  <p class="sub"><b>Cola o link do replay</b> (PPPoker) e a mão abre sozinha:
  o filme completo com showdown e a leitura de um coach profissional — com
  <b>matemática de solver</b> por trás de cada veredito, street a street.
  Movido pelo <b>Motor KKN</b>.</p>

  <div class="mid">
    <div class="feats">
      <div class="feat"><h3>🔗 Cola o link, sai o filme</h3>
        <p>Replay da PPPoker abre sozinho: a mão inteira quadro a quadro, com
        as cartas do vilão no showdown e quem levou o pote. Print, arquivo e
        áudio também valem — qualquer sala.</p></div>
      <div class="feat"><h3>⚖️ Veredito com número, street a street</h3>
        <p>Toda análise abre com ✅ jogou bem / 🟡 dava pra melhorar / ❌ jogada
        cara — e cada decisão vem com a conta na frente: equity mínima, sua
        equity real e o EV do lance em bb.</p></div>
      <div class="feat"><h3>🎯 Exploit por vilão + timing tells <small>exclusivo</small></h3>
        <p>/vilao monta o dossiê de cada reg do clube com as SUAS mãos —
        stats, showdowns vistos e até o TEMPO das ações (“snap-bet dele foi
        valor em 80% das vezes”). Nenhum tracker faz isso.</p></div>
      <div class="feat"><h3>🧮 Solver de verdade, flop ao river</h3>
        <p>Equilíbrio CFR+ multi-street, ranges Nash com EV mão a mão, motor
        de EV para <b>qualquer all-in</b> (abrir, re-shove, squeeze, pagar) e
        a matriz 13×13 de <b>qualquer mão sua</b> pós-flop.</p></div>
      <div class="feat"><h3>🔬 Você audita a ferramenta <small>exclusivo</small></h3>
        <p>/prova roda sete classes de verificação nas SUAS mãos e mostra as
        falhas na cara — mais a ressalva do que a prova <b>não</b> cobre.
        Você não precisa acreditar: você confere.</p></div>
      <div class="feat"><h3>💸 Leaks em dinheiro + Tilt Detector <small>exclusivo</small></h3>
        <p>“Esse erro custa ~4bb a cada 100 mãos.” E o motor percebe quando o
        pote grande muda o seu jogo — com o custo do desvio.</p></div>
    </div>
    <div class="proof" style="margin:0;justify-content:flex-start;gap:7px">
      <img src="{_img('folder_ev_posflop.png')}" alt="Matriz de EV pós-flop">
      <figcaption>Imagem real do produto: quanto <b>cada mão</b> do seu range
      vale naquele turn, em fichas — equilíbrio CFR+ resolvido a partir da SUA
      mão, direto no Telegram.</figcaption>
      <div class="talk">
        <p><b>Você</b> — paguei certo naquele river?</p>
        <p class="k"><b>&#9824; KKNuths</b> — Não. Você pagou 23,6bb com dois
        pares: precisava de <b>28%</b> e tinha <b>12%</b> contra o range dele.
        O fold poupava <b>23bb</b>. No flop e no turn você jogou bem — o erro
        foi só o último call. 🎬 O filme da mão segue abaixo.</p>
      </div>
    </div>
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
      <span class="chip"><b>CFR+</b> · solver flop→river</span>
      <span class="chip"><b>Monte Carlo</b> · equity e banca</span>
      <span class="chip"><b>ICM</b> · automático</span>
    </div>
  </div>

  <div class="ctabar">
    <div class="go">Fase de <em>testes fechados</em>
      <small>Grátis durante o piloto — 100 análises por mês, sem instalar nada.</small></div>
    <span class="invite">Acesso por convite<small>fale com quem te passou este folder</small></span>
  </div>

  <div class="foot">KKNuths &#9824; · análise <b>pós-sessão</b> sobre replays e
  arquivos exportados pela sala — sem conexão com a sua conta, sem RTA, nada
  rodando enquanto você joga.</div>
</div>

<div class="page">
  <div class="brand"><img class="logo" src="{_img('logo_avatar.png')}" alt="KKNuths"><b>KKNuths</b> · tudo que ele faz por você</div>
  <h1 class="sec" style="font-size:27px">O arsenal <em>completo</em></h1>
  <p class="sub" style="font-size:11.5px">O selo dourado marca o que é
  <b>exclusivo do KKNuths</b> — nenhum tracker ou chatbot do mercado faz.</p>

  <div class="cols">
    <div class="grp"><h4>📥 Análise</h4><ul>
      <li><b>Link de replay (PPPoker)</b>: cola e a mão abre sozinha</li>
      <li><b>O filme da mão</b> com showdown, vencedor e a conta em cada street<span class="x">EXCLUSIVO</span></li>
      <li>Print, .txt (GG/Stars/Winamax/Party/888), texto colado, CSV, áudio e PDF</li>
      <li><b>Leitura declarada</b>: em print, o bot abre dizendo o que leu e o quanto confia<span class="x">EXCLUSIVO</span></li>
      <li><b>Relatório mão a mão</b> — decisão ✅/❌ separada do resultado</li>
    </ul></div>
    <div class="grp"><h4>🎮 Treino</h4><ul>
      <li><b>Quiz diário 19h</b> com AS SUAS mãos + streak 🔥</li>
      <li>O spot que você mais <b>erra</b> volta com mais frequência 🎯<span class="x">EXCLUSIVO</span></li>
      <li><b>/simular</b> — rejogue com menu de sizings (3x/pote/all-in em bb)</li>
      <li><b>/leitura</b> — adivinhe o que o vilão mostrou no showdown</li>
      <li>Card de desafio pronto pro grupo do clube 📣</li>
    </ul></div>
    <div class="grp"><h4>🎯 Perfil &amp; Exploit</h4><ul>
      <li><b>/vilao</b> — dossiê de cada reg com as SUAS mãos<span class="x">EXCLUSIVO</span></li>
      <li><b>Timing tells</b> — o tempo das ações cruzado com showdowns<span class="x">EXCLUSIVO</span></li>
      <li><b>KKN Tilt Detector</b> — o pote grande mudou seu jogo? Custo em bb<span class="x">EXCLUSIVO</span></li>
      <li>Leaks precificados em bb/100, rankeados pelo que devolve mais</li>
      <li><b>Caderno do coach</b>: ele lembra do seu jogo de uma sessão pra outra</li>
    </ul></div>
    <div class="grp"><h4>🧮 Matemática</h4><ul>
      <li><b>Solver CFR+ flop→river</b> — apostas futuras modeladas</li>
      <li><b>/spot</b> — EV de qualquer all-in: abrir, re-shove, squeeze, pagar<span class="x">EXCLUSIVO</span></li>
      <li><b>Gráfico de EV de qualquer mão</b>, não só all-in — a matriz 13×13 do seu range naquele board</li>
      <li><b>PKO/bounty</b> e <b>ICM automático</b> — as contas que ninguém faz na mesa</li>
      <li>Nash com ante, MDF (multiway inclusive), blockers, /banca por Monte Carlo</li>
    </ul></div>
  </div>

  <div class="cmds"><code>/treino</code><code>/simular</code><code>/leitura</code>
  <code>/vilao</code><code>/range</code><code>/spot</code><code>/banca</code>
  <code>/stats</code><code>/evolucao</code><code>/estilo</code><code>/torneio</code>
  <code>/relatorio</code><code>/prova</code><code>/ask</code><code>/manual</code></div>

  <div class="two">
    <div class="steps2" style="flex-direction:column">
      <div class="step2"><b><span class="n">1</span>Peça seu acesso</b>O convite é pessoal, um a um — quem te passou este folder te libera.</div>
      <div class="step2"><b><span class="n">2</span>Mande uma mão</b>Cole o link do replay (ou print/arquivo). 30 segundos até a primeira análise.</div>
      <div class="step2"><b><span class="n">3</span>Discuta com o coach</b>Discorde, pergunte, peça a tabela — ele recalcula e mostra a conta.</div>
    </div>
    <div class="ask"><h4>O que eu preciso de você no teste</h4><ul>
      <li>Mande <b>um torneio inteiro</b> (ou 10 mãos) na primeira semana — é com volume que os leaks aparecem.</li>
      <li>Responda o <b>quiz das 19h</b> por 3 dias seguidos.</li>
      <li><b>Discorde em voz alta.</b> Se um veredito parecer errado, diga ali no chat: ou eu te mostro a conta, ou o erro é meu e vira correção.</li>
      <li>Rode <b>/prova</b> uma vez e me diga o que apareceu.</li>
      <li>Me conte <b>o que faltou</b> — o que você abriria outro programa pra fazer.</li>
    </ul></div>
  </div>

  <div class="ctabar">
    <div class="go">Piloto fechado: <em>10 jogadores</em>
      <small>análise pós-sessão · sem conexão com a sua conta · sem RTA</small></div>
    <span class="invite">Acesso por convite<small>seu acesso é liberado a dedo</small></span>
  </div>
  <div class="foot">KKNuths &#9824; — pare de achar. Calcule.</div>
</div>
</body>
</html>"""
