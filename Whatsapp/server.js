"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const whatsapp_web_js_1 = require("whatsapp-web.js");
const cors_1 = __importDefault(require("cors"));
const dotenv_1 = __importDefault(require("dotenv"));
const qrcode_1 = __importDefault(require("qrcode"));
dotenv_1.default.config();
const app = (0, express_1.default)();
app.use((0, cors_1.default)());
app.use(express_1.default.json({ limit: '10mb' }));
// Cache para armazenar os IDs encontrados (nome -> id do whatsapp)
let allTargets = [];
let statusVal = "disconnected";
let qrCodeBase64 = "";
const client = new whatsapp_web_js_1.Client({
    authStrategy: new whatsapp_web_js_1.LocalAuth(),
    puppeteer: {
        headless: true, // Invisible, so it can run via python hidden process
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-zygote',
            '--disable-extensions',
            '--disable-client-side-phishing-detection',
            '--disable-component-update',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-notifications',
            '--disable-offer-store-unmasked-wallet-cards',
            '--disable-popup-blocking',
            '--disable-print-preview',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-speech-api',
            '--disable-sync',
            '--ignore-gpu-blacklist',
            '--metrics-recording-only',
            '--no-default-browser-check',
            '--no-first-run',
            '--no-pings',
            '--password-store=basic',
            '--use-gl=swiftshader',
            '--use-mock-keychain',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        ],
    },
});
function applyChannelMediaCompatibilityPatch() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const result = yield client.pupPage.evaluate(() => {
                var _a, _b, _c;
                const webWindow = window;
                const msgModelClass = (_c = (_b = (_a = webWindow.require) === null || _a === void 0 ? void 0 : _a.call(webWindow, 'WAWebCollections')) === null || _b === void 0 ? void 0 : _b.Msg) === null || _c === void 0 ? void 0 : _c.modelClass;
                if (!(msgModelClass === null || msgModelClass === void 0 ? void 0 : msgModelClass.prototype)) {
                    return { applied: false, reason: 'Msg model indisponivel' };
                }
                if (typeof msgModelClass.prototype.avParams === 'function') {
                    return { applied: false, reason: 'avParams ja existe' };
                }
                msgModelClass.prototype.avParams = function () {
                    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p, _q, _r, _s, _t, _u, _v;
                    const raw = typeof this.toJSON === 'function' ? this.toJSON() : {};
                    const mediaData = this.mediaData && typeof this.mediaData.toJSON === 'function'
                        ? this.mediaData.toJSON()
                        : (this.mediaData || {});
                    const mediaObject = this.mediaObject || {};
                    return Object.assign(Object.assign(Object.assign({}, raw), mediaData), { type: (_a = this.type) !== null && _a !== void 0 ? _a : raw.type, mimetype: (_b = this.mimetype) !== null && _b !== void 0 ? _b : mediaData.mimetype, filehash: (_d = (_c = this.filehash) !== null && _c !== void 0 ? _c : mediaData.filehash) !== null && _d !== void 0 ? _d : mediaObject.filehash, encFilehash: (_e = this.encFilehash) !== null && _e !== void 0 ? _e : mediaData.encFilehash, uploadhash: (_f = this.uploadhash) !== null && _f !== void 0 ? _f : mediaData.uploadhash, directPath: (_g = this.directPath) !== null && _g !== void 0 ? _g : mediaData.directPath, mediaKey: (_h = this.mediaKey) !== null && _h !== void 0 ? _h : mediaData.mediaKey, mediaKeyTimestamp: (_j = this.mediaKeyTimestamp) !== null && _j !== void 0 ? _j : mediaData.mediaKeyTimestamp, size: (_l = (_k = this.size) !== null && _k !== void 0 ? _k : mediaData.size) !== null && _l !== void 0 ? _l : mediaObject.size, width: (_m = this.width) !== null && _m !== void 0 ? _m : mediaData.width, height: (_o = this.height) !== null && _o !== void 0 ? _o : mediaData.height, mediaHandle: (_p = this.mediaHandle) !== null && _p !== void 0 ? _p : mediaData.mediaHandle, caption: (_q = this.caption) !== null && _q !== void 0 ? _q : mediaData.caption, isGif: (_r = this.isGif) !== null && _r !== void 0 ? _r : mediaData.isGif, isPtt: (_s = this.isPtt) !== null && _s !== void 0 ? _s : mediaData.isPtt, waveform: (_t = this.waveform) !== null && _t !== void 0 ? _t : mediaData.waveform, streamingSidecar: (_u = this.streamingSidecar) !== null && _u !== void 0 ? _u : mediaData.streamingSidecar, firstFrameSidecar: (_v = this.firstFrameSidecar) !== null && _v !== void 0 ? _v : mediaData.firstFrameSidecar });
                };
                return { applied: true, reason: 'fallback avParams instalado' };
            });
            console.log(`[Compat] Patch de midia para canais: ${result.reason}`);
        }
        catch (err) {
            console.warn("[Compat] Nao foi possivel aplicar patch de midia para canais:", err.message);
        }
    });
}
// --- EVENTOS DO WHATSAPP ---
client.on('qr', (qr) => __awaiter(void 0, void 0, void 0, function* () {
    statusVal = "qr";
    try {
        qrCodeBase64 = yield qrcode_1.default.toDataURL(qr, {
            errorCorrectionLevel: 'M',
            type: 'image/png',
            margin: 2,
            width: 400,
            color: { dark: '#000000', light: '#FFFFFF' },
        });
        console.log('📱 Novo QR Code gerado (escaneie em até ~20s)');
    }
    catch (err) {
        console.error("Erro gerando QR base64:", err);
    }
}));
client.on('authenticated', () => {
    console.log("✅ Authenticated!");
    statusVal = "connected";
    qrCodeBase64 = "";
});
client.on('auth_failure', (msg) => {
    console.error("❌ Authentication failure:", msg);
    statusVal = "disconnected";
});
client.on('disconnected', () => {
    statusVal = "disconnected";
    qrCodeBase64 = "";
});
function refreshTargets() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const chats = yield client.getChats();
            let channels = [];
            try {
                channels = (yield client.getChannels()) || [];
            }
            catch (e) {
                console.log("Sem método getChannels ou erro:", e);
            }
            const all = [...chats, ...channels];
            allTargets = all
                .filter((c) => {
                const isChannel = c.isChannel || (c.id && c.id._serialized && (c.id._serialized.includes('@newsletter') || c.id._serialized.includes('@broadcast')));
                const isGroup = c.isGroup || (c.id && c.id._serialized && c.id._serialized.includes('@g.us'));
                return isChannel || isGroup;
            })
                .map((c) => {
                const isGrp = c.isGroup || (c.id && c.id._serialized && c.id._serialized.includes('@g.us'));
                return {
                    name: c.name,
                    id: c.id._serialized,
                    type: isGrp ? 'group' : 'channel'
                };
            });
            // Remove duplicados
            allTargets = allTargets.filter((v, i, a) => a.findIndex(t => (t.id === v.id)) === i);
        }
        catch (err) {
            throw err;
        }
    });
}
client.on('ready', () => __awaiter(void 0, void 0, void 0, function* () {
    console.log('✅ WhatsApp conectado e pronto!');
    statusVal = "connected";
    try {
        yield applyChannelMediaCompatibilityPatch();
        yield refreshTargets();
        console.log(`📋 Total de canais/grupos monitorados: ${allTargets.length}`);
    }
    catch (err) {
        console.error("Erro ao buscar chats no start:", err.message);
    }
}));
// --- FILA DE MENSAGENS (serialização de envios concorrentes) ---
let messageQueue = [];
let isProcessing = false;
// ⚠️ O delay entre envios é controlado pelo bot Python (delay_segundos).
// Este servidor apenas serializa chamadas concorrentes — sem delay interno.
function processQueue() {
    return __awaiter(this, void 0, void 0, function* () {
        if (isProcessing || messageQueue.length === 0)
            return;
        isProcessing = true;
        while (messageQueue.length > 0) {
            const item = messageQueue.shift();
            console.log(`[Queue] Processando envio para destinos: ${item.targets.join(", ")}`);
            try {
                const result = yield sendToDestinationsInternal(item.text, item.base64Image, item.mimeType, item.targets);
                console.log(`[Queue] Envio concluído. Sucessos: ${result.successCount}. Falhas: ${result.failureCount}.`);
            }
            catch (err) {
                console.error("[Queue] Erro ao processar item da fila:", err.message);
            }
        }
        isProcessing = false;
    });
}
/**
 * Função interna para enviar mensagens para destinos (canais ou grupos)
 */
