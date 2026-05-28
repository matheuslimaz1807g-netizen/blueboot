"""
bot_runner.py – Thread-safe Telethon lifecycle manager.

Runs the asyncio event loop in a dedicated daemon thread so it doesn't
block the Flask web server running in the main thread.

Uses polling (get_messages every 10s) instead of NewMessage events,
since Telegram doesn't always deliver events to channels where the account
is only a subscriber — polling is more reliable in this scenario.
"""
from __future__ import annotations

import asyncio
import hashlib
import random
import re
import threading
import time
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import ResolveUsernameRequest

from pipeline import processar_mensagem

# ── Constants ────────────────────────────────────────────────────────────────

_POLL_INTERVAL_SECONDS = 10
_PRODUCT_DEDUP_TTL_SECONDS = 24 * 60 * 60
_PRODUCT_DEDUP_LIMIT = 2_000
_SEEN_MESSAGE_LIMIT = 5_000
_AUTH_TIMEOUT_SECONDS = 30
_FETCH_TIMEOUT_SECONDS = 15
_POLL_MESSAGES_LIMIT = 10
_SEED_MESSAGES_LIMIT = 5
_CONFIG_LOG_INTERVAL_SECONDS = 600
_TZ_BR = timezone(timedelta(hours=-3))

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_PRICE_RE = re.compile(r"r\$\s*([\d.,]+)", re.IGNORECASE)
_AVOID_TERMS = frozenset(
    ["compre", "link", "aqui", "grupo", "oferta", "desconto",
     "cupom", "off", "site", "clique", "ativo", "liberado", "enviado", "valor"]
)
_STORE_MAP = {
    "mercadolivre": "Mercado Livre",
    "meli.la":      "Mercado Livre",
    "aliexpress":   "AliExpress",
    "a.aliexpress": "AliExpress",
    "shopee":       "Shopee",
}


# ── Small value objects ───────────────────────────────────────────────────────

@dataclass
class DailyStats:
    processed: int = 0
    telegram:  int = 0
    whatsapp:  int = 0
    errors:    int = 0
    day: object = field(default_factory=lambda: datetime.now(timezone.utc).date())

    def reset_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).date()
        if self.day != today:
            self.processed = self.telegram = self.whatsapp = self.errors = 0
            self.day = today

    def as_dict(self) -> dict:
        return {
            "today_processed": self.processed,
            "today_telegram":  self.telegram,
            "today_whatsapp":  self.whatsapp,
            "errors_24h":      self.errors,
            "day":             self.day,
        }


@dataclass
class QueueItem:
    fingerprint: str
    message: object


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_preview(message) -> str:
    """Build a short human-readable summary of a Telegram message."""
    text: str = (
        getattr(message, "raw_text", None)
        or getattr(message, "message", None)
        or ""
    )
    if not text:
        return "Mensagem sem texto"

    price_match = _PRICE_RE.search(text)
    price = f"R$ {price_match.group(1).strip()}" if price_match else ""

    text_lower = text.lower()
    store = next((v for k, v in _STORE_MAP.items() if k in text_lower), "")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = ""
    for line in lines:
        ll = line.lower()
        if "http" in ll or line.startswith("#"):
            continue
        if any(t in ll for t in _AVOID_TERMS):
            continue
        if len(line) >= 5:
            title = re.sub(r"#\w+", "", line).strip()
            break

    if not title:
        title = next((ln for ln in lines if not ln.startswith("#")), "Mensagem sem texto")

    parts = [p for p in (title, price, store) if p]
    preview = " | ".join(parts)
    return (preview[:65] + "…") if len(preview) > 65 else preview


def _compute_product_fingerprint(message) -> str:
    """Stable content-based fingerprint for deduplication."""
    raw = getattr(message, "raw_text", "") or ""
    normalized = (
        unicodedata.normalize("NFKD", raw)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )

    urls = [
        re.sub(r"^https?://", "", m.strip().strip("`'\"()[]{}<>.,;!").split("#")[0].split("?")[0]).rstrip("/")
        for m in _URL_RE.findall(normalized)
    ]
    urls = [u for u in urls if u]

    text_no_urls = _URL_RE.sub(" ", normalized)
    lines = [
        ln.strip()
        for ln in text_no_urls.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ][1:]  # skip first line (usually channel name / header)

    title = ""
    for line in lines:
        cleaned = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", line)).strip()
        if len(cleaned) >= 8:
            title = cleaned[:140]
            break

    prices = [re.sub(r"\D", "", p) for p in _PRICE_RE.findall(normalized)]
    prices = [p for p in prices if p]

    parts: list[str] = []
    if title:
        parts.append(f"title:{title}")
    if prices:
        parts.append(f"price:{prices[-1]}")
    if urls:
        parts.append(f"url:{urls[0]}")

    if not parts:
        chat_id = getattr(getattr(message, "chat", None), "id", "")
        msg_id  = getattr(message, "id", "")
        parts.append(f"message:{chat_id}:{msg_id}")

    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ── BotRunner ─────────────────────────────────────────────────────────────────

