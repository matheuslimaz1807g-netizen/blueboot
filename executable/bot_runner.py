"""
bot_runner.py â€” Thread-safe Telethon lifecycle manager.

Runs the asyncio event loop in a dedicated daemon thread so it doesn't
block the Flask web server running in the main thread.

Usa polling (get_messages a cada 10s) no lugar de eventos NewMessage,
pois o Telegram nem sempre entrega eventos para canais onde a conta
Ã© apenas assinante â€” polling Ã© mais confiÃ¡vel nesse cenÃ¡rio.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import threading
import time
import unicodedata
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from pipeline import processar_mensagem

_RECONNECT_INTERVAL = 15
_RECONNECT_MAX_ATTEMPTS = 10
_POLL_INTERVAL = 10  # segundos entre cada checagem
_DELIVERY_INTERVAL_SECONDS = 10 * 60  # 10 minutos entre envios reais
_PRODUCT_DEDUP_TTL_SECONDS = 24 * 60 * 60
_PRODUCT_DEDUP_LIMIT = 2000
_URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)
_PRICE_PATTERN = re.compile(r"r\$\s*([\d.,]+)", re.I)


class BotRunner:
    """
    Controls the full lifecycle of the Telethon client.

    Thread-safety contract:
    - All asyncio calls happen inside self._loop (dedicated thread).
    - Flask routes interact via self._stats, self._status
      which are protected by self._lock.
    """

    def __init__(
        self,
        log_callback: Callable[[str, str], None],
        activity_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._log = log_callback
        self._activity = activity_callback
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
        # Guarda o Ãºltimo msg_id visto por canal para o polling
        self._last_seen_by_chat: dict[int, int] = {}
        # DeduplicaÃ§Ã£o extra por (chat_id, msg_id)
        self._seen_messages: set[tuple[int, int]] = set()
        self._seen_message_order: deque[tuple[int, int]] = deque()
        self._seen_message_limit: int = 5000
        self._delivery_queue: Optional[asyncio.Queue] = None
        self._delivery_worker_task: Optional[asyncio.Task] = None
        self._next_dispatch_at: float = 0.0
        self._active_delivery_item: Optional[tuple] = None
        self._queue_snapshot: list[dict] = []  # Thread-safe snapshot for heartbeat
        self._pending_product_fingerprints: set[str] = set()
        self._recent_product_fingerprints: dict[str, float] = {}
        self._recent_product_order: deque[tuple[str, float]] = deque()

    # â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            return {"ok": False, "error": "Bot nÃ£o estÃ¡ rodando."}

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
            stats = dict(self._stats)
            queue_size = self._delivery_queue.qsize() if self._delivery_queue else 0
            stats["delivery_queue_size"] = queue_size
            stats["next_dispatch_seconds"] = max(0, int(self._next_dispatch_at - time.time()))
            return stats

    def get_queue_items(self) -> list[dict]:
        """Retorna snapshot thread-safe dos itens na fila com ETAs estimados.

        O snapshot Ã© mantido pelo _delivery_worker e atualizado sob _lock
        sempre que o estado da fila muda. Isso evita acesso cross-thread
        ao asyncio.Queue._queue (que nÃ£o Ã© thread-safe).
        """
        with self._lock:
            return list(self._queue_snapshot)

    def _refresh_queue_snapshot(self) -> None:
        """Recalcula o snapshot da fila. DEVE ser chamado de dentro do asyncio loop."""
        items: list[dict] = []
        try:
            active_item = self._active_delivery_item

            full_list: list[tuple] = []
            if active_item:
                full_list.append(active_item)

            if self._delivery_queue:
                full_list.extend(list(self._delivery_queue._queue))

            delay = self._delay if self._delay > 0 else 300
            current_next = self._next_dispatch_at
            now = time.time()
            if current_next < now:
                current_next = now

            # SimulaÃ§Ã£o exata da lÃ³gica do _delivery_worker para cÃ¡lculo de ETA
            current_time_sim = current_next
            burst_sim = 0  # Simula burst_count no worker

            for idx, item in enumerate(full_list):
                if not (isinstance(item, tuple) and len(item) == 2):
                    continue
                _fingerprint, msg = item

                text = ""
                if hasattr(msg, "raw_text") and msg.raw_text:
                    text = msg.raw_text
                elif hasattr(msg, "message") and msg.message:
                    text = msg.message

                preview_text = ""
                price = ""
                store = ""

                if text:
                    # 1. Detectar preÃ§o (R$ XX,XX)
                    price_match = re.search(r'R\$\s*([\d.,]+)', text)
                    if price_match:
                        price = f"R$ {price_match.group(1).strip()}"

                    # 2. Detectar loja
                    text_lower = text.lower()
                    if "mercadolivre" in text_lower or "meli.la" in text_lower:
                        store = "Mercado Livre"
                    elif "aliexpress" in text_lower or "a.aliexpress" in text_lower:
                        store = "AliExpress"
                    elif "shopee" in text_lower:
                        store = "Shopee"

                    # 3. HeurÃ­stica inteligente para extrair o tÃ­tulo do produto real
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    avoid_terms = ["compre", "link", "aqui", "grupo", "oferta", "desconto", "cupom", "off", "site", "clique", "ðŸ‘‰", "ðŸ›’", "ativo", "liberado", "enviado", "valor"]
                    
                    best_title = ""
                    for line in lines:
                        line_lower = line.lower()
                        # Pula linhas com links
                        if "http" in line_lower:
                            continue
                        # Pula hashtags
                        if line.startswith("#"):
                            continue
                        # Pula linhas que contenham termos genÃ©ricos de cupom/aÃ§Ãµes comerciais
                        if any(term in line_lower for term in avoid_terms):
                            continue
                        # Pula linhas muito curtas que nÃ£o representam um tÃ­tulo de produto
                        if len(line) < 5:
                            continue
                        
                        # Se passou em todas as regras, esta linha Ã© o tÃ­tulo do produto!
                        best_title = line
                        break

                    # Fallbacks caso a heurÃ­stica seja muito estrita
                    if not best_title:
                        if len(lines) > 1:
                            best_title = lines[1] if not lines[1].startswith("#") else lines[0]
                        elif lines:
                            best_title = lines[0]
                        else:
                            best_title = "Mensagem sem texto"

                    # Remove hashtags do tÃ­tulo do produto
                    best_title = re.sub(r'#\w+', '', best_title).strip()
                    
                    # 4. Montar previsualizaÃ§Ã£o premium elegante (TÃ­tulo | PreÃ§o | Loja)
                    parts = [best_title]
                    if price:
                        parts.append(price)
                    if store:
                        parts.append(store)
                    
                    preview_text = " | ".join(parts)
                else:
                    preview_text = "Mensagem sem texto"

                # Limita tamanho para layout elegante
                preview = (preview_text[:65] + "...") if len(preview_text) > 65 else preview_text

                # O ETA deste item Ã© o tempo simulado atual
                eta = current_time_sim

                # Determina o tempo para o PRÃ“XIMO item, simulando o que o worker decidirÃ¡ ao concluir este item
                queue_remaining_after_this = len(full_list) - (idx + 1)
                
                # Se apÃ³s enviar este item, ainda restarem >= 3 itens na fila, e nÃ£o tivermos usado o burst:
                if queue_remaining_after_this >= 3 and burst_sim < 1:
                    # Burst ativado para o prÃ³ximo item (sem delay adicional)
                    burst_sim += 1
                else:
                    # Cooldown normal para o prÃ³ximo item
                    current_time_sim += delay
                    burst_sim = 0

                tz_br = timezone(timedelta(hours=-3))
                eta_str = datetime.fromtimestamp(eta, tz=tz_br).strftime("%H:%M:%S")

                items.append({"preview": preview, "eta": eta_str})
        except Exception as exc:
            import traceback
            print(f"[_refresh_queue_snapshot] Erro: {exc}\n{traceback.format_exc()}", flush=True)

        with self._lock:
            self._queue_snapshot = items

    def update_config(self, config: dict) -> None:
        with self._lock:
            self._config = config
            self._delay = int(config.get("delay_segundos", 300))

    def _remember_message(self, chat_id: int, msg_id: int) -> bool:
        """Retorna False se a mensagem jÃ¡ foi vista."""
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

    def _product_fingerprint(self, message) -> str:
        raw_text = getattr(message, "raw_text", "") or ""
        normalized = unicodedata.normalize("NFKD", raw_text)
        normalized = normalized.encode("ascii", "ignore").decode("ascii").lower()

        urls = []
        for match in _URL_PATTERN.findall(normalized):
            url = match.strip().strip("`'\"()[]{}<>.,;!").split("#", 1)[0].split("?", 1)[0]
            url = re.sub(r"^https?://", "", url).rstrip("/")
            if url:
                urls.append(url)

        text_without_urls = _URL_PATTERN.sub(" ", normalized)
        lines = [
            line.strip()
            for line in text_without_urls.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if len(lines) > 1:
            lines = lines[1:]

        title = ""
        for line in lines:
            cleaned = re.sub(r"[^a-z0-9]+", " ", line)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if len(cleaned) >= 8:
                title = cleaned[:140]
                break

        prices = [
            re.sub(r"\D", "", price)
            for price in _PRICE_PATTERN.findall(normalized)
            if re.sub(r"\D", "", price)
        ]

        parts = []
        if title:
            parts.append(f"title:{title}")
        if prices:
            parts.append(f"price:{prices[-1]}")
        if urls:
            parts.append(f"url:{urls[0]}")

        if not parts:
            chat_id = getattr(getattr(message, "chat", None), "id", "")
            msg_id = getattr(message, "id", "")
            parts.append(f"message:{chat_id}:{msg_id}")

        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _prune_product_fingerprints_locked(self, now: float) -> None:
        while self._recent_product_order:
            fingerprint, created_at = self._recent_product_order[0]
            is_expired = now - created_at > _PRODUCT_DEDUP_TTL_SECONDS
            is_over_limit = len(self._recent_product_order) > _PRODUCT_DEDUP_LIMIT
            if not is_expired and not is_over_limit:
                break
            self._recent_product_order.popleft()
            if self._recent_product_fingerprints.get(fingerprint) == created_at:
                self._recent_product_fingerprints.pop(fingerprint, None)

    def _remember_product(self, fingerprint: str) -> bool:
        now = time.time()
        with self._lock:
            self._prune_product_fingerprints_locked(now)
            if fingerprint in self._pending_product_fingerprints:
                return False
            if fingerprint in self._recent_product_fingerprints:
                return False
            self._pending_product_fingerprints.add(fingerprint)
        return True

    def _finish_product(self, fingerprint: str, remember_recent: bool) -> None:
        now = time.time()
        with self._lock:
            self._pending_product_fingerprints.discard(fingerprint)
            if remember_recent:
                self._recent_product_fingerprints[fingerprint] = now
                self._recent_product_order.append((fingerprint, now))
            self._prune_product_fingerprints_locked(now)

    # â”€â”€ Internal asyncio loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            self._log("error", "API_ID ou API_HASH invÃ¡lidos ou ausentes na configuraÃ§Ã£o.")
            with self._lock:
                self._status_val = "error"
            return

        phone = config.get("phone", "")
        sources: list[str] = config.get("sources", [])

        from telethon.sessions import StringSession
        session_string = config.get("session_string", "")
        session = StringSession()
        if session_string:
            try:
                session = StringSession(session_string)
            except Exception as e:
                self._log("warning", f"âš ï¸ Session string invÃ¡lida ou corrompida ({str(e)[:50]}...). Iniciando nova sessÃ£o.")
                session = StringSession()

        self._client = TelegramClient(session, api_id, api_hash)

        try:
            await self._client.connect()

            # â”€â”€ AutenticaÃ§Ã£o â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if not await self._client.is_user_authorized():
                if not phone:
                    self._log("error", "NÃºmero de telefone ausente para autenticaÃ§Ã£o.")
                    with self._lock:
                        self._status_val = "error"
                    return

                with self._lock:
                    self._status_val = "waiting_code"

                self._log("info", f"SessÃ£o requer autorizaÃ§Ã£o. Solicitando cÃ³digo para {phone}...")
                try:
                    self._phone_hash = await self._client.send_code_request(phone)
                except Exception as exc:
                    self._log("error", f"Erro ao solicitar cÃ³digo: {exc}")
                    with self._lock:
                        self._status_val = "error"
                    return

                self._auth_event = asyncio.Event()
                self._auth_success = False
                await self._auth_event.wait()

                if not self._auth_success:
                    self._log("info", "AutenticaÃ§Ã£o cancelada ou bot parado.")
                    return

            with self._lock:
                self._status_val = "running"

            # â”€â”€ Resolver fontes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            self._log("info", f"Resolvendo {len(sources)} fontes: {sources}")
            resolved_chats = []
            for src in sources:
                src_clean = src.strip()
                if not src_clean:
                    continue
                try:
                    entity_input = src_clean.split('/')[-1] if '/' in src_clean else src_clean
                    
                    entity = None
                    # Se nÃ£o for numÃ©rico (com ou sem sinal de menos), tentamos forÃ§ar a resoluÃ§Ã£o via API para atualizar o cache
                    is_numeric = entity_input.isdigit() or (entity_input.startswith('-') and entity_input[1:].isdigit())
                    if not is_numeric:
                        try:
                            from telethon.tl.functions.contacts import ResolveUsernameRequest
                            res = await self._client(ResolveUsernameRequest(entity_input))
                            if res.chats:
                                entity = res.chats[0]
                            elif res.users:
                                entity = res.users[0]
                        except Exception as ex:
                            self._log("warning", f"ResolveUsernameRequest falhou para '{entity_input}', tentando get_entity padrÃ£o: {ex}")
                    
                    if not entity:
                        entity = await self._client.get_entity(entity_input)

                    entity_name = getattr(entity, "title", None) or getattr(entity, "username", None) or src_clean
                    resolved_chats.append(entity)
                    self._log("info", f"âœ… Monitorando: {entity_name} (ID: {entity.id})")
                except Exception as e:
                    self._log("warning", f"âŒ Falha ao encontrar '{src_clean}': {e}")

            if not resolved_chats:
                self._log("warning", "Nenhuma fonte vÃ¡lida encontrada para monitorar.")
                return
            else:
                self._log("success", f"Bot conectado e monitorando {len(resolved_chats)} fontes via polling.")

            # â”€â”€ Seed: marca as mensagens atuais como jÃ¡ vistas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Assim sÃ³ processa mensagens NOVAS apÃ³s o bot iniciar
            for entity in resolved_chats:
                try:
                    msgs = await self._client.get_messages(entity, limit=5)
                    last_id = msgs[0].id if msgs else 0
                    self._last_seen_by_chat[entity.id] = last_id
                    self._log("info", f"[Polling] Cursor inicial {entity.id}: msg_id={last_id}")
                except Exception as exc:
                    self._log("warning", f"[Polling] Falha ao iniciar cursor de {getattr(entity, 'id', '?')}: {exc}")

            # â”€â”€ Processar mensagem e atualizar stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            async def _process_and_count(message) -> tuple[bool, bool, bool, Optional[dict]]:
                try:
                    processed, tg_ok, wp_ok, promo = await processar_mensagem(
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
                            if self._activity and (tg_ok or wp_ok):
                                destinations = []
                                if tg_ok:
                                    destinations.append("Telegram")
                                if wp_ok:
                                    destinations.append("WhatsApp")
                                destination_text = " e ".join(destinations)
                                total = self._stats["today_processed"]
                                
                                # Extrair informaÃ§Ãµes do produto
                                title_text = "Produto"
                                price_text = "N/A"
                                store_text = ""
                                if promo:
                                    if promo.get("seoTitle"):
                                        title_text = promo.get("seoTitle").strip()
                                    elif promo.get("originalTitle"):
                                        title_text = promo.get("originalTitle").strip()
                                    
                                    # Limitar tamanho do tÃ­tulo para caber no log
                                    if len(title_text) > 60:
                                        title_text = title_text[:57] + "..."
                                        
                                    if promo.get("newPrice"):
                                        price_text = f"R$ {promo.get('newPrice')}"
                                    elif promo.get("oldPrice"):
                                        price_text = f"R$ {promo.get('oldPrice')}"
                                        
                                    if promo.get("store"):
                                        store_text = f" [{promo.get('store')}]"
                                
                                # Calcular horÃ¡rio aproximado do prÃ³ximo disparo
                                delay_to_use = self._delay if self._delay > 0 else 3
                                next_dispatch = time.time() + delay_to_use
                                tz_br = timezone(timedelta(hours=-3))
                                next_time_str = datetime.fromtimestamp(next_dispatch, tz=tz_br).strftime("%H:%M:%S")
                                
                                activity_msg = (
                                    f"ðŸ“¦ {title_text}{store_text} | Valor: {price_text}\n"
                                    f"âœ… Enviado para {destination_text}! Total hoje: {total}.\n"
                                    f"â±ï¸ PrÃ³ximo envio liberado a partir das {next_time_str}."
                                )
                                self._activity(
                                    "success",
                                    activity_msg,
                                )
                        else:
                            self._stats["errors_24h"] += 1
                    return processed, tg_ok, wp_ok, promo
                except Exception as exc:
                    self._log("error", f"[BotRunner] Erro ao processar mensagem: {exc}")
                    with self._lock:
                        self._stats["errors_24h"] += 1
                    return False, False, False, None

            self._process_and_count = _process_and_count

            async def _delivery_worker() -> None:
                with self._lock:
                    _configured_delay = self._delay
                self._log(
                    "info",
                    f"[RateLimit] Fila de envio iniciada. Delay configurado: {_configured_delay}s ({_configured_delay//60}min {_configured_delay%60}s).",
                )
                
                burst_count = 0  # Controla envios imediatos
                
                while not self._stop_event.is_set():
                    # âœ… PASSO 1: PEGAR ITEM DA FILA (com timeout de 1s)
                    try:
                        fingerprint, message = await asyncio.wait_for(
                            self._delivery_queue.get(),
                            timeout=1,
                        )
                        with self._lock:
                            self._active_delivery_item = (fingerprint, message)
                        self._refresh_queue_snapshot()
                    except asyncio.TimeoutError:
                        continue

                    try:
                        msg_id = getattr(message, "id", "?")
                        queue_size = self._delivery_queue.qsize()
                        
                        # âœ… PASSO 2: VERIFICAR SE PRECISA ESPERAR COOLDOWN
                        while True:
                            with self._lock:
                                time_remaining = max(0, self._next_dispatch_at - time.time())
                            
                            if time_remaining <= 0:
                                # Cooldown terminado, pode processar
                                break
                            
                            self._log(
                                "info",
                                f"[RateLimit] Msg {msg_id} em cooldown: aguardando {int(time_remaining)}s. Fila restante: {queue_size}.",
                            )
                            
                            # Atualiza snapshot para o heartbeat ver o ETA correto
                            self._refresh_queue_snapshot()
                            
                            # Espera o tempo restante (ou atÃ© o bot parar), max 30s para refresh periÃ³dico
                            wait_chunk = min(time_remaining, 30)
                            try:
                                await asyncio.wait_for(
                                    self._stop_event.wait(),
                                    timeout=wait_chunk,
                                )
                                # Se chegou aqui, o bot foi parado
                                break
                            except asyncio.TimeoutError:
                                # Timeout normal, continua o loop de cooldown
                                pass
                        
                        # Se o bot foi parado durante a espera, sair
                        if self._stop_event.is_set():
                            self._delivery_queue.task_done()
                            break
                        
                        # âœ… PASSO 3: PROCESSAR A MENSAGEM
                        self._log(
                            "info",
                            f"[RateLimit] Processando msg {msg_id}. Fila restante: {queue_size}.",
                        )
                        
                        _processed, tg_ok, wp_ok, _promo = await self._process_and_count(message)
                        
                        # âœ… PASSO 4: SÃ“ ATIVAR COOLDOWN SE REALMENTE ENVIOU PARA ALGUM CANAL
                        actually_sent = tg_ok or wp_ok
                        if actually_sent:
                            with self._lock:
                                delay_to_use = self._delay if self._delay > 0 else 300
                                
                                # Burst logic: se fila restante for >= 3 (ou seja, total era 4), e ainda nÃ£o usamos o burst
                                if queue_size >= 3 and burst_count < 1:
                                    self._next_dispatch_at = time.time()  # Sem delay!
                                    burst_count += 1
                                    burst_msg = " âš¡ BURST ATIVADO: prÃ³ximo item imediato!"
                                else:
                                    self._next_dispatch_at = time.time() + delay_to_use
                                    burst_count = 0
                                    burst_msg = ""
                            
                            destinations = []
                            if tg_ok:
                                destinations.append("Telegram")
                            if wp_ok:
                                destinations.append("WhatsApp")
                            dest_text = " e ".join(destinations)
                            
                            self._log(
                                "info",
                                f"[RateLimit] âœ… Msg {msg_id} enviada para {dest_text}! PrÃ³ximo envio em {max(0, int(self._next_dispatch_at - time.time()))}s.{burst_msg}",
                            )
                        elif _processed:
                            self._log(
                                "info",
                                f"[RateLimit] â­ï¸  Msg {msg_id} processada mas filtrada/sem destino. PrÃ³ximo item imediato.",
                            )
                        else:
                            self._log(
                                "info",
                                f"[RateLimit] â­ï¸  Msg {msg_id} ignorada (nÃ£o Ã© promoÃ§Ã£o/link invÃ¡lido). PrÃ³ximo item imediato.",
                            )
                        
                    except Exception as exc:
                        self._log("error", f"[RateLimit] Erro ao processar msg {msg_id}: {exc}")
                    finally:
                        # âœ… FINALIZAR PRODUTO E MARCAR TASK COMO CONCLUÃDA
                        self._finish_product(fingerprint, remember_recent=False)
                        with self._lock:
                            self._active_delivery_item = None
                        self._delivery_queue.task_done()
                        self._refresh_queue_snapshot()

            self._delivery_queue = asyncio.Queue()
            self._delivery_worker_task = asyncio.create_task(_delivery_worker())

            # â”€â”€ Loop de polling (Tarefa Principal) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            self._log("info", "ðŸš€ Motor de busca (Polling) iniciado!")
            
            # Log inicial com configuraÃ§Ãµes
            wpp_enabled = self._config.get("send_whatsapp", False)
            wpp_destinations = self._config.get("wpp_destinations", [])
            wpp_endpoint = self._config.get("whatsapp_endpoint") or "http://localhost:4000/send"
            
            # Garantir que a config interna tambÃ©m seja corrigida se estiver nula
            if self._config.get("whatsapp_endpoint") is None:
                self._config["whatsapp_endpoint"] = wpp_endpoint
            
            now = time.time()
            if now - getattr(self, "_last_config_log_time", 0) > 600:
                self._log("info", f"âš™ï¸ WhatsApp Config: ENABLED={wpp_enabled} | Canais={wpp_destinations} | Endpoint={wpp_endpoint}")
                self._last_config_log_time = now
            
            while not self._stop_event.is_set():
                try:

                    for entity in resolved_chats:
                        if self._stop_event.is_set(): break
                        
                        last_seen = self._last_seen_by_chat.get(entity.id, 0)
                        
                        # Busca mensagens com timeout
                        try:
                            msgs = await asyncio.wait_for(
                                self._client.get_messages(entity, limit=10),
                                timeout=15
                            )
                        except asyncio.TimeoutError:
                            self._log("warning", f"[Polling] Timeout em {getattr(entity, 'id', '?')}")
                            continue

                        if not msgs: continue

                        new_msgs = [m for m in reversed(msgs) if m.id > last_seen]
                        
                        if new_msgs:
                            self._log("info", f"[{entity.id}] +{len(new_msgs)} mensagens novas!")
                            for message in new_msgs:
                                if not self._remember_message(entity.id, message.id): continue
                                
                                self._log("info", f"[{entity.id}/{message.id}] Processando...")
                                
                                # Atualiza cursor
                                with self._lock:
                                    self._last_seen_by_chat[entity.id] = max(self._last_seen_by_chat.get(entity.id, 0), message.id)

                                fingerprint = self._product_fingerprint(message)
                                if not self._remember_product(fingerprint):
                                    self._log(
                                        "info",
                                        f"[Dedup] Produto duplicado ignorado antes da fila (msg {message.id}).",
                                    )
                                    continue

                                # Enfileira para envio sequencial sem travar a proxima busca.
                                await self._delivery_queue.put((fingerprint, message))
                                self._refresh_queue_snapshot()
                                self._log(
                                    "info",
                                    f"[RateLimit] Msg {message.id} enfileirada. Fila: {self._delivery_queue.qsize()} item(ns).",
                                )

                    # Se a conexÃ£o cair, o client.get_messages vai falhar e cair aqui
                    if not self._client.is_connected():
                        self._log("warning", "ConexÃ£o perdida. Tentando reconectar...")
                        await self._client.connect()
                        await asyncio.sleep(5)
                    
                    # Espera o intervalo de 10 segundos
                    await asyncio.sleep(_POLL_INTERVAL)

                except Exception as exc:
                    self._log("error", f"[Polling] Erro no ciclo: {exc}")
                    await asyncio.sleep(10)

        except Exception as exc:
            self._log("error", f"[BotRunner] ExceÃ§Ã£o no cliente: {exc}")
            with self._lock:
                self._status_val = "error"
        finally:
            if self._delivery_worker_task:
                self._delivery_worker_task.cancel()
                try:
                    await self._delivery_worker_task
                except asyncio.CancelledError:
                    pass
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
