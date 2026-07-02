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
            return existing.data[0]
        created = (
            self.client.table("users")
            .insert({"telegram_id": telegram_id, "username": username, "lang": lang})
            .execute()
        )
        return created.data[0] if created.data else None

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
            "upload_id": upload_id,
            "site": hand.site,
            "hand_id": hand.hand_id,
            "format": hand.format.value,
            "canonical": hand.model_dump(mode="json"),
            "played_at": hand.played_at,
        }
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

    @_safe(None)
    def save_hand_analysis(
        self,
        hand_row_id: str,
        structured: dict,
        summary: str,
        embedding: list[float] | None = None,
    ) -> Optional[str]:
        if not self._guard():
            return None
        row = (
            self.client.table("hand_analysis")
            .insert(
                {
                    "hand_id": hand_row_id,
                    "ev_loss": structured.get("net_bb"),
                    "mistakes": structured.get("spots"),
                    "summary": summary,
                    "embedding": embedding,
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
                "detail": detail or {},
            }
        ).execute()

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


@lru_cache
def get_repository() -> Repository:
    return Repository()
