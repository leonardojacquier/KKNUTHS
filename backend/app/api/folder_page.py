"""Folder de divulgação — duas páginas A4, síntese comercial do KKNuths.

Servido em /folder (compartilhável) e exportado em PDF (asset) para envio
direto por WhatsApp/Telegram ou impressão em clube.

ACESSO ABERTO (decisão do dono, 22/08): o folder LEVA o link do bot.

Até aqui ele circulava sem link, de propósito — o acesso era dado a dedo e
folder com link vira cadastro aleatório, o que tira do piloto o controle da
amostra. O dono decidiu abrir. Consequência aceita: quem receber o folder
entra sozinho, e a amostra deixa de ser escolhida.

Se um dia voltar a fechar, é remover BOT_URL das barras de CTA e do rodapé,
devolver o selo "Acesso por convite" e reverter os dois testes que guardam
isto (test_folder_de_divulgacao.py e test_bayes.py) — os três juntos, senão
o folder e o teste contam versões diferentes da mesma decisão.

DESIGN (22/08): a tese comercial passou a ser a INVERSÃO — todo concorrente
vende "powered by AI"; aqui o argumento é "a IA não faz a conta". É o que a
arquitetura de fato faz (o modelo julga, a matemática calcula, os guardas
conferem) e é o que separa o produto de um wrapper de chatbot.

A página 1 não descreve a análise: ela MOSTRA uma, com o placar street a
street real. O formato de saída do produto virou o dispositivo de layout —
quem lê o folder já sabe o que vai receber no Telegram.

TRÊS RESTRIÇÕES que qualquer mexida futura precisa respeitar:
  1. DUAS PÁGINAS A4 EXATAS (210×296mm). Este arquivo vira PDF; conteúdo a
     mais não rola a página, ele SOME no overflow:hidden.
  2. FONTES DO SISTEMA, nunca @import de Google Fonts — o gerador de PDF
     roda sem rede e a fonte cai em silêncio, quebrando o layout medido.
  3. print-color-adjust:exact em tudo que tem fundo colorido, senão o PDF
     sai com os blocos brancos.
"""
from __future__ import annotations

from app.api.manual_page import _img

def _bot_url() -> str:
    """O @ do bot vem do setting, nunca de literal espalhado pelo HTML."""
    try:
        from app.config import get_settings

        return f"https://t.me/{get_settings().telegram_bot_username}"
    except Exception:
        return "https://t.me/KKNUts_BOT"


def _bot_curto() -> str:
    """t.me/KKNUts_BOT — o que a pessoa digita, sem o https:// na frente."""
    return _bot_url().replace("https://", "")


