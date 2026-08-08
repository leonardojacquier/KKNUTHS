"""Persistência no Supabase (Postgres).

Camada fina sobre o cliente supabase-py. Quando `SUPABASE_URL`/`SUPABASE_SERVICE_KEY`
não estão configurados, o repositório fica *desabilitado* e todos os métodos viram
no-op (retornam None) — assim o bot roda em dev sem banco e os testes não tocam rede.
"""
from __future__ import annotations

import logging
from functools import lru_cache, wraps
from typing import Any, Optional

from app.config import get_settings
from app.models.canonical import CanonicalHand

log = logging.getLogger("repository")


def _safe(default):
    """Persistência nunca derruba uma análise: qualquer erro de rede/banco vira
    log + valor default (o chamador já trata None/[] como 'sem banco')."""

    def deco(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            try:
                return fn(self, *args, **kwargs)
            except Exception as exc:
                log.warning("repositorio %s falhou: %s", fn.__name__, exc)
                return default

        return wrapper

    return deco


def _scrub_nul(obj):
    """Remove \\x00 de qualquer string aninhada — Postgres rejeita NUL em
    text/jsonb (22P05) e o INSERT inteiro morre por causa de um byte."""
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, dict):
        return {k: _scrub_nul(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub_nul(v) for v in obj]
    return obj


class Repository:
    def __init__(self) -> None:
        s = get_settings()
        self.enabled = bool(s.supabase_url and s.supabase_service_key)
        self._url = s.supabase_url
        self._key = s.supabase_service_key
        self._client = None

    # ------------------------------------------------------------------
    @property
    def client(self):
        if not self.enabled:
            return None
        if self._client is None:
            from supabase import create_client  # lazy import

            self._client = create_client(self._url, self._key)
        return self._client

    def _guard(self) -> bool:
        if not self.enabled:
            log.debug("repository desabilitado (Supabase não configurado)")
        return self.enabled

    # ------------------------------- users ----------------------------
    @_safe(None)
    def get_or_create_user(
        self, telegram_id: int, username: str | None = None, lang: str = "pt"
    ) -> Optional[dict]:
        if not self._guard():
            return None
        existing = (
            self.client.table("users").select("*").eq("telegram_id", telegram_id).execute()
        )
        if existing.data:
            row = existing.data[0]
            # backfill do nome: usuários antigos foram criados sem username e
            # o portal ficava sem identificação legível
            if username and row.get("username") != username:
                try:
                    self.client.table("users").update({"username": username}) \
                        .eq("telegram_id", telegram_id).execute()
                    row["username"] = username
                except Exception:
                    pass
            return row
        created = (
            self.client.table("users")
            .insert({"telegram_id": telegram_id, "username": username, "lang": lang})
            .execute()
        )
        # AVISO DE CADASTRO NOVO — aqui, e não nos 10 lugares que chamam esta
        # função: usuário nasce num ponto só, e instrumentar os chamadores é
        # receita de esquecer um. Fire-and-forget: se o Telegram falhar, o
        # cadastro continua valendo.
        if created.data:
            try:
                from app.bot.notify import avisar_admin_usuario_novo

                total = None
                try:
                    total = (self.client.table("users")
                             .select("id", count="exact")
                             .execute().count)
                except Exception:
                    pass
                avisar_admin_usuario_novo(username, telegram_id, total)
            except Exception as exc:
                log.debug("aviso de usuário novo falhou: %s", exc)
        return created.data[0] if created.data else None

    @_safe(None)
    def store_raw_file(self, telegram_id: int, content: bytes, fmt: str) -> Optional[str]:
        """Guarda o arquivo bruto no Storage (bucket privado 'uploads').

        Permite auditoria e reprocessamento quando um formato falhar.
        Retorna o caminho no bucket ou None.
        """
        if not self._guard() or not content:
            return None
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = f"{telegram_id}/{stamp}.{fmt or 'bin'}"
        self.client.storage.from_("uploads").upload(
            path, bytes(content), {"content-type": "application/octet-stream"}
        )
        return path

    # ------------------------------ uploads ---------------------------
    @_safe(None)
    def save_upload(
        self, user_id: str, file_url: str | None, fmt: str, site: str | None, confidence: float
    ) -> Optional[str]:
        if not self._guard():
            return None
        row = (
            self.client.table("uploads")
            .insert(
                {
                    "user_id": user_id,
                    "file_url": file_url,
                    "format": fmt,
                    "site": site,
                    "confidence": confidence,
                    "status": "analyzed",
                }
            )
            .execute()
        )
        return row.data[0]["id"] if row.data else None

    # ------------------------------- hands ----------------------------
    @_safe(None)
    def save_hand(
        self, user_id: str, hand: CanonicalHand, upload_id: str | None = None
    ) -> Optional[str]:
        """Upsert por (user_id, site, hand_id) — reenvios não duplicam."""
        if not self._guard():
            return None
        payload = {
            "user_id": user_id,
            "site": hand.site,
            "hand_id": hand.hand_id,
            "format": hand.format.value,
            "canonical": hand.model_dump(mode="json"),
            "played_at": hand.played_at,
        }
        # upsert sobrescreve toda coluna presente no payload — só incluir o
        # upload_id quando há um, para não apagar a linhagem em reprocessamentos
        if upload_id is not None:
            payload["upload_id"] = upload_id
        row = (
            self.client.table("hands")
            .upsert(payload, on_conflict="user_id,site,hand_id")
            .execute()
        )
        return row.data[0]["id"] if row.data else None

    @_safe([])
    def get_all_hands(self, user_id: str, limit: int = 5000) -> list[CanonicalHand]:
        """Histórico completo do usuário (para stats cumulativas)."""
        if not self._guard():
            return []
        res = (
            self.client.table("hands")
            .select("canonical")
            .eq("user_id", user_id)
            .order("played_at", desc=True)
            .limit(limit)
            .execute()
        )
        out = []
        for row in res.data or []:
            try:
                out.append(CanonicalHand.model_validate(row["canonical"]))
            except Exception:
                continue
        return out

    def get_hands_para_perfil(self, user_id: str,
                              limit: int = 5000) -> tuple[list[CanonicalHand], int]:
        """(mãos que contam para o PERFIL, quantas ficaram de fora).

        `compute_player_stats` descarta replay avulso e print — amostra
        escolhida a dedo não vira frequência (o Ricardo apareceu com VPIP
        94% sobre 53 replays que ele escolheu mandar; o real é 26%). Só que
        descartava DEPOIS de baixar e validar tudo. Medido nesta base:

            5000 mãos -> 14.8 MB trafegados e 2.3 s de pydantic, por ENVIO,
                         para jogar a maioria fora

        Filtrando por `canonical->>source_format` no banco, só desce o que
        vai ser usado. A contagem do que sobrou vem de um count barato — sem
        ela, `amostra_viesada` sumia e o aluno que só manda replay perdia o
        aviso de que o perfil dele não mede frequência.

        Se o filtro falhar (PostgREST antigo, coluna JSON diferente), CAI
        PARA o caminho de sempre em vez de devolver lista vazia: número que
        encolhe calado é o defeito que este projeto mais combate.
        """
        from app.analysis.stats import FONTES_COMPLETAS

        if not self._guard():
            return [], 0
        try:
            res = (self.client.table("hands").select("canonical")
                   .eq("user_id", user_id)
                   .in_("canonical->>source_format", sorted(FONTES_COMPLETAS))
                   .order("played_at", desc=True).limit(limit).execute())
            total = (self.client.table("hands").select("id", count="exact")
                     .eq("user_id", user_id).limit(1).execute().count) or 0
        except Exception as exc:
            log.warning("filtro de fonte falhou (%s) — caindo no histórico "
                        "completo", exc)
            todas = self.get_all_hands(user_id, limit)
            return todas, 0
        out = []
        for row in res.data or []:
            try:
                out.append(CanonicalHand.model_validate(row["canonical"]))
            except Exception:
                continue
        return out, max(0, total - len(out))

    @_safe(None)
    def save_hand_analysis(
        self,
        hand_row_id: str,
        structured: dict,
        summary: str,
        embedding: list[float] | None = None,
        modelo: str | None = None,
    ) -> Optional[str]:
        if not self._guard():
            return None
        row = (
            self.client.table("hand_analysis")
            .insert(
                {
                    "hand_id": hand_row_id,
                    # ATENÇÃO AO NOME: esta coluna guarda `net_bb`, o
                    # RESULTADO líquido da mão — NÃO o EV perdido pela
                    # decisão. O nome "ev_loss" já enganou o produto: virou
                    # "(custou 37,4bb)" numa lição de uma mão que o aluno
                    # GANHOU (+40,8bb), e "(custou 12,5bb)" num call de KK que
                    # estava certo. Resultado não mede qualidade de decisão.
                    # Quem for MOSTRAR isso ao aluno tem que chamar de
                    # resultado; quem quiser EV de decisão usa
                    # decisoes_por_street.ev_call_bb, que é conta de verdade.
                    "ev_loss": structured.get("net_bb"),
                    "mistakes": structured.get("spots"),
                    "summary": summary,
                    "embedding": embedding,
                    "modelo": modelo,
                }
            )
            .execute()
        )
        return row.data[0]["id"] if row.data else None

    # --------------------------- player stats -------------------------
    @_safe(None)
    def upsert_player_stats(self, user_id: str, stats: Any) -> None:
        if not self._guard():
            return None
        self.client.table("player_stats").upsert(
            {
                "user_id": user_id,
                "hands": stats.hands,
                "vpip": stats.vpip,
                "pfr": stats.pfr,
                "three_bet": stats.three_bet,
                "af": stats.af,
                "label": stats.label,
                "detail": stats.detail,
            },
            on_conflict="user_id",
        ).execute()

    @_safe(None)
    def snapshot_player_stats(self, user_id: str, stats: Any,
                              net_bb: float | None = None) -> None:
        """Grava um ponto na linha do tempo de evolução (além do upsert atual).

        Os valores gravados são os MESMOS que o /stats exibe (bayes-corrigidos
        quando a flag está ligada) — /evolucao dizendo 'VPIP 100' com /stats
        dizendo '28%' era o mesmo jogador se contradizendo entre comandos."""
        if not self._guard():
            return None
        vpip, pfr, three_bet, af = stats.vpip, stats.pfr, stats.three_bet, stats.af
        try:
            from app.config import get_settings

            if get_settings().bayes_stats:
                from app.analysis.bayes import bayes_stats

                b = bayes_stats(stats)
                vpip = b["vpip"]["mean"]
                pfr = b["pfr"]["mean"]
                three_bet = b["three_bet"]["mean"]
                af = b["af"]["mean"]
        except Exception:
            pass  # correção indisponível: grava cru (melhor que não gravar)
        self.client.table("player_stats_history").insert(
            {
                "user_id": user_id,
                "hands": stats.hands,
                "vpip": vpip,
                "pfr": pfr,
                "three_bet": three_bet,
                "af": af,
                "net_bb": net_bb,
                "label": stats.label,
            }
        ).execute()

    @_safe([])
    def get_stats_history(self, user_id: str, limit: int = 60) -> list[dict]:
        if not self._guard():
            return []
        res = (
            self.client.table("player_stats_history").select("*")
            .eq("user_id", user_id).order("created_at", desc=False)
            .limit(limit).execute()
        )
        return res.data or []

    @_safe([])
    def get_field_averages(self) -> list[dict]:
        """Stats atuais de TODOS os usuários (>=20 mãos) — benchmark do field."""
        if not self._guard():
            return []
        res = (
            self.client.table("player_stats")
            .select("hands, vpip, pfr, three_bet, af")
            .gte("hands", 20).limit(500).execute()
        )
        return res.data or []

    # --------------------------- caderno do coach ----------------------
    @_safe(None)
    def save_note(self, user_id: str, kind: str, note: str) -> None:
        if not self._guard() or not note:
            return None
        self.client.table("player_notes").insert(
            {"user_id": user_id, "kind": kind, "note": note[:500]}
        ).execute()

    @_safe([])
    def get_notes(self, user_id: str, limit: int = 12) -> list[dict]:
        if not self._guard():
            return []
        res = (
            self.client.table("player_notes").select("kind, note, created_at")
            .eq("user_id", user_id).order("created_at", desc=True)
            .limit(limit).execute()
        )
        return res.data or []

    # ------------------------------ billing ---------------------------
    @_safe(None)
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        if not self._guard():
            return None
        res = self.client.table("users").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None

    @_safe(None)
    def update_user_plan(self, user_id: str, plan: str) -> None:
        if not self._guard():
            return None
        self.client.table("users").update({"plan": plan}).eq("id", user_id).execute()

    @_safe(None)
    def add_credits(self, user_id: str, amount: int) -> None:
        if not self._guard():
            return None
        user = self.get_user_by_id(user_id)
        if user:
            new = (user.get("credits") or 0) + amount
            self.client.table("users").update({"credits": new}).eq("id", user_id).execute()

    @_safe(None)
    def upsert_subscription(self, sub: dict) -> None:
        """sub: {user_id, stripe_customer, stripe_sub_id, plan, status, period_end}."""
        if not self._guard():
            return None
        self.client.table("subscriptions").upsert(
            sub, on_conflict="stripe_sub_id"
        ).execute()

    @_safe(None)
    def record_usage(self, user_id: str, type_: str, cost_credits: int = 0) -> None:
        if not self._guard():
            return None
        self.client.table("usage_events").insert(
            {"user_id": user_id, "type": type_, "cost_credits": cost_credits}
        ).execute()

    @_safe([])
    def get_population_hands(self, limit: int = 2000) -> list[CanonicalHand]:
        """Mãos de TODOS os usuários (dados agregados do motor explorativo)."""
        if not self._guard():
            return []
        res = (
            self.client.table("hands").select("canonical")
            .order("created_at", desc=True).limit(limit).execute()
        )
        out = []
        for row in res.data or []:
            try:
                out.append(CanonicalHand.model_validate(row["canonical"]))
            except Exception:
                continue
        return out

    # --------------------------- drills/quiz ---------------------------
    @_safe(None)
    def set_pending_drill(self, telegram_id: int, drill: dict) -> None:
        if not self._guard():
            return None
        self.client.table("pending_drills").upsert(
            {"telegram_id": telegram_id, "drill": drill}, on_conflict="telegram_id"
        ).execute()

    @_safe(None)
    def pop_pending_drill(self, telegram_id: int) -> Optional[dict]:
        """Lê e remove o drill pendente (respondido uma vez só)."""
        if not self._guard():
            return None
        res = (
            self.client.table("pending_drills")
            .select("drill").eq("telegram_id", telegram_id).execute()
        )
        if not res.data:
            return None
        self.client.table("pending_drills").delete().eq("telegram_id", telegram_id).execute()
        return res.data[0]["drill"]

    @_safe(None)
    def get_hand_canonical(self, hand_row_id: str) -> Optional[CanonicalHand]:
        """Mão canônica por id de linha — usada pra re-derivar o gabarito
        de conversas persistidas quando o analyzer evolui."""
        if not self._guard():
            return None
        res = (self.client.table("hands").select("canonical")
               .eq("id", hand_row_id).execute())
        if not res.data:
            return None
        try:
            return CanonicalHand.model_validate(res.data[0]["canonical"])
        except Exception:
            return None

    @_safe(None)
    def update_hand_canonical(self, hand_row_id: str, hand: CanonicalHand) -> None:
        """Regrava o canonical de uma mão — correção de herói dita pelo
        aluno ('eu sou o dscholze1979'): stats, drills e relatórios passam
        a ler a mão do ponto de vista certo."""
        if not self._guard():
            return None
        self.client.table("hands").update(
            {"canonical": _scrub_nul(hand.model_dump(mode="json"))}
        ).eq("id", hand_row_id).execute()

    # -------------------------- metadados do usuário -------------------
    @_safe(None)
    def set_user_meta(self, user_id: str, key: str, value) -> None:
        """Chave/valor por usuário (ex.: payouts do torneio atual)."""
        if not self._guard():
            return None
        self.client.table("user_meta").upsert(
            {"user_id": user_id, "key": key, "value": value,
             "updated_at": "now()"},
            on_conflict="user_id,key",
        ).execute()

    @_safe(None)
    def get_user_meta(self, user_id: str, key: str):
        if not self._guard():
            return None
        res = (self.client.table("user_meta").select("value")
               .eq("user_id", user_id).eq("key", key).execute())
        return res.data[0]["value"] if res.data else None

    # ----------------------- conversa com o coach ----------------------
    @_safe(None)
    def set_conversation(self, telegram_id: int, state: dict) -> None:
        """Contexto+histórico da conversa — regravado a cada troca pra
        sobreviver a restart (a conversa 'esquecia' a mão no deploy)."""
        if not self._guard():
            return None
        self.client.table("conversation_state").upsert(
            {"telegram_id": telegram_id, "state": state,
             "updated_at": "now()"},
            on_conflict="telegram_id",
        ).execute()

    @_safe(None)
    def get_conversation(self, telegram_id: int) -> Optional[dict]:
        if not self._guard():
            return None
        res = (
            self.client.table("conversation_state")
            .select("state").eq("telegram_id", telegram_id).execute()
        )
        return res.data[0]["state"] if res.data else None

    # ------------------------- simulação jogável -----------------------
    @_safe(None)
    def set_pending_sim(self, telegram_id: int, sim: dict) -> None:
        """Estado da simulação em andamento — regravado a cada passo, pra
        sobreviver ao restart do auto-deploy (o quiz já sobrevive; a sim
        morria no meio da mão)."""
        if not self._guard():
            return None
        self.client.table("pending_sims").upsert(
            {"telegram_id": telegram_id, "sim": sim, "updated_at": "now()"},
            on_conflict="telegram_id",
        ).execute()

    @_safe(None)
    def get_pending_sim(self, telegram_id: int) -> Optional[dict]:
        if not self._guard():
            return None
        res = (
            self.client.table("pending_sims")
            .select("sim").eq("telegram_id", telegram_id).execute()
        )
        return res.data[0]["sim"] if res.data else None

    @_safe(None)
    def delete_pending_sim(self, telegram_id: int) -> None:
        if not self._guard():
            return None
        self.client.table("pending_sims").delete().eq(
            "telegram_id", telegram_id).execute()

    @_safe(None)
    def get_player_stats(self, user_id: str) -> Optional[dict]:
        if not self._guard():
            return None
        res = self.client.table("player_stats").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None

    @_safe(None)
    def get_latest_analysis(self, user_id: str) -> Optional[dict]:
        """Última análise do usuário (para retomar o coach após restart)."""
        if not self._guard():
            return None
        res = (
            self.client.table("hand_analysis")
            .select("summary, hands!inner(id, user_id, canonical)")
            .eq("hands.user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        row = res.data[0]
        return {
            "summary": row.get("summary"),
            "hand_row_id": (row.get("hands") or {}).get("id"),
            "canonical": (row.get("hands") or {}).get("canonical"),
        }

    # ------------------------------ eventos ----------------------------
    @_safe(None)
    def log_event(
        self,
        telegram_id: int | None,
        username: str | None,
        event: str,
        detail: dict | None = None,
    ) -> None:
        """Registra qualquer interação com o bot (visibilidade de dashboard)."""
        if not self._guard():
            return None
        self.client.table("bot_events").insert(
            {
                "telegram_id": telegram_id,
                "username": username,
                "event": event,
                # \x00 em string (ex.: excerpt de arquivo binário) derruba o
                # INSERT inteiro (Postgres 22P05) — e o log da falha sumia
                "detail": _scrub_nul(detail or {}),
            }
        ).execute()

    @_safe(0)
    def quiz_streak_days(self, telegram_id: int) -> int:
        """Sequência de DIAS consecutivos (contando hoje ou ontem) em que o
        usuário respondeu quiz/treino — o combustível do 🔥 de retenção."""
        from datetime import date, timedelta

        if not self._guard():
            return 0
        rows = (self.client.table("bot_events").select("created_at")
                .eq("telegram_id", telegram_id).eq("event", "drill_answer")
                .order("created_at", desc=True).limit(400).execute().data) or []
        days = sorted({r["created_at"][:10] for r in rows}, reverse=True)
        if not days:
            return 0
        today = date.today()
        start = days[0]
        # streak vale se a última resposta foi hoje ou ontem (ainda dá pra manter)
        if start not in (today.isoformat(), (today - timedelta(days=1)).isoformat()):
            return 0
        streak = 1
        cur = date.fromisoformat(start)
        for ds in days[1:]:
            if date.fromisoformat(ds) == cur - timedelta(days=1):
                streak += 1
                cur = date.fromisoformat(ds)
            else:
                break
        return streak

    @_safe([])
    def drill_verdicts(self, telegram_id: int, limit: int = 60) -> list[dict]:
        """Últimos vereditos de quiz/treino (detail de drill_verdict: verdict
        boa/mista/ruim + cat) — combustível da repetição espaçada: o sorteio
        do drill puxa as categorias em que o aluno mais erra."""
        if not self._guard():
            return []
        rows = (self.client.table("bot_events").select("detail, created_at")
                .eq("telegram_id", telegram_id).eq("event", "drill_verdict")
                .order("created_at", desc=True).limit(limit).execute().data) or []
        return [r["detail"] for r in rows if isinstance(r.get("detail"), dict)]

    # ------------------------- knowledge base (RAG) -------------------
    @_safe([])
    def search_analysis(
        self, user_id: str, embedding: list[float], limit: int = 8
    ) -> list[dict]:
        if not self._guard():
            return []
        res = self.client.rpc(
            "match_hand_analysis",
            {"p_user_id": user_id, "p_query": embedding, "p_limit": limit},
        ).execute()
        return res.data or []

    # --------------------- memória COLETIVA (entre alunos) -------------
    # Tudo o mais aqui é por aluno: match_hand_analysis trava em user_id, o
    # caderno também. Isto é o único caminho que atravessa alunos — o que o
    # coach aprendeu com as 194 mãos do Ricardo chegando na 4ª do Antonio.
    @_safe([])
    def buscar_conhecimento(self, embedding: list[float], limit: int = 3,
                            min_alunos: int = 1) -> list[dict]:
        if not self._guard() or not embedding:
            return []
        res = self.client.rpc(
            "match_conhecimento",
            {"p_query": embedding, "p_limit": limit,
             "p_min_alunos": min_alunos},
        ).execute()
        return res.data or []

    @_safe(None)
    def salvar_conhecimento(self, kind: str, titulo: str, gatilho: str,
                            texto: str, embedding: list[float] | None,
                            categoria: str | None = None,
                            ev_bb: float | None = None,
                            alunos: int = 1,
                            origem: dict | None = None) -> dict | None:
        if not self._guard():
            return None
        linha = {"kind": kind, "titulo": titulo[:200], "gatilho": gatilho[:400],
                 "texto": texto[:1200], "categoria": categoria,
                 "ev_bb": ev_bb, "alunos": max(1, int(alunos)),
                 "origem": origem or {}}
        if embedding:
            linha["embedding"] = embedding
        res = self.client.table("conhecimento").insert(linha).execute()
        return (res.data or [None])[0]

    @_safe([])
    def listar_conhecimento(self, limit: int = 100) -> list[dict]:
        if not self._guard():
            return []
        res = (self.client.table("conhecimento")
               .select("id, kind, titulo, gatilho, texto, categoria, ev_bb, "
                       "alunos, usos, created_at")
               .order("alunos", desc=True).limit(limit).execute())
        return res.data or []

    @_safe(None)
    def marcar_uso_conhecimento(self, ids: list[str]) -> None:
        """Conta quantas vezes cada saber foi injetado numa análise.

        Sem isso não dá para saber se a memória coletiva serve para alguma
        coisa — é a diferença entre 'temos uma base' e 'a base é usada'.
        """
        if not self._guard() or not ids:
            return None
        self.client.rpc("incrementar_uso_conhecimento",
                        {"p_ids": ids}).execute()
        return None


@lru_cache
def get_repository() -> Repository:
    return Repository()
