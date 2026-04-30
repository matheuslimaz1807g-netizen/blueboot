"""
bot_runner.py — Thread-safe Telethon lifecycle manager.

Runs the asyncio event loop in a dedicated daemon thread so it doesn't
block the Flask web server running in the main thread.

Usa polling (get_messages a cada 10s) no lugar de eventos NewMessage,
pois o Telegram nem sempre entrega eventos para canais onde a conta
é apenas assinante — polling é mais confiável nesse cenário.
"""
from __future__ import annotations

import asyncio
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Optional

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from pipeline import processar_mensagem

_RECONNECT_INTERVAL = 15
_RECONNECT_MAX_ATTEMPTS = 10
_POLL_INTERVAL = 10  # segundos entre cada checagem


class BotRunner:
    """
    Controls the full lifecycle of the Telethon client.

    Thread-safety contract:
    - All asyncio calls happen inside self._loop (dedicated thread).
    - Flask routes interact via self._stats, self._status
      which are protected by self._lock.
    """

    def __init__(self, log_callback: Callable[[str, str], None]) -> None:
        self._log = log_callback
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[TelegramClient] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._status_val: str = "stopped"

        self._stats: dict = {
            "today_processed": 0,
            "today_telegram": 0,
            "today_whatsapp": 0,
            "errors_24h": 0,
            "day": datetime.now(timezone.utc).date(),
        }
        self._config: dict = {}
        self._delay: int = 3
        # Guarda o último msg_id visto por canal para o polling
        self._last_seen_by_chat: dict[int, int] = {}
        # Deduplicação extra por (chat_id, msg_id)
        self._seen_messages: set[tuple[int, int]] = set()
        self._seen_message_order: deque[tuple[int, int]] = deque()
        self._seen_message_limit: int = 5000

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, config: dict) -> None:
        """
        # FUTURE: multi-tenant: accept tenant_id in config to isolate sessions.
        Ex: self._tenant_id = config.get("tenant_id", "default")
        """
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
        with self._lock:
            self._config = config
            self._delay = int(config.get("delay_segundos", 3))

    def _remember_message(self, chat_id: int, msg_id: int) -> bool:
        """Retorna False se a mensagem já foi vista."""
        key = (chat_id, msg_id)
        with self._lock:
            if key in self._seen_messages:
                return False
            if len(self._seen_message_order) >= self._seen_message_limit:
                old = self._seen_message_order.popleft()
                self._seen_messages.discard(old)
            self._seen_message_order.append(key)
            self._seen_messages.add(key)
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

        from telethon.sessions import StringSession
        session_string = config.get("session_string", "")
        session = StringSession(session_string) if session_string else StringSession()

        self._client = TelegramClient(session, api_id, api_hash)

        try:
            await self._client.connect()

            # ── Autenticação ──────────────────────────────────────────────────
            if not await self._client.is_user_authorized():
                if not phone:
                    self._log("error", "Número de telefone ausente para autenticação.")
                    with self._lock:
                        self._status_val = "error"
                    return

                with self._lock:
                    self._status_val = "waiting_code"

                self._log("info", f"Sessão requer autorização. Solicitando código para {phone}...")
                try:
                    self._phone_hash = await self._client.send_code_request(phone)
                except Exception as exc:
                    self._log("error", f"Erro ao solicitar código: {exc}")
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

            # ── Resolver fontes ───────────────────────────────────────────────
            self._log("info", f"Resolvendo {len(sources)} fontes: {sources}")
            resolved_chats = []
            for src in sources:
                src_clean = src.strip()
                if not src_clean:
                    continue
                try:
                    entity_input = src_clean.split('/')[-1] if '/' in src_clean else src_clean
                    entity = await self._client.get_entity(entity_input)
                    entity_name = getattr(entity, "title", None) or getattr(entity, "username", None) or src_clean
                    resolved_chats.append(entity)
                    self._log("info", f"✅ Monitorando: {entity_name} (ID: {entity.id})")
                except Exception as e:
                    self._log("warning", f"❌ Falha ao encontrar '{src_clean}': {e}")

            if not resolved_chats:
                self._log("warning", "Nenhuma fonte válida encontrada para monitorar.")
                return
            else:
                self._log("success", f"Bot conectado e monitorando {len(resolved_chats)} fontes via polling.")

            # ── Seed: marca as mensagens atuais como já vistas ────────────────
            # Assim só processa mensagens NOVAS após o bot iniciar
            for entity in resolved_chats:
                try:
                    msgs = await self._client.get_messages(entity, limit=5)
                    last_id = msgs[0].id if msgs else 0
                    self._last_seen_by_chat[entity.id] = last_id
                    self._log("info", f"[Polling] Cursor inicial {entity.id}: msg_id={last_id}")
                except Exception as exc:
                    self._log("warning", f"[Polling] Falha ao iniciar cursor de {getattr(entity, 'id', '?')}: {exc}")

            # ── Processar mensagem e atualizar stats ──────────────────────────
            async def process_message_and_update_stats(message) -> None:
                try:
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
                except Exception as exc:
                    self._log("error", f"[BotRunner] Erro ao processar mensagem: {exc}")
                    with self._lock:
                        self._stats["errors_24h"] += 1

            # ── Loop de polling ───────────────────────────────────────────────
            # Igual ao código simples que funcionava — get_messages a cada 10s,
            # processa em background com create_task para não perder mensagens
            # enquanto o Selenium está rodando.
            async def polling_loop() -> None:
                last_heartbeat = time.time()
                while not self._stop_event.is_set():
                    await asyncio.sleep(_POLL_INTERVAL)

                    # Heartbeat a cada 60 segundos
                    if time.time() - last_heartbeat > 60:
                        self._log("info", f"Bot ativo. Monitorando {len(resolved_chats)} fontes via polling...")
                        last_heartbeat = time.time()

                    for entity in resolved_chats:
                        if self._stop_event.is_set():
                            break
                        try:
                            last_seen = self._last_seen_by_chat.get(entity.id, 0)
                            msgs = await self._client.get_messages(entity, limit=10)

                            # Filtra só mensagens novas, em ordem cronológica
                            new_msgs = [
                                m for m in reversed(msgs)
                                if m.id > last_seen
                            ]

                            for message in new_msgs:
                                msg_id = message.id

                                # Deduplicação extra
                                if not self._remember_message(entity.id, msg_id):
                                    continue

                                self._log("info", f"[{entity.id}/{msg_id}] Nova mensagem capturada via polling.")

                                # Atualiza watermark imediatamente
                                with self._lock:
                                    self._last_seen_by_chat[entity.id] = max(
                                        self._last_seen_by_chat.get(entity.id, 0), msg_id
                                    )

                                # Processa em background — não bloqueia o polling
                                asyncio.create_task(process_message_and_update_stats(message))

                        except Exception as exc:
                            entity_name = getattr(entity, "title", None) or getattr(entity, "id", "?")
                            self._log("warning", f"[Polling] Falha ao consultar {entity_name}: {exc}")

            # ── Reconector automático ─────────────────────────────────────────
            async def reconnect_watchdog() -> None:
                attempts = 0
                while not self._stop_event.is_set():
                    await asyncio.sleep(30)
                    if self._stop_event.is_set():
                        break

                    if not self._client.is_connected():
                        attempts += 1
                        if attempts > _RECONNECT_MAX_ATTEMPTS:
                            self._log("error", "[Watchdog] Máximo de tentativas atingido. Encerrando.")
                            with self._lock:
                                self._status_val = "error"
                            self._stop_event.set()
                            break

                        with self._lock:
                            self._status_val = "reconnecting"

                        self._log("warning", f"[Watchdog] Conexão perdida. Tentativa {attempts}/{_RECONNECT_MAX_ATTEMPTS} em {_RECONNECT_INTERVAL}s...")
                        await asyncio.sleep(_RECONNECT_INTERVAL)

                        try:
                            await self._client.connect()
                            if await self._client.is_user_authorized():
                                with self._lock:
                                    self._status_val = "running"
                                attempts = 0
                                self._log("success", "[Watchdog] Reconectado com sucesso.")
                            else:
                                self._log("error", "[Watchdog] Reconectado mas sessão expirou.")
                                with self._lock:
                                    self._status_val = "error"
                                self._stop_event.set()
                        except Exception as exc:
                            self._log("warning", f"[Watchdog] Falha ao reconectar: {exc}")
                    else:
                        attempts = 0

            polling_task = asyncio.create_task(polling_loop())
            watchdog_task = asyncio.create_task(reconnect_watchdog())

            await self._stop_event.wait()

            polling_task.cancel()
            watchdog_task.cancel()
            await asyncio.gather(polling_task, watchdog_task, return_exceptions=True)

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
                if self._status_val not in ("error",):
                    self._status_val = "stopped"
            self._log("info", "Bot encerrado.")

    def _reset_day_if_needed(self) -> None:
        today = datetime.now(timezone.utc).date()
        if self._stats["day"] != today:
            self._stats.update({
                "today_processed": 0,
                "today_telegram": 0,
                "today_whatsapp": 0,
                "errors_24h": 0,
                "day": today,
            })