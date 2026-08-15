"""A análise entregue começa pelo selo — a narração de tools fica no bastidor.

Caso real — juiz da saída de 31/07, primeiro dia medindo o artefato certo:
nota 3.5/10, com 6 análises "SEM selo de veredito na 1ª linha". O selo
EXISTIA em todas; estava enterrado atrás de "Deixa eu conferir o EV desse
open-shove..." — a frase que o coach escreve antes de chamar cada tool. Com
duas rodadas de tools o preâmbulo ainda saía duplicado ("Deixa eu conferir
a leitura do river..." + "Deixa eu ver que equity...").
"""
from app.agent.llm import _montar_resposta


def test_narracao_pre_tool_e_cortada():
    parts = ["Deixa eu conferir o EV desse open-shove com A7s a 7.9bb.",
             "✅ Você jogou bem — open-shove padrão\n\nCom 7.9bb no CO..."]
    saida = _montar_resposta(parts)
    assert saida.startswith("✅")
    assert "Deixa eu conferir" not in saida


def test_preambulo_duplicado_some_inteiro():
    """Duas rodadas de tools = duas frases de bastidor. Caso real das 10:18."""
    parts = ["Deixa eu conferir a leitura do river e a força do seu range.",
             "Deixa eu ver que equity seus dois pares têm contra o range.",
             "✅ Você jogou bem — largou o river com preço ruim\n\n🟡 *Pré*..."]
    saida = _montar_resposta(parts)
    assert saida.startswith("✅")
    assert "Deixa eu" not in saida


def test_sem_selo_nenhum_bloco_e_descartado():
    """Rodadas esgotadas ou resposta de conversa: o texto pré-tools é a rede
    de segurança e não pode sumir — comportamento antigo preservado."""
    parts = ["Vou calcular a equity desse spot.",
             "Contra 88+ e AQ você tem 41% — o call fica marginal."]
    saida = _montar_resposta(parts)
    assert saida == ("Vou calcular a equity desse spot.\n\n"
                     "Contra 88+ e AQ você tem 41% — o call fica marginal.")


def test_selo_amarelo_e_vermelho_tambem_ancoram():
    assert _montar_resposta(["bastidor", "🟡 Dava pra jogar melhor..."]) \
        .startswith("🟡")
    assert _montar_resposta(["bastidor", "❌ Jogada cara..."]).startswith("❌")


def test_blocos_depois_do_selo_sao_mantidos():
    parts = ["bastidor", "✅ Você jogou bem", "A conta que mais pesa: ..."]
    saida = _montar_resposta(parts)
    assert saida.endswith("A conta que mais pesa: ...")


def test_todos_os_loops_de_tools_usam_a_montagem():
    """Se um caminho novo voltar ao join cru, o preâmbulo volta com ele."""
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm)
    assert 'join(x.strip() for x in parts' not in fonte, \
        "use _montar_resposta(parts) em vez do join cru"
    assert fonte.count("_montar_resposta(parts)") >= 6


# ---- o selo no MEIO do bloco (13/08, juiz em 5.8) ---------------------------

def test_selo_no_meio_do_bloco_tambem_ancora():
    """O modelo colou narração e veredito no MESMO bloco: 'Fecho a análise.'
    e o ✅ duas linhas abaixo. A regra por-bloco mantinha o preâmbulo
    inteiro — entregue assim em produção em 13/08 às 22:01."""
    parts = ["Vou analisar os spots de stack curto das key hands.",
             "KT tinha 50% contra o range largo dele — call trivial. "
             "Fecho a análise.\n\n✅ *Torneio tocado bem — variância, "
             "não erro*\n\n🟡 *QQ (SB, 10bb)* — 3-bet all-in..."]
    saida = _montar_resposta(parts)
    assert saida.startswith("✅")
    assert "Fecho a análise" not in saida
    assert "Vou analisar" not in saida
    assert "🟡 *QQ" in saida, "o corpo depois do selo fica inteiro"


def test_tem_selo_olha_linhas_nao_o_comeco():
    from app.agent.llm import _tem_selo

    assert _tem_selo("bastidor\n✅ veredito")
    assert not _tem_selo("Vou ajustar a notação dos ranges.")
    assert not _tem_selo(None)


# ---- o resgate da conclusão (13/08 21:24, nota 2.5) -------------------------

def test_resgate_devolve_a_analise_quando_o_forcado_tem_selo(monkeypatch):
    import app.agent.llm as llm

    capturado = {}

    def fake_force(client, model, system_blocks, msgs):
        capturado["msgs"] = msgs
        return ("Deixa eu só fechar.\n✅ Você jogou bem — shove padrão\n"
                "Com 8bb...")

    monkeypatch.setattr(llm, "_force_text", fake_force)
    saida = llm._resgatar_conclusao(
        None, "m", [], [{"role": "user", "content": "ctx"}])
    assert saida.startswith("✅"), "o resgate também passa pela montagem"
    # a instrução explícita foi anexada ao último turno de usuário
    ultimo = capturado["msgs"][-1]
    assert ultimo["role"] == "user"
    assert any("selo de veredito" in str(b) for b in ultimo["content"])


def test_resgate_sem_selo_devolve_None(monkeypatch):
    """Forçou e AINDA veio sem veredito: None — quem decide o plano C é o
    chamador (selo de emergência), nunca texto cru de novo."""
    import app.agent.llm as llm

    monkeypatch.setattr(llm, "_force_text",
                        lambda *a: "continuo sem conseguir calcular")
    assert llm._resgatar_conclusao(None, "m", [], []) is None


def test_os_dois_finais_do_coach_passam_pelo_resgate():
    """Fim por stop normal E por rodadas esgotadas: os dois chamam o
    resgate quando não há selo — era exatamente onde a narração vazava."""
    import inspect

    import app.agent.llm as llm

    fonte = inspect.getsource(llm.coach)
    assert fonte.count("_resgatar_conclusao(") == 2


# ---- o plano C com dignidade (13/08 22:26) ----------------------------------

def test_fallback_deterministico_tem_selo_naipe_e_honestidade():
    """'VOCÊ (Tc Kh) em ?' foi entregue como análise. O plano C agora é
    produto: selo na 1ª linha, naipe com ícone, e diz que é o modo seguro."""
    from app.agent.analyzer import _deterministic_summary
    from app.models.canonical import CanonicalHand, PlayerSeat, Stakes

    hand = CanonicalHand(
        hand_id="f1", site="GG", hero="Hero", stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True)],
        hero_cards=["Tc", "Kh"], final_board=[], shown_cards={}, streets=[])
    spots = [{"decision": "call", "street": "preflop", "to_call": 10,
              "pot_before": 35, "required_equity": 0.227}]
    s = _deterministic_summary(hand, spots, net=-1020.0, bb=100.0)
    assert s.startswith("🟡")
    assert "10♣" in s and "K♥" in s        # pretty_cards grafa T como 10
    assert "Tc" not in s and "Kh" not in s
    assert "em ?" not in s and " no ?" not in s
    assert "modo seguro" in s
    assert "equity necessária 22.7%" in s, "os números continuam"
    assert "-10.2 BB" in s
