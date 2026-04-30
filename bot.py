"""
bot_runner.py — Thread-safe Telethon lifecycle manager.

Runs the asyncio event loop in a dedicated daemon thread so it doesn't
block the Flask web server running in the main thread.
"""
from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Optional

from telethon import TelegramClient, events, utils
from telethon.errors import SessionPasswordNeededError

from pipeline import processar_mensagem

# These values are provided by the Telegram API — NOT the bot token.
# They are fetched from the remote config at startup.
_DEFAULT_API_ID = 0
_DEFAULT_API_HASH = ""


class BotRunner:
    """
    Controls the full lifecycle of the Telethon client.

    Thread-safety contract:
    - All asyncio calls happen inside self._loop (dedicated thread).
    - Flask routes interact via self._running, self._stats, self._status
      which are protected by self._lock.
    """

    def __init__(self, log_callback: Callable[[str, str], None]) -> None:
        self._log = log_callback
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[TelegramClient] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._status_val: str = "stopped"  # "running" | "stopped" | "error"

        self._stats: dict = {
            "today_processed": 0,
            "today_telegram": 0,
            "today_whatsapp": 0,
            "errors_24h": 0,
            "day": datetime.now(timezone.utc).date(),
        }
        self._config: dict = {}
        # Delay applied between consecutive messages (seconds)
        self._delay: int = 3
        self._debug_unmatched_events_logged: int = 0
        self._last_seen_by_chat: dict[int, int] = {}
        self._seen_messages: set[tuple[int, int]] = set()
        self._seen_message_order: deque[tuple[int, int]] = deque()
        self._seen_message_limit: int = 5000

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, config: dict) -> None:
        with self._lock:
            if self._status_val == "running":
                return
            self._config = config
            self._delay = int(config.get("delay_segundos", 3))

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="TelethonLoop",
        )
        self._thread.start()

    def stop(self) -> None:
        loop = self._loop
        stop_evt = self._stop_event
        stop_evt = self._stop_event
        auth_evt = getattr(self, "_auth_event", None)
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
        """Submit the OTP code to Telethon via run_coroutine_threadsafe"""
        if not self._loop or not self._client:
            return {"ok": False, "error": "Bot não está rodando."}

        async def _do_auth():
            try:
                if password:
                    await self._client.sign_in(password=password)
                else:
                    await self._client.sign_in(self._config.get("phone", ""), code)
                
                session_str = self._client.session.save()
                self._auth_success = True
                if hasattr(self, "_auth_event"):
                    self._auth_event.set()
                return {"ok": True, "session_string": session_str}
            except SessionPasswordNeededError:
                return {"ok": False, "requires_password": True}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        future = asyncio.run_coroutine_threadsafe(_do_auth(), self._loop)
        try:
            return future.result(timeout=30)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def status(self) -> str:
        with self._lock:
            return self._status_val

    def get_stats(self) -> dict:
        with self._lock:
            self._reset_day_if_needed()
            return dict(self._stats)

    def update_config(self, config: dict) -> None:
        """Hot-reload config without restarting the client."""
        with self._lock:
            self._config = config
            self._delay = int(config.get("delay_segundos", 3))

    def _remember_message(self, chat_id: int | None, msg_id: int | None) -> bool:
        """Return False when a message was already seen by event or polling."""
        if chat_id is None or msg_id is None:
            return True

        key = (int(chat_id), int(msg_id))
        with self._lock:
            if key in self._seen_messages:
                return False

            if len(self._seen_message_order) >= self._seen_message_limit:
                old_key = self._seen_message_order.popleft()
                self._seen_messages.discard(old_key)

            self._seen_message_order.append(key)
            self._seen_messages.add(key)

            prev_last = self._last_seen_by_chat.get(int(chat_id), 0)
            if int(msg_id) > prev_last:
                self._last_seen_by_chat[int(chat_id)] = int(msg_id)
        return True

    # ── Internal asyncio loop ─────────────────────────────────────────────────

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._telethon_main())
        except Exception as exc:
            self._log("error", f"[BotRunner] Erro fatal no loop: {exc}")
            with self._lock:
                self._status_val = "error"

    async def _telethon_main(self) -> None:
        config = self._config
        self._stop_event = asyncio.Event()

        # Robust validation before init
        _raw_api = config.get("api_id")
        api_id = int(_raw_api) if _raw_api and str(_raw_api).strip() not in ("", "0") else 0
        api_hash = str(config.get("api_hash") or "").strip()

        if not api_id or not api_hash:
            self._log("error", "API_ID ou API_HASH inválidos ou ausentes na configuração.")
            with self._lock:
                self._status_val = "error"
            return

        phone = config.get("phone", "")
        sources: list[str] = config.get("sources", [])

        # Use in-memory session (StringSession) so no .session file is written
        from telethon.sessions import StringSession
        session_string = config.get("session_string", "")
        session = StringSession(session_string) if session_string else StringSession()

        self._client = TelegramClient(session, api_id, api_hash)

        try:
            await self._client.connect()

            if not await self._client.is_user_authorized():
                if not phone:
                    self._log("error", "Número de telefone ausente para autenticação.")
                    with self._lock:
                        self._status_val = "error"
                    return

                with self._lock:
                    self._status_val = "waiting_code"
                
                self._log("info", f"Sessão Telegram requer autorização. Solicitando código via app Telegram para {phone}...")
                try:
                    self._phone_hash = await self._client.send_code_request(phone)
                except Exception as exc:
                    self._log("error", f"Erro ao solicitar código do Telegram: {exc}")
                    with self._lock:
                        self._status_val = "error"
                    return

                self._auth_event = asyncio.Event()
                self._auth_success = False
                await self._auth_event.wait()

                if not self._auth_success:
                    self._log("info", "Autenticação cancelada ou bot parado.")
                    return

            with self._lock:
                self._status_val = "running"

            # Resolve sources to entities for more reliable filtering across
            # usernames, channels and groups.
            self._log("info", f"Iniciando resolução de {len(sources)} fontes: {sources}")
            resolved_chats = []
            resolved_ids = []
            resolved_peer_ids = set()
            self._debug_unmatched_events_logged = 0
            for src in sources:
                src_clean = src.strip()
                if not src_clean: continue
                try:
                    # Remove trailing slashes and common prefixes to help resolution
                    entity_input = src_clean.split('/')[-1] if '/' in src_clean else src_clean
                    entity = await self._client.get_entity(entity_input)
                    peer_id = utils.get_peer_id(entity)
                    resolved_chats.append(entity)
                    resolved_ids.append(entity.id)
                    resolved_peer_ids.add(peer_id)
                    entity_name = getattr(entity, "title", None) or getattr(entity, "username", None) or src_clean
                    self._log("info", f"✅ Monitorando: {entity_name} (ID: {entity.id}, peer_id: {peer_id})")
                except Exception as e:
                    self._log("warning", f"❌ Falha ao encontrar '{src_clean}': {e}")

            if not resolved_chats:
                self._log("warning", "Nenhuma fonte válida encontrada para monitorar.")
            else:
                self._log("success", f"Bot conectado e monitorando {len(resolved_chats)} fontes com sucesso.")

            # Seed polling watermark so only messages posted after startup are processed.
            for entity in resolved_chats:
                try:
                    peer_id = utils.get_peer_id(entity)
                    latest_messages = await self._client.get_messages(entity, limit=5)
                    latest_id = latest_messages[0].id if latest_messages else 0
                    self._last_seen_by_chat[peer_id] = latest_id
                    
                    # Lembrar das últimas mensagens também para evitar duplicação em caso de reordenamento
                    for msg in latest_messages:
                        msg_chat_id = getattr(msg, "chat_id", None) or peer_id
                        self._remember_message(msg_chat_id, getattr(msg, "id", None))
                        
                    self._log("info", f"[Polling] Ultima mensagem conhecida para {peer_id}: {latest_id}")
                except Exception as exc:
                    self._log("warning", f"[Polling] Falha ao iniciar cursor da fonte {getattr(entity, 'id', '?')}: {exc}")


            async def process_message_and_update_stats(message) -> None:
                processed, tg_ok, wp_ok = await processar_mensagem(
                    message,
                    self._config,
                    self._client,
                    self._log,
                )
                with self._lock:
                    self._reset_day_if_needed()
                    if processed:
                        self._stats["today_processed"] += 1
                        if tg_ok:
                            self._stats["today_telegram"] += 1
                        if wp_ok:
                            self._stats["today_whatsapp"] += 1
                    else:
                        self._stats["errors_24h"] += 1

            async def poll_sources_loop() -> None:
                if not resolved_chats:
                    return

                self._log("info", f"[Polling] Fallback ativo a cada 10s para {len(resolved_chats)} fontes.")
                while not self._stop_event.is_set():
                    await asyncio.sleep(10)
                    for entity in resolved_chats:
                        if self._stop_event.is_set():
                            break
                        try:
                            peer_id = utils.get_peer_id(entity)
                            last_seen = self._last_seen_by_chat.get(peer_id, 0)
                            messages = await self._client.get_messages(entity, limit=5)
                            new_messages = [
                                msg for msg in reversed(messages)
                                if getattr(msg, "id", 0) > last_seen
                            ]

                            for message in new_messages:
                                msg_id = getattr(message, "id", None)
                                message_chat_id = getattr(message, "chat_id", None) or peer_id
                                if not self._remember_message(message_chat_id, msg_id):
                                    continue
                                self._log("info", f"[{message_chat_id}/{msg_id}] Evento capturado via polling.")
                                await process_message_and_update_stats(message)
                                await asyncio.sleep(self._delay)

                            # FIX: Atualiza o watermark após processar o lote,
                            # impedindo que o polling re-processe as mesmas mensagens
                            if new_messages:
                                max_id = max(getattr(m, "id", 0) for m in new_messages)
                                with self._lock:
                                    self._last_seen_by_chat[peer_id] = max(
                                        self._last_seen_by_chat.get(peer_id, 0), max_id
                                    )

                        except Exception as exc:
                            entity_name = getattr(entity, "title", None) or getattr(entity, "username", None) or getattr(entity, "id", "?")
                            self._log("warning", f"[Polling] Falha ao consultar {entity_name}: {exc}")

            polling_task = asyncio.create_task(poll_sources_loop())

            # Register handler for each resolved source channel/group
            @self._client.on(events.NewMessage(chats=resolved_chats))
            async def handler(event):
                chat_id = getattr(event, "chat_id", "?")
                msg_id = getattr(event.message, "id", "?")
                if not self._remember_message(chat_id, msg_id):
                    return
                # FIX: Atualiza o watermark imediatamente ao receber via evento,
                # impedindo que o polling pegue a mesma mensagem depois
                with self._lock:
                    self._last_seen_by_chat[chat_id] = max(
                        self._last_seen_by_chat.get(chat_id, 0), msg_id
                    )
                self._log("info", f"[{chat_id}/{msg_id}] Evento recebido do Telegram.")
                await process_message_and_update_stats(event.message)
                await asyncio.sleep(self._delay)

            @self._client.on(events.NewMessage)
            async def debug_handler(event):
                if self._debug_unmatched_events_logged >= 20:
                    return

                chat_id = getattr(event, "chat_id", None)
                if chat_id in resolved_peer_ids or chat_id in resolved_ids:
                    return

                self._debug_unmatched_events_logged += 1
                try:
                    chat = await event.get_chat()
                    chat_name = getattr(chat, "title", None) or getattr(chat, "username", None) or str(chat_id)
                except Exception:
                    chat_name = str(chat_id)

                self._log("info", f"[DEBUG] Evento fora do filtro: {chat_name} (chat_id: {chat_id})")

            await self._stop_event.wait()
            polling_task.cancel()
            await asyncio.gather(polling_task, return_exceptions=True)

        except Exception as exc:
            self._log("error", f"[BotRunner] Exceção no cliente: {exc}")
            with self._lock:
                self._status_val = "error"
        finally:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            with self._lock:
                if self._status_val == "running":
                    self._status_val = "stopped"
            self._log("info", "Bot encerrado.")

    def _reset_day_if_needed(self) -> None:
        """Reset daily counters (called with _lock held)."""
        today = datetime.now(timezone.utc).date()
        if self._stats["day"] != today:
            self._stats.update({
                "today_processed": 0,
                "today_telegram": 0,
                "today_whatsapp": 0,
                "errors_24h": 0,
                "day": today,
            })