class BotRunner:
    """
    Controls the full lifecycle of the Telethon client.

    Thread-safety contract:
      - All asyncio calls happen inside ``self._loop`` (dedicated thread).
      - Flask routes interact via ``self._stats``, ``self._status``
        which are protected by ``self._lock``.
    """

    def __init__(
        self,
        log_callback: Callable[[str, str], None],
        activity_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._log = log_callback
        self._activity = activity_callback

        # Threading primitives
        self._lock   = threading.Lock()
        self._loop:   Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        # Telethon
        self._client:     Optional[TelegramClient] = None
        self._stop_event: Optional[asyncio.Event]  = None

        # Auth (set dynamically during auth flow)
        self._auth_event:   Optional[asyncio.Event] = None
        self._auth_success: bool = False
        self._phone_hash:   object = None

        # Runtime state
        self._status_val: str = "stopped"
        self._config:     dict = {}
        self._delay:      int  = 3
        self._stats = DailyStats()

        # Polling cursors
        self._last_seen_by_chat:   dict[int, int]            = {}
        self._seen_messages:       set[tuple[int, int]]       = set()
        self._seen_message_order:  deque[tuple[int, int]]     = deque()

        # Delivery queue
        self._delivery_queue:       Optional[asyncio.Queue]   = None
        self._delivery_worker_task: Optional[asyncio.Task]    = None
        self._next_dispatch_at:     float                     = 0.0
        self._active_delivery_item: Optional[QueueItem]       = None
        self._queue_snapshot:       list[dict]                = []

        # Product deduplication
        self._pending_fingerprints: set[str]               = set()
        self._recent_fingerprints:  dict[str, float]       = {}
        self._recent_fp_order:      deque[tuple[str, float]] = deque()

        # Misc
        self._last_config_log_time: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, config: dict) -> None:
        """Start the bot. No-op if already running."""
        with self._lock:
            if self._status_val == "running":
                return
            self._config = config
            self._delay  = int(config.get("delay_segundos", 3))

        self._loop   = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="TelethonLoop",
        )
        self._thread.start()

    def stop(self) -> None:
        """Gracefully stop the bot and join the background thread."""
        loop      = self._loop
        stop_evt  = self._stop_event
        auth_evt  = self._auth_event

        if loop:
            if stop_evt:
                loop.call_soon_threadsafe(stop_evt.set)
            if auth_evt:
                loop.call_soon_threadsafe(auth_evt.set)

        if self._thread:
            self._thread.join(timeout=10)

        with self._lock:
            self._status_val = "stopped"

    def submit_code(self, code: str, password: str = "") -> dict:
        """Submit Telegram login code or 2FA password from Flask thread."""
        if not self._loop or not self._client:
            return {"ok": False, "error": "Bot não está rodando."}

        async def _do_auth() -> dict:
            try:
                if password:
                    await self._client.sign_in(password=password)
                else:
                    await self._client.sign_in(self._config.get("phone", ""), code)
                session_str       = self._client.session.save()
                self._auth_success = True
                if self._auth_event:
                    self._auth_event.set()
                return {"ok": True, "session_string": session_str}
            except SessionPasswordNeededError:
                return {"ok": False, "requires_password": True}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        future = asyncio.run_coroutine_threadsafe(_do_auth(), self._loop)
        try:
            return future.result(timeout=_AUTH_TIMEOUT_SECONDS)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def status(self) -> str:
        with self._lock:
            return self._status_val

    def get_stats(self) -> dict:
        with self._lock:
            self._stats.reset_if_new_day()
            stats = self._stats.as_dict()
            queue_size = self._delivery_queue.qsize() if self._delivery_queue else 0
            stats["delivery_queue_size"]    = queue_size
            stats["next_dispatch_seconds"]  = max(0, int(self._next_dispatch_at - time.time()))
            return stats

    def get_queue_items(self) -> list[dict]:
        """Thread-safe snapshot of the delivery queue with estimated ETAs."""
        with self._lock:
            return list(self._queue_snapshot)

    def update_config(self, config: dict) -> None:
        with self._lock:
            self._config = config
            self._delay  = int(config.get("delay_segundos", 300))

    # ── Deduplication ─────────────────────────────────────────────────────────

    def _remember_message(self, chat_id: int, msg_id: int) -> bool:
        """Return False if the (chat_id, msg_id) pair was already seen."""
        key = (chat_id, msg_id)
        with self._lock:
            if key in self._seen_messages:
                return False
            if len(self._seen_message_order) >= _SEEN_MESSAGE_LIMIT:
                self._seen_messages.discard(self._seen_message_order.popleft())
            self._seen_message_order.append(key)
            self._seen_messages.add(key)
        return True

    def _remember_product(self, fingerprint: str) -> bool:
        """Return False if this product fingerprint is pending or recently sent."""
        now = time.time()
        with self._lock:
            self._prune_fingerprints(now)
            if fingerprint in self._pending_fingerprints:
                return False
            if fingerprint in self._recent_fingerprints:
                return False
            self._pending_fingerprints.add(fingerprint)
        return True

    def _finish_product(self, fingerprint: str, *, remember: bool = True) -> None:
        """Mark a product as no longer pending; optionally persist it."""
        now = time.time()
        with self._lock:
            self._pending_fingerprints.discard(fingerprint)
            if remember:
                self._recent_fingerprints[fingerprint] = now
                self._recent_fp_order.append((fingerprint, now))
            self._prune_fingerprints(now)

    def _prune_fingerprints(self, now: float) -> None:
        """Must be called under self._lock."""
        while self._recent_fp_order:
            fp, created = self._recent_fp_order[0]
            if (
                now - created <= _PRODUCT_DEDUP_TTL_SECONDS
                and len(self._recent_fp_order) <= _PRODUCT_DEDUP_LIMIT
            ):
                break
            self._recent_fp_order.popleft()
            if self._recent_fingerprints.get(fp) == created:
                self._recent_fingerprints.pop(fp, None)

    # ── Queue snapshot ─────────────────────────────────────────────────────────

    def _refresh_queue_snapshot(self) -> None:
        """Rebuild the ETA snapshot. MUST be called from the asyncio loop thread."""
        items: list[dict] = []
        try:
            active = self._active_delivery_item
            # Build full ordered list: active item first, then queued items
            # We access _queue._queue only here, inside the asyncio thread —
            # this is acceptable since no other coroutine modifies the queue concurrently.
            queued: list[QueueItem] = list(self._delivery_queue._queue) if self._delivery_queue else []
            full = ([active] if active else []) + queued

            now        = time.time()
            sim_time   = max(self._next_dispatch_at, now)
            burst_used = 0
            delay      = self._delay if self._delay > 0 else 300

            for idx, item in enumerate(full):
                if not isinstance(item, QueueItem):
                    continue
                eta_str  = datetime.fromtimestamp(sim_time, tz=_TZ_BR).strftime("%H:%M:%S")
                preview  = _extract_preview(item.message)
                items.append({"preview": preview, "eta": eta_str})

                # Simulate burst / cooldown for next slot
                remaining_after = len(full) - (idx + 1)
                if remaining_after >= 3 and burst_used < 1:
                    burst_used += 1  # next item dispatched immediately
                else:
                    sim_time  += delay
                    burst_used = 0

        except Exception as exc:
            import traceback
            self._log("error", f"[Snapshot] Erro: {exc}\n{traceback.format_exc()}")

        with self._lock:
            self._queue_snapshot = items

    # ── asyncio loop entry-point ───────────────────────────────────────────────

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._telethon_main())
        except Exception as exc:
            self._log("error", f"[BotRunner] Erro fatal no loop: {exc}")
            with self._lock:
                self._status_val = "error"

    # ── Telethon main coroutine ────────────────────────────────────────────────

    async def _telethon_main(self) -> None:
        self._stop_event = asyncio.Event()

        try:
            client = await self._build_client()
        except ValueError as exc:
            self._log("error", str(exc))
            with self._lock:
                self._status_val = "error"
            return

        self._client = client

        try:
            await client.connect()

            if not await client.is_user_authorized():
                ok = await self._authenticate()
                if not ok:
                    return

            with self._lock:
                self._status_val = "running"

            resolved = await self._resolve_sources()
            if not resolved:
                self._log("warning", "Nenhuma fonte válida encontrada para monitorar.")
                return

            await self._seed_cursors(resolved)
            self._log_config()

            self._delivery_queue       = asyncio.Queue()
            self._delivery_worker_task = asyncio.create_task(
                self._delivery_worker(), name="DeliveryWorker"
            )

            await self._polling_loop(resolved)

        except Exception as exc:
            self._log("error", f"[BotRunner] Exceção no cliente: {exc}")
            with self._lock:
                self._status_val = "error"
        finally:
            await self._shutdown()

    async def _build_client(self) -> TelegramClient:
        config   = self._config
        raw_id   = config.get("api_id")
        api_id   = int(raw_id) if raw_id and str(raw_id).strip() not in ("", "0") else 0
        api_hash = str(config.get("api_hash") or "").strip()

        if not api_id or not api_hash:
            raise ValueError("API_ID ou API_HASH inválidos ou ausentes na configuração.")

        session_string = config.get("session_string", "")
        try:
            session = StringSession(session_string) if session_string else StringSession()
        except Exception as exc:
            self._log("warning", f"⚠️ Session string inválida ({str(exc)[:50]}). Iniciando nova sessão.")
            session = StringSession()

        return TelegramClient(session, api_id, api_hash)

    async def _authenticate(self) -> bool:
        phone = self._config.get("phone", "")
        if not phone:
            self._log("error", "Número de telefone ausente para autenticação.")
            with self._lock:
                self._status_val = "error"
            return False

        with self._lock:
            self._status_val = "waiting_code"

        self._log("info", f"Sessão requer autorização. Solicitando código para {phone}...")
        try:
            self._phone_hash = await self._client.send_code_request(phone)
        except Exception as exc:
            self._log("error", f"Erro ao solicitar código: {exc}")
            with self._lock:
                self._status_val = "error"
            return False

        self._auth_event   = asyncio.Event()
        self._auth_success = False
        await self._auth_event.wait()

        if not self._auth_success:
            self._log("info", "Autenticação cancelada ou bot parado.")
            return False
        return True

    async def _resolve_sources(self) -> list:
        sources: list[str] = self._config.get("sources", [])
        self._log("info", f"Resolvendo {len(sources)} fontes: {sources}")
        resolved = []

        for src in sources:
            src = src.strip()
            if not src:
                continue
            try:
                entity = await self._resolve_single_source(src)
                name   = getattr(entity, "title", None) or getattr(entity, "username", None) or src
                resolved.append(entity)
                self._log("info", f"✅ Monitorando: {name} (ID: {entity.id})")
            except Exception as exc:
                self._log("warning", f"❌ Falha ao encontrar '{src}': {exc}")

        return resolved

    async def _resolve_single_source(self, src: str):
        handle = src.split("/")[-1] if "/" in src else src
        is_numeric = handle.lstrip("-").isdigit()

        if not is_numeric:
            try:
                res = await self._client(ResolveUsernameRequest(handle))
                if res.chats:
                    return res.chats[0]
                if res.users:
                    return res.users[0]
            except Exception as exc:
                self._log("warning", f"ResolveUsernameRequest falhou para '{handle}': {exc}")

        return await self._client.get_entity(handle)

    async def _seed_cursors(self, entities: list) -> None:
        """Mark existing messages as seen so only future messages are processed."""
        for entity in entities:
            try:
                msgs   = await self._client.get_messages(entity, limit=_SEED_MESSAGES_LIMIT)
                last_id = msgs[0].id if msgs else 0
                self._last_seen_by_chat[entity.id] = last_id
                self._log("info", f"[Polling] Cursor inicial {entity.id}: msg_id={last_id}")
            except Exception as exc:
                self._log("warning", f"[Polling] Falha ao iniciar cursor de {getattr(entity, 'id', '?')}: {exc}")

    def _log_config(self) -> None:
        now = time.time()
        if now - self._last_config_log_time < _CONFIG_LOG_INTERVAL_SECONDS:
            return
        wpp_enabled      = self._config.get("send_whatsapp", False)
        wpp_destinations = self._config.get("wpp_destinations", [])
        wpp_endpoint     = self._config.get("whatsapp_endpoint") or "http://localhost:4000/send"
        self._config.setdefault("whatsapp_endpoint", wpp_endpoint)
        self._log("info", f"⚙️ WhatsApp Config: ENABLED={wpp_enabled} | Canais={wpp_destinations} | Endpoint={wpp_endpoint}")
        self._last_config_log_time = now

    # ── Polling loop ──────────────────────────────────────────────────────────

    async def _polling_loop(self, entities: list) -> None:
        self._log("info", "🚀 Motor de busca (Polling) iniciado!")

        while not self._stop_event.is_set():
            try:
                for entity in entities:
                    if self._stop_event.is_set():
                        break
                    await self._poll_entity(entity)

                if not self._client.is_connected():
                    self._log("warning", "Conexão perdida. Tentando reconectar...")
                    await self._client.connect()
                    await asyncio.sleep(5)
                    continue

            except Exception as exc:
                self._log("error", f"[Polling] Erro no ciclo: {exc}")

            try:
                await asyncio.wait_for(
                    asyncio.shield(self._stop_event.wait()),
                    timeout=_POLL_INTERVAL_SECONDS,
                )
                break  # stop_event was set
            except asyncio.TimeoutError:
                pass   # normal: wait out the interval

    async def _poll_entity(self, entity) -> None:
        last_seen = self._last_seen_by_chat.get(entity.id, 0)

        try:
            msgs = await asyncio.wait_for(
                self._client.get_messages(entity, limit=_POLL_MESSAGES_LIMIT),
                timeout=_FETCH_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            self._log("warning", f"[Polling] Timeout em {getattr(entity, 'id', '?')}")
            return

        if not msgs:
            return

        new_msgs = [m for m in reversed(msgs) if m.id > last_seen]
        if not new_msgs:
            return

        self._log("info", f"[{entity.id}] +{len(new_msgs)} mensagens novas!")

        for message in new_msgs:
            if not self._remember_message(entity.id, message.id):
                continue

            with self._lock:
                self._last_seen_by_chat[entity.id] = max(
                    self._last_seen_by_chat.get(entity.id, 0), message.id
                )

            fingerprint = _compute_product_fingerprint(message)
            if not self._remember_product(fingerprint):
                self._log("info", f"[Dedup] Produto duplicado ignorado (msg {message.id}).")
                continue

            item = QueueItem(fingerprint=fingerprint, message=message)
            await self._delivery_queue.put(item)
            self._refresh_queue_snapshot()
            self._log("info", f"[RateLimit] Msg {message.id} enfileirada. Fila: {self._delivery_queue.qsize()} item(ns).")

    # ── Delivery worker ────────────────────────────────────────────────────────

    async def _delivery_worker(self) -> None:
        with self._lock:
            delay = self._delay
        self._log("info", f"[RateLimit] Fila de envio iniciada. Delay: {delay}s.")

        burst_count = 0

        while not self._stop_event.is_set():
            # ── Step 1: fetch next item (1 s timeout to stay responsive to stop) ──
            try:
                item: QueueItem = await asyncio.wait_for(
                    self._delivery_queue.get(), timeout=1
                )
            except asyncio.TimeoutError:
                continue

            with self._lock:
                self._active_delivery_item = item
            self._refresh_queue_snapshot()

            msg_id = getattr(item.message, "id", "?")

            try:
                # ── Step 2: honour cooldown ────────────────────────────────────
                await self._wait_for_cooldown(msg_id)
                if self._stop_event.is_set():
                    break

                # ── Step 3: process ───────────────────────────────────────────
                queue_size = self._delivery_queue.qsize()
                self._log("info", f"[RateLimit] Processando msg {msg_id}. Fila restante: {queue_size}.")

                processed, tg_ok, wp_ok, promo = await self._process_and_count(item.message)

                # ── Step 4: set next cooldown window ──────────────────────────
                actually_sent = tg_ok or wp_ok
                if actually_sent:
                    burst_count = self._schedule_next_dispatch(queue_size, burst_count)
                    dest = " e ".join(filter(None, ["Telegram" if tg_ok else "", "WhatsApp" if wp_ok else ""]))
                    remaining = max(0, int(self._next_dispatch_at - time.time()))
                    self._log("info", f"[RateLimit] \u2705 Msg {msg_id} enviada para {dest}! Pr\u00f3ximo envio em {remaining}s.")
                else:
                    label = "filtrada/sem destino" if processed else "ignorada (nao e promocao/link invalido)"
                    self._log("info", f"[RateLimit] \u23ED\uFE0F  Msg {msg_id} {label}. Pr\u00f3ximo item imediato.")

            except Exception as exc:
                self._log("error", f"[RateLimit] Erro ao processar msg {msg_id}: {exc}")
            finally:
                self._finish_product(item.fingerprint, remember=False)
                with self._lock:
                    self._active_delivery_item = None
                self._delivery_queue.task_done()
                self._refresh_queue_snapshot()

    async def _wait_for_cooldown(self, msg_id: object) -> None:
        """Sleep until self._next_dispatch_at, logging every 30 s."""
        while True:
            with self._lock:
                remaining = max(0.0, self._next_dispatch_at - time.time())
            if remaining <= 0:
                return
            self._log("info", f"[RateLimit] Msg {msg_id} em cooldown: aguardando {int(remaining)}s.")
            self._refresh_queue_snapshot()
            chunk = min(remaining, 30.0)
            try:
                await asyncio.wait_for(asyncio.shield(self._stop_event.wait()), timeout=chunk)
                return  # stop requested
            except asyncio.TimeoutError:
                pass

    def _schedule_next_dispatch(self, queue_size: int, burst_count: int) -> int:
        """Update next_dispatch_at; return updated burst_count."""
        with self._lock:
            delay = self._delay if self._delay > 0 else 300
            if queue_size >= 3 and burst_count < 1:
                self._next_dispatch_at = time.time()
                return burst_count + 1
            else:
                jitter = random.randint(2, max(2, delay))
                self._next_dispatch_at = time.time() + jitter
                return 0

    # ── Message processing ────────────────────────────────────────────────────

    async def _process_and_count(self, message) -> tuple[bool, bool, bool, Optional[dict]]:
        try:
            processed, tg_ok, wp_ok, promo = await processar_mensagem(
                message, self._config, self._client, self._log
            )
            with self._lock:
                self._stats.reset_if_new_day()
                if processed:
                    self._stats.processed += 1
                    if tg_ok:
                        self._stats.telegram += 1
                    if wp_ok:
                        self._stats.whatsapp += 1
                    if self._activity and (tg_ok or wp_ok):
                        self._emit_activity(tg_ok, wp_ok, promo)
                else:
                    self._stats.errors += 1
            return processed, tg_ok, wp_ok, promo

        except Exception as exc:
            self._log("error", f"[BotRunner] Erro ao processar mensagem: {exc}")
            with self._lock:
                self._stats.errors += 1
            return False, False, False, None

    def _emit_activity(self, tg_ok: bool, wp_ok: bool, promo: Optional[dict]) -> None:
        """Emit an activity event (must be called under self._lock)."""
        dest = " e ".join(filter(None, ["Telegram" if tg_ok else "", "WhatsApp" if wp_ok else ""]))
        total = self._stats.processed

        title = "Produto"
        price = "N/A"
        store = ""

        if promo:
            raw_title = promo.get("seoTitle") or promo.get("originalTitle") or "Produto"
            title = raw_title.strip()[:57] + ("..." if len(raw_title) > 60 else "")
            if promo.get("newPrice"):
                price = f"R$ {promo['newPrice']}"
            elif promo.get("oldPrice"):
                price = f"R$ {promo['oldPrice']}"
            if promo.get("store"):
                store = f" [{promo['store']}]"

        delay = self._delay if self._delay > 0 else 3
        next_ts = datetime.fromtimestamp(time.time() + delay, tz=_TZ_BR).strftime("%H:%M:%S")

        self._activity(
            "success",
            f"\U0001F4E6 {title}{store} | Valor: {price}\n"
            f"\u2705 Enviado para {dest}! Total hoje: {total}.\n"
            f"\u23F1\uFE0F Pr\u00f3ximo envio liberado a partir das {next_ts}.",
        )

    # ── Shutdown ──────────────────────────────────────────────────────────────

    async def _shutdown(self) -> None:
        if self._delivery_worker_task:
            self._delivery_worker_task.cancel()
            try:
                await self._delivery_worker_task
            except asyncio.CancelledError:
                pass

        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass

        with self._lock:
            if self._status_val != "error":
                self._status_val = "stopped"

        self._log("info", "Bot encerrado.")