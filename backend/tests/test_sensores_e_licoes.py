"""Sensores antes de cérebro — a fase 1 que o conselho mandou construir.

Três peças: o card compartilhável ganha origem rastreável (?start=card), o
vigia de anomalias determinístico que funciona com N=6, e o destilador de
lições anônimas que estoca em silêncio (publicar é decisão humana).
"""
from datetime import datetime, timezone

from scripts.anomalias import achar_anomalias
from scripts.destilar_licoes import EV_MINIMO_BB, validar

_AGORA = datetime(2026, 8, 2, 21, 0, tzinfo=timezone.utc)


def _e(tid, event, hora):
    return {"telegram_id": tid, "event": event,
            "created_at": f"2026-08-02T{hora}:00+00:00"}


def test_tropecou_e_sumiu_e_detectado():
    """O padrão do Antônio: bug na 1ª mão, nunca mais voltou."""
    evs = [_e(1, "print_recebido", "10:00"), _e(1, "upload_failed", "10:01")]
    achados = achar_anomalias(evs, _AGORA, {1: "Antônio"})
    assert any("Antônio" in a and "tropeçou" in a for a in achados)


def test_erro_seguido_de_atividade_nao_e_sumico():
    """Falhou mas continuou usando = se resolveu sozinho; não alarmar."""
    evs = [_e(1, "upload_failed", "10:01"), _e(1, "followup", "10:05")]
    assert not any("tropeçou" in a for a in achar_anomalias(evs, _AGORA))


def test_envio_repetido_e_detectado():
    evs = [_e(2, "print_recebido", "11:00"), _e(2, "print_recebido", "11:03"),
           _e(2, "print_recebido", "11:07"), _e(2, "followup", "12:00")]
    achados = achar_anomalias(evs, _AGORA, {2: "Rico"})
    assert any("repetiu" in a for a in achados)


def test_tres_maos_espacadas_nao_sao_briga_com_a_tela():
    evs = [_e(2, "print_recebido", "09:00"), _e(2, "print_recebido", "12:00"),
           _e(2, "print_recebido", "15:00")]
    assert not any("repetiu" in a for a in achar_anomalias(evs, _AGORA))


def test_start_sem_mao_e_o_padrao_do_lucas():
    evs = [_e(3, "start", "02:01"), _e(3, "go_treino", "02:02")]
    achados = achar_anomalias(evs, _AGORA, {3: "Lucas"})
    assert any("Lucas" in a and "/start" in a for a in achados)


def test_start_com_mao_no_mesmo_dia_esta_otimo():
    evs = [_e(3, "start", "02:01"), _e(3, "print_recebido", "02:30")]
    assert not any("/start" in a for a in achar_anomalias(evs, _AGORA))


def test_falha_em_serie_e_defeito_nao_azar():
    evs = [_e(1, "entrega_falha", "09:00"), _e(2, "entrega_falha", "11:00"),
           _e(3, "entrega_falha", "13:00"), _e(1, "followup", "14:00"),
           _e(2, "followup", "14:00"), _e(3, "followup", "14:00")]
    achados = achar_anomalias(evs, _AGORA)
    assert any("entrega_falha" in a and "3x" in a for a in achados)


def test_dia_normal_fica_em_silencio():
    evs = [_e(1, "print_recebido", "10:00"), _e(1, "followup", "10:20"),
           _e(2, "drill_answer", "19:05")]
    assert achar_anomalias(evs, _AGORA) == []


# ---- destilador de lições -------------------------------------------------

_BOA = {"vale": True, "titulo": "Pagar river sem preço",
        "spot": "Torneio, ~20bb efetivos. Vilão dá overbet no river depois "
                "de check-check no turn.",
        "licao": "O call pedia 33% e a mão tinha ~18% — pagar custa 9.3bb. "
                 "Overbet depois de linha passiva é value-heavy.",
        "ev_bb": -9.3, "categoria": "river"}


def test_licao_boa_passa():
    v = validar(dict(_BOA))
    assert v and v["categoria"] == "river" and v["ev_bb"] == -9.3


def test_licao_sem_numero_relevante_nao_e_licao():
    assert validar({**_BOA, "ev_bb": EV_MINIMO_BB - 1}) is None
    assert validar({**_BOA, "ev_bb": "não sei"}) is None


def test_modelo_dizendo_nao_vale_e_respeitado():
    assert validar({**_BOA, "vale": False}) is None


def test_anonimizacao_vazada_descarta_a_licao():
    """Se o nome do clube/sala escapou pra escrita, a lição não entra —
    anonimização é por construção, não por confiança."""
    assert validar({**_BOA, "spot": "No clube Suprema, com ~20bb..."}) is None
    assert validar({**_BOA, "licao": "No PPPoker isso custa 9.3bb."}) is None


def test_categoria_inventada_nao_entra():
    assert validar({**_BOA, "categoria": "psicologia"}) is None


def test_card_compartilhavel_carrega_origem():
    """t.me/BOT?start=card — sem isso, quem chega pelo card é invisível e o
    único loop de crescimento fica sem sensor."""
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers)
    assert "?start=card" in fonte


def test_destilador_nunca_publica_sozinho(monkeypatch):
    """Publicar é decisão humana — uma lição errada no grupo do clube
    destrói a credibilidade com o público exato de aquisição.

    Por COMPORTAMENTO, olhando o que chega ao banco. A versão anterior fazia
    `assert '"publicada": True' not in fonte`, e a gravação real é
    `insert({**licao, "hand_analysis_id": ...})` — se `destilar()` passar a
    devolver `publicada` dentro do dicionário, o literal nunca aparece no
    fonte e o campo vai para a estante mesmo assim. É o mesmo modo de falha
    que deixou passar a inversão de um portão em 09/08.
    """
    from scripts import destilar_licoes as d

    gravados: list[dict] = []

    class _T:
        def insert(self, payload):
            gravados.append(payload)
            return self

        def execute(self):
            return type("R", (), {"data": [{"id": "L1"}]})()

    class _Repo:
        enabled = True

        class client:
            @staticmethod
            def table(_):
                return _T()

        @staticmethod
        def log_event(*a, **k):
            return None

    analise = {"id": "A1", "hero_cards": ["Kh", "Kd"],
               "final_board": ["2c", "7c", "9h"]}
    monkeypatch.setattr(d, "get_repository", lambda: _Repo())
    monkeypatch.setattr(d, "candidatas", lambda *a, **k: [analise])
    monkeypatch.setattr(d, "destilar", lambda _a: {
        "titulo": "Overpair em board seco",
        "corpo": "Com KK em board 2-7-9 você segue apostando.",
        "categoria": "postflop"})

    assert d.main() == 0
    assert gravados, "nada foi gravado — o teste não exercitou a escrita"
    for payload in gravados:
        assert payload.get("publicada") is not True, (
            "o destilador publicou sozinho: `publicada` chegou True ao banco")
        assert payload["hand_analysis_id"] == "A1"