_CSS = """
*{box-sizing:border-box}
:root{
  --papel:#FBFAF6;      /* creme do folder impresso */
  --carta:#FFFFFF;
  --tinta:#16211A;
  --mut:#5A665E;
  --feltro:#124A30;     /* verde de mesa */
  --feltro2:#0D3A25;
  --verde-claro:#2E7D5B;
  --ouro:#B38D24;
  --ouro-vivo:#D9AC5F;
  --ouro-claro:#F1D9A7;
  --ouro-tenue:#F6EEDC;
  --linha:#E2E6E0;
  --serif:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
  --mono:'SF Mono',ui-monospace,'DejaVu Sans Mono','Courier New',monospace;
}
@page{size:A4;margin:0}
body{margin:0;background:#fff;color:var(--tinta);line-height:1.5;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;
print-color-adjust:exact;-webkit-print-color-adjust:exact}
.page{width:210mm;height:296mm;margin:0 auto;padding:8mm 12mm 6mm;
overflow:hidden;display:flex;flex-direction:column;gap:2.8mm;
background:radial-gradient(ellipse at top,#EEF3EC 0%,var(--papel) 62%);
print-color-adjust:exact}

/* ── marca ─────────────────────────────────────────────────────────── */
.brand{display:flex;align-items:center;gap:10px;justify-content:center;
color:var(--mut);font-size:12.5px;letter-spacing:.18em;text-transform:uppercase}
.brand b{font-family:var(--serif);font-size:22px;color:var(--tinta);
letter-spacing:0;text-transform:none}
.brand .logo{width:34px;height:34px;border-radius:50%;align-self:center;
box-shadow:0 1px 4px rgba(0,0,0,.25)}

/* ── tese ──────────────────────────────────────────────────────────── */
h1{font-family:var(--serif);font-size:36px;margin:0;text-align:center;
letter-spacing:-.015em;line-height:1.06}
h1 em{color:var(--ouro);font-style:italic}
.sub{color:var(--mut);text-align:center;max-width:148mm;margin:0 auto;
font-size:12px;line-height:1.45}
.sub b{color:var(--tinta)}

/* ── O PLACAR: a estrutura É o produto ─────────────────────────────── */
.demo{background:var(--carta);border:1px solid var(--linha);border-radius:12px;
box-shadow:0 1px 3px rgba(0,0,0,.05);overflow:hidden;print-color-adjust:exact}
.demo-cab{background:var(--feltro);color:var(--ouro-claro);
padding:4px 12px;font-size:10px;letter-spacing:.2em;text-transform:uppercase;
display:flex;justify-content:space-between;align-items:center;
print-color-adjust:exact}
.demo-cab span:last-child{font-family:var(--mono);letter-spacing:.06em;
color:#BFD3C6;text-transform:none}
.veredito{font-family:var(--serif);font-size:15px;padding:7px 12px 5px;
border-bottom:1px solid var(--linha)}
.rua{display:grid;grid-template-columns:16px 46px 1fr;gap:8px;
align-items:baseline;padding:3.5px 12px;font-size:10.5px;line-height:1.4}
.rua+.rua{border-top:1px solid #F1F3F0}
.rua .lbl{font-family:var(--mono);font-size:8.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--ouro)}
.rua b{color:var(--tinta)}
.rua p{margin:0;color:var(--mut)}
.demo-pe{background:var(--ouro-tenue);border-top:1px solid var(--linha);
padding:6px 12px;font-size:10.5px;color:#6B5C3C;print-color-adjust:exact}
.demo-pe b{color:#3A2C12}

/* ── grade de argumentos ───────────────────────────────────────────── */
.mid{display:grid;grid-template-columns:1.1fr .9fr;gap:5mm;flex:1;
align-items:stretch}
.feats{display:flex;flex-direction:column;gap:2mm;justify-content:space-between}
.feat{background:var(--carta);border:1px solid var(--linha);
border-left:3px solid var(--feltro);border-radius:10px;padding:4px 11px;
box-shadow:0 1px 3px rgba(0,0,0,.05);print-color-adjust:exact}
.feat h3{margin:0 0 1px;font-size:12.5px}
.feat h3 small{color:var(--ouro);font-size:9.5px;letter-spacing:.12em;
text-transform:uppercase;margin-left:6px}
.feat p{margin:0;color:var(--mut);font-size:10.5px;line-height:1.45}
/* prova: as imagens PREENCHEM a coluna. Sem min-height:0 o flex não deixa
   o filho encolher e sobra caixote branco — foi o defeito da 1ª versão. */
.proof{background:var(--carta);border:1px solid var(--linha);border-radius:12px;
padding:8px;display:flex;flex-direction:column;gap:6px;
print-color-adjust:exact;min-height:0}
.proof figure{margin:0;display:flex;flex-direction:column;gap:3px;
flex:1 1 0;min-height:0}
.proof img{width:100%;flex:1 1 0;min-height:0;object-fit:contain;
object-position:center;border-radius:8px;display:block}
.proof figcaption{font-size:10px;color:var(--mut);text-align:center;flex:none}

/* faixa de comandos */
.cmds{display:flex;flex-wrap:wrap;gap:5px;justify-content:center}
.cmds code{font-family:var(--mono);font-size:10px;background:var(--ouro-tenue);
color:#6B5C3C;border:1px solid var(--linha);border-radius:999px;
padding:2.5px 9px;print-color-adjust:exact}

/* passos + pedido ao testador: é o que faz um piloto valer alguma coisa */
.two{display:grid;grid-template-columns:1fr 1.05fr;gap:3.5mm;flex:1;
align-items:start;min-height:0}
.passos{display:flex;flex-direction:column;gap:2.5mm}
.passo{background:var(--carta);border:1px solid var(--linha);border-radius:12px;
padding:7px 12px;display:flex;gap:9px;align-items:flex-start;
box-shadow:0 1px 3px rgba(0,0,0,.05);print-color-adjust:exact}
.passo .n{flex:none;width:20px;height:20px;border-radius:50%;
background:var(--feltro);color:var(--ouro-claro);font-size:10.5px;
font-weight:800;display:flex;align-items:center;justify-content:center;
print-color-adjust:exact}
.passo b{display:block;font-size:11.5px;margin-bottom:1px}
.passo span{font-size:10.5px;color:var(--mut);line-height:1.4}
.ask{background:var(--feltro);color:#EAF2EC;border-radius:12px;padding:9px 14px;
print-color-adjust:exact}
.ask h4{margin:0 0 5px;font-family:var(--serif);font-size:15px;
color:var(--ouro-claro);font-weight:400}
.ask ul{margin:0;padding-left:15px;font-size:10.5px;line-height:1.5;
color:#CFE0D5}
.ask li{margin-bottom:2.5px}
.ask b{color:#fff}

/* ── ciência: as medalhas ──────────────────────────────────────────── */
.scitit{color:var(--ouro);font-size:10px;letter-spacing:.22em;
text-transform:uppercase;text-align:center;margin-bottom:2.5mm}
.sci{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.nobel{display:flex;align-items:center;gap:11px;text-align:left;
background:var(--carta);border:1px solid var(--linha);border-radius:10px;
padding:6px 13px 6px 8px;box-shadow:0 1px 3px rgba(0,0,0,.05);
print-color-adjust:exact}
.medal{width:44px;height:44px;border-radius:50%;flex:none;color:#211904;
display:flex;flex-direction:column;align-items:center;justify-content:center;
background:radial-gradient(circle at 34% 28%,var(--ouro-claro),var(--ouro) 72%);
border:2px solid var(--ouro);box-shadow:0 1px 4px rgba(0,0,0,.2);
print-color-adjust:exact}
.medal i{font-style:normal;font-size:7.5px;font-weight:800;letter-spacing:.08em}
.medal b{font-family:var(--serif);font-size:15px;font-weight:700;line-height:1}
.nobel .who{font-size:13px;font-weight:700;color:#3A2C12}
.nobel .what{display:block;font-size:11px;color:#7A6136;line-height:1.35}
.chips{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;margin-top:2.5mm}
.chip{display:flex;align-items:center;gap:6px;background:var(--carta);
border:1px solid var(--linha);border-radius:999px;padding:3px 11px;
font-size:10.5px;color:var(--mut);print-color-adjust:exact}
.chip b{color:var(--tinta);font-family:var(--mono);font-size:10px}

/* ── barra de chamada ──────────────────────────────────────────────── */
.ctabar{margin-top:auto;background:linear-gradient(120deg,var(--feltro),var(--feltro2));
color:#EAF2EC;border-radius:14px;padding:9px 16px;display:flex;
align-items:center;justify-content:space-between;gap:12px;
print-color-adjust:exact}
.ctabar .go{font-family:var(--serif);font-size:19px;line-height:1.2}
.ctabar .go em{color:var(--ouro-claro);font-style:normal}
.ctabar small{display:block;color:#BFD3C6;font-size:11px;font-family:system-ui}
.invite{background:var(--ouro-claro);color:#3A2C12;font-weight:800;
font-size:14px;border-radius:10px;padding:7px 14px;text-align:center;
flex:none;print-color-adjust:exact;text-decoration:none;display:block}
.invite small{display:block;color:#6B5C3C;font-weight:600;font-size:10px;
font-family:var(--mono);letter-spacing:-.01em}
.foot{color:var(--mut);font-size:10px;text-align:center;line-height:1.45}
.foot b{color:var(--tinta)}

/* ── página 2 ──────────────────────────────────────────────────────── */
.sec{font-family:var(--serif);font-size:25px;margin:0;text-align:center;
line-height:1.15}
.sec em{color:var(--ouro);font-style:italic}
/* align-items:start impede o card de esticar até o rodapé: sem isso sobra
   meia página em branco dentro das caixas (defeito da 1ª versão) */
.cols{display:grid;grid-template-columns:1fr 1fr;gap:3.5mm;align-items:start}
.grp{background:var(--carta);border:1px solid var(--linha);border-radius:12px;
padding:7px 12px;box-shadow:0 1px 3px rgba(0,0,0,.05);print-color-adjust:exact}
.grp h4{margin:0 0 4px;font-size:11.5px;color:var(--feltro);letter-spacing:.14em;
text-transform:uppercase}
.grp ul{margin:0;padding-left:14px;font-size:10.5px;color:var(--mut);
line-height:1.5}
.grp li{margin-bottom:1.5px}
.grp li b{color:var(--tinta)}
.ex{color:var(--ouro);font-weight:800}
.legenda{text-align:center;font-size:10.5px;color:var(--mut)}
.legenda b{color:var(--ouro)}
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

  <h1>A IA não faz a <em>conta</em>.</h1>
  <p class="sub">Ela lê a mão, julga a jogada e explica em português de mesa.
    <b>Quem calcula é a matemática</b> — equity contra o range real, ICM, equilíbrio
    de Nash, o preço exato de cada call. Você recebe opinião técnica com
    <b>número conferido embaixo</b>, não estimativa de chatbot.</p>

  <div class="demo">
    <div class="demo-cab"><span>O que chega no seu Telegram</span>
      <span>K&#9830;Q&#9830; &#183; BTN &#183; 18.7bb</span></div>
    <div class="veredito">&#128993; Dava pra jogar melhor — o pré nasceu torto,
      o resto você conduziu bem</div>
    <div class="rua"><span>&#128993;</span><span class="lbl">Pré</span>
      <p>abriu 2.8bb com K&#9830;Q&#9830;: com 18.7bb é território de jam —
      <b>empurrar rende +1.49bb contra foldar</b>.</p></div>
    <div class="rua"><span>&#9989;</span><span class="lbl">Flop</span>
      <p>9&#9829;J&#9830;2&#9824; — c-bet 3.9bb: <b>40% de equity</b> com dois
      overs e gutshot. Semi-blefe correto.</p></div>
    <div class="rua"><span>&#9989;</span><span class="lbl">Turn</span>
      <p>5&#9830; — check behind: pegou backdoor flush draw, nada feito.
      Preserva o pote com K high.</p></div>
    <div class="rua"><span>&#9989;</span><span class="lbl">River</span>
      <p>3&#9827; — check behind: sem valor pra apostar nem fold equity pra
      blefar. Xis é claro.</p></div>
    <div class="demo-pe">E fecha como coach fecha: explicando <b>por que</b> a
      jogada decide o spot. Discordou? Responda ali mesmo — <b>&#8220;o vilão era
      tight, só pagava com JJ+&#8221;</b> — e ele refaz as contas com a informação
      nova, e manda o gráfico do range junto.</div>
  </div>

  <div class="mid">
    <div class="feats">
      <div class="feat"><h3>Cola o link, sai o filme <small>exclusivo</small></h3>
        <p>Replay de PPPoker e Suprema abre sozinho: a mão inteira quadro a
        quadro, com a conta em cada street.</p></div>
      <div class="feat"><h3>Veredito com número, street a street</h3>
        <p>Toda análise abre com &#9989; jogou bem / &#128993; dava pra melhorar /
        &#10060; jogada cara — e o placar prova o veredito.</p></div>
      <div class="feat"><h3>Solver de verdade, flop ao river</h3>
        <p>Equilíbrio CFR+ multi-street e ranges Nash com EV mão a mão —
        matemática publicada, não palpite.</p></div>
      <div class="feat"><h3>Você audita a ferramenta <small>exclusivo</small></h3>
        <p>/prova roda sete classes de verificação nas SUAS mãos e mostra as
        falhas na cara. Confiança se comprova.</p></div>
    </div>
    <div class="proof">
      <figure>
        <img src="{_img('site_filme.png')}" alt="O filme da mão, quadro a quadro">
        <figcaption>&#127916; O filme da mão — cada street com a conta na figura</figcaption>
      </figure>
      <figure>
        <img src="{_img('site_card.png')}" alt="Card de desafio pronto pro grupo do clube">
        <figcaption>&#128227; Card pronto pro grupo — o spot vira desafio, com o
          link de volta pro bot</figcaption>
      </figure>
    </div>
  </div>

  <div>
    <div class="scitit">A ciência por trás — incluindo dois Prêmios Nobel</div>
    <div class="sci">
      <span class="nobel"><span class="medal"><i>NOBEL</i><b>2002</b></span>
        <span><span class="who">Daniel Kahneman</span>
        <span class="what">Teoria da Perspectiva &#8594; o Tilt Detector</span></span></span>
      <span class="nobel"><span class="medal"><i>NOBEL</i><b>1994</b></span>
        <span><span class="who">John Nash</span>
        <span class="what">Teoria dos Jogos &#8594; ranges de all-in</span></span></span>
    </div>
    <div class="chips">
      <span class="chip"><b>CFR+</b> solver flop&#8594;river</span>
      <span class="chip"><b>Monte Carlo</b> equity e banca</span>
      <span class="chip"><b>Bayes</b> leitura de vilão</span>
      <span class="chip"><b>ICM</b> automático em torneio</span>
    </div>
  </div>

  <div class="ctabar">
    <div class="go">Manda a primeira mão <em>agora</em>
      <small>Grátis durante o piloto — 50 análises por mês, sem instalar nada.</small></div>
    <a class="invite" href="{_bot_url()}">Abrir no Telegram<small>{_bot_curto()}</small></a>
  </div>

  <div class="foot">KKNuths &#9824; · análise <b>pós-sessão</b> sobre replays e
  arquivos exportados pela sala — sem conexão com a sua conta, sem RTA, nada
  rodando enquanto você joga.</div>
</div>

<div class="page">
  <div class="brand"><img class="logo" src="{_img('logo_avatar.png')}" alt="KKNuths"><b>KKNuths</b> · tudo que ele faz por você</div>

  <h2 class="sec">O arsenal — e o que <em>ninguém mais</em> tem</h2>
  <p class="legenda">O selo <b>exclusivo</b> marca o que nenhum tracker ou
    chatbot do mercado faz.</p>

  <div class="cols">
    <div class="grp">
      <h4>Mandar a mão</h4>
      <ul>
        <li><b>Link de replay</b> (PPPoker e Suprema): cola e a mão abre sozinha
          <span class="ex">exclusivo</span></li>
        <li><b>Torneio inteiro</b>: manda o arquivo do PokerCraft — vem a sessão
          completa, com showdown, vencedor e a conta em cada street</li>
        <li><b>Print, .txt</b> (GG/Stars/Winamax/Party/888), texto colado, CSV,
          áudio e PDF</li>
        <li><b>Leitura declarada</b>: em print, o bot abre dizendo o que leu e o
          quanto confia — errou algo, você corrige na conversa
          <span class="ex">exclusivo</span></li>
      </ul>
    </div>

    <div class="grp">
      <h4>O que volta</h4>
      <ul>
        <li><b>Placar street a street</b> com selo em cada rua — decisão separada
          do resultado</li>
        <li><b>O filme da mão</b>: storyboard quadro a quadro com a matemática na
          figura <span class="ex">exclusivo</span></li>
        <li><b>Gráfico de range 13&#215;13</b> junto da análise — você vê as mãos
          de que ele fala</li>
        <li><b>Relatório mão a mão</b> do torneio: até 150 mãos analisadas, e o
          botão &#128269; reabre cada uma no chat <span class="ex">exclusivo</span></li>
      </ul>
    </div>

    <div class="grp">
      <h4>Treino que gruda</h4>
      <ul>
        <li><b>Quiz diário</b> com AS SUAS mãos + streak &#128293;</li>
        <li><b>/foco</b>: o spot que mais te custa, um por vez, com critério de
          alta escrito antes <span class="ex">exclusivo</span></li>
        <li><b>/simular</b>: rejogue a mão com menu de sizings e compare com a
          linha real</li>
        <li><b>/leitura</b>: adivinhe o que o vilão mostrou no showdown</li>
        <li>Card de desafio pronto pro grupo do clube &#128227;</li>
      </ul>
    </div>

    <div class="grp">
      <h4>Perfil &amp; exploit</h4>
      <ul>
        <li><b>/vilao</b>: dossiê de cada reg do clube com as SUAS mãos
          <span class="ex">exclusivo</span></li>
        <li><b>Timing tells</b>: o tempo das ações cruzado com showdowns
          <span class="ex">exclusivo</span></li>
        <li><b>Leaks em dinheiro</b> + Tilt Detector: onde sua decisão muda
          depois de uma perda <span class="ex">exclusivo</span></li>
        <li><b>/spot</b>: EV de qualquer all-in — abrir, re-shove, squeeze,
          pagar <span class="ex">exclusivo</span></li>
        <li><b>Gráfico de EV de qualquer mão</b>, do flop ao river</li>
        <li><b>Caderno do coach</b>: ele lembra do seu jogo de uma sessão pra
          outra</li>
        <li><b>/banca</b>, <b>/evolucao</b> e <b>/estilo</b>: risco de ruína,
          linha do tempo e o arquétipo que você joga</li>
      </ul>
    </div>
  </div>

  <div class="cmds"><code>/treino</code><code>/simular</code><code>/leitura</code><code>/vilao</code><code>/range</code><code>/spot</code><code>/banca</code><code>/stats</code><code>/evolucao</code><code>/estilo</code><code>/torneio</code><code>/relatorio</code><code>/foco</code><code>/prova</code><code>/ask</code><code>/manual</code></div>

  <div class="two">
    <div class="passos">
      <div class="passo"><span class="n">1</span><span><b>Abra o bot</b>
        <span>Toque no link, dê Iniciar. Sem instalar nada, sem cadastro.</span></span></div>
      <div class="passo"><span class="n">2</span><span><b>Mande uma mão</b>
        <span>Cola o link do replay, o print ou o arquivo. 30 segundos até a primeira análise.</span></span></div>
      <div class="passo"><span class="n">3</span><span><b>Discuta com o coach</b>
        <span>Discorde, pergunte, peça a tabela — ele recalcula e mostra a conta.</span></span></div>
    </div>
    <div class="ask"><h4>O que eu preciso de você no teste</h4><ul>
      <li>Mande <b>um torneio inteiro</b> (ou 10 mãos) na primeira semana — é com
        volume que os leaks aparecem.</li>
      <li>Responda o <b>quiz das 19h</b> por 3 dias seguidos.</li>
      <li><b>Discorde em voz alta.</b> Se um veredito parecer errado, diga ali no
        chat: ou eu te mostro a conta, ou o erro é meu e vira correção.</li>
      <li>Rode <b>/prova</b> uma vez e me diga o que apareceu.</li>
      <li>Me conte <b>o que faltou</b> — o que você abriria outro programa pra fazer.</li>
    </ul></div>
  </div>

  <div class="ctabar">
    <div class="go">Pare de achar. <em>Calcule.</em>
      <small>Toda resposta passa por conferência determinística antes de chegar
      em você — regra é pedido, conferência é garantia.</small></div>
    <a class="invite" href="{_bot_url()}">Abrir no Telegram<small>{_bot_curto()}</small></a>
  </div>

  <div class="foot">KKNuths &#9824; · o coach lembra de você: cada mão enviada
  alimenta seu perfil, e o coaching fica mais seu a cada sessão.</div>
</div>
</body>
</html>"""
