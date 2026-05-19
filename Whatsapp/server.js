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
// Cache para armazenar os IDs encontrados (nome do grupo -> id do whatsapp)
let allGroups = [];
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
// --- EVENTOS DO WHATSAPP ---
client.on('qr', (qr) => __awaiter(void 0, void 0, void 0, function* () {
    statusVal = "qr";
    try {
        qrCodeBase64 = yield qrcode_1.default.toDataURL(qr); // Returns data:image/png;base64,...
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
function refreshGroups() {
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
            allGroups = all
                .filter((c) => c.isGroup || c.isChannel || (c.id && c.id._serialized && (c.id._serialized.includes('@newsletter') || c.id._serialized.includes('@broadcast'))))
                .map((c) => ({ name: c.name, id: c.id._serialized }));
            // Remove duplicados
            allGroups = allGroups.filter((v, i, a) => a.findIndex(t => (t.id === v.id)) === i);
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
        yield refreshGroups();
        console.log(`📋 Total de grupos/canais monitorados: ${allGroups.length}`);
    }
    catch (err) {
        console.error("Erro ao buscar chats no start:", err.message);
    }
}));
// --- FILA DE MENSAGENS (ANTI-BAN) ---
let messageQueue = [];
let isProcessing = false;
let lastDispatchTime = 0; // Armazena o timestamp do último envio bem-sucedido
const SEND_DELAY = (parseInt(process.env.WHATSAPP_DELAY_MINUTES || "15")) * 60 * 1000;
function processQueue() {
    return __awaiter(this, void 0, void 0, function* () {
        if (isProcessing || messageQueue.length === 0)
            return;
        isProcessing = true;
        while (messageQueue.length > 0) {
            // Enforça cooldown global mínimo entre disparos sucessivos
            const now = Date.now();
            const timeSinceLast = now - lastDispatchTime;
            if (timeSinceLast < SEND_DELAY) {
                const waitTime = SEND_DELAY - timeSinceLast;
                console.log(`[Queue] Respeitando cooldown mínimo: aguardando ${Math.ceil(waitTime / 1000)}s antes do envio do próximo item...`);
                yield new Promise((res) => setTimeout(res, waitTime));
            }
            const item = messageQueue.shift();
            console.log(`[Queue] Processando envio para grupos: ${item.targets.join(", ")}`);
            try {
                yield sendToGroupsInternal(item.text, item.base64Image, item.mimeType, item.targets);
                lastDispatchTime = Date.now(); // Atualiza após envio com sucesso
                console.log("[Queue] Envio concluído.");
            }
            catch (err) {
                console.error("[Queue] Erro ao processar item da fila:", err.message);
            }
        }
        isProcessing = false;
    });
}
/**
 * Função interna para enviar mensagens (sem delay de fila)
 */
function sendToGroupsInternal(text_1, base64Image_1, mimeType_1) {
    return __awaiter(this, arguments, void 0, function* (text, base64Image, mimeType, targets = []) {
        if (statusVal !== "connected") {
            throw new Error(`WhatsApp não está conectado.`);
        }
        try {
            // Refresha a lista de grupos para garantir
            yield refreshGroups();
        }
        catch (err) {
            console.warn("Aviso: Timeout ao atualizar lista de grupos, usando versao em cache", err.message);
        }
        const matchedGroups = allGroups.filter((g) => targets.includes(g.name));
        if (matchedGroups.length === 0) {
            throw new Error(`Nenhum dos grupos/canais (${targets.join(', ')}) foi encontrado no seu Whatsapp!`);
        }
        for (const group of matchedGroups) {
            try {
                if (base64Image && (mimeType === null || mimeType === void 0 ? void 0 : mimeType.startsWith("image/"))) {
                    const media = new whatsapp_web_js_1.MessageMedia(mimeType, base64Image);
                    yield client.sendMessage(group.id, media, { caption: text });
                }
                else {
                    yield client.sendMessage(group.id, text);
                }
                console.log(`[Direct] Enviado para: ${group.name}`);
                // Pequeno delay de 3s entre grupos do mesmo lote
                yield new Promise((res) => setTimeout(res, 3000));
            }
            catch (err) {
                console.error(`[Direct] Erro em ${group.name}:`, err.message);
            }
        }
    });
}
// --- ROTAS DA API ---
app.get('/status', (req, res) => {
    res.json({
        status: statusVal,
        qr: qrCodeBase64,
        queue_size: messageQueue.length,
        next_delay_min: isProcessing && messageQueue.length > 0 ? SEND_DELAY / 60000 : 0
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