function sendToDestinationsInternal(text_1, base64Image_1, mimeType_1) {
    return __awaiter(this, arguments, void 0, function* (text, base64Image, mimeType, targets = []) {
        if (statusVal !== "connected") {
            throw new Error(`WhatsApp não está conectado.`);
        }
        try {
            yield refreshTargets();
        }
        catch (err) {
            console.warn("Aviso: Timeout ao atualizar lista de chats, usando versao em cache", err.message);
        }
        const matchedChats = [];
        for (const target of targets) {
            let parsedTargetName = target;
            let expectedType = null;
            if (target.startsWith("channel:")) {
                parsedTargetName = target.replace("channel:", "");
                expectedType = "channel";
            }
            else if (target.startsWith("group:")) {
                parsedTargetName = target.replace("group:", "");
                expectedType = "group";
            }
            const found = allTargets.find((t) => {
                if (t.name !== parsedTargetName)
                    return false;
                if (expectedType !== null && t.type !== expectedType)
                    return false;
                return true;
            });
            if (found) {
                matchedChats.push(found);
            }
        }
        if (matchedChats.length === 0) {
            throw new Error(`Nenhum dos destinos (${targets.join(', ')}) foi encontrado no seu Whatsapp!`);
        }
        let successCount = 0;
        let failureCount = 0;
        const failures = [];
        for (const chat of matchedChats) {
            try {
                let sentMessage;
                if (base64Image && (mimeType === null || mimeType === void 0 ? void 0 : mimeType.startsWith("image/"))) {
                    const media = new whatsapp_web_js_1.MessageMedia(mimeType, base64Image);
                    sentMessage = yield client.sendMessage(chat.id, media, { caption: text });
                }
                else {
                    sentMessage = yield client.sendMessage(chat.id, text);
                }
                if (!sentMessage) {
                    throw new Error("whatsapp-web.js retornou envio vazio/null");
                }
                console.log(`[Direct] Enviado para ${chat.type === 'group' ? 'grupo' : 'canal'}: ${chat.name}`);
                successCount += 1;
                // Pequeno delay de 3s entre destinos do mesmo lote
                yield new Promise((res) => setTimeout(res, 3000));
            }
            catch (err) {
                failureCount += 1;
                failures.push(`${chat.name} (${chat.type}): ${err.message}`);
                console.error(`[Direct] Erro em ${chat.name} (${chat.type}):`, err.message);
            }
        }
        if (successCount === 0) {
            throw new Error(`Todos os destinos falharam: ${failures.join('; ')}`);
        }
        return { successCount, failureCount };
    });
}
// --- ROTAS DA API ---
app.get('/status', (req, res) => {
    res.json({
        status: statusVal,
        qr: qrCodeBase64,
        queue_size: messageQueue.length
    });
});
app.post('/send', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    const { text, base64Image, mimeType, targets } = req.body;
    if (!text && !base64Image) {
        res.status(400).json({ error: "Conteúdo vazio" });
        return;
    }
    // Adiciona na fila
    messageQueue.push({ text, base64Image, mimeType, targets });
    // Inicia o processamento se não estiver rodando
    processQueue();
    res.status(202).json({
        status: "queued",
        message: "Mensagem adicionada à fila de processamento lento.",
        queue_position: messageQueue.length
    });
}));
// --- INICIALIZAÇÃO ---
const PORT = process.env.PORT || 4000;
client.initialize().catch((err) => {
    console.error("Failed to initialize WhatsApp client:", err);
});
app.listen(PORT, () => console.log(`🚀 Servidor rodando na porta ${PORT}`));
