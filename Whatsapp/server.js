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
const qrcode_1 = __importDefault(require("qrcode")); // Use raw qrcode gen instead of terminal
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
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
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
    statusVal = "connected";
    qrCodeBase64 = "";
});
client.on('disconnected', () => {
    statusVal = "disconnected";
    qrCodeBase64 = "";
});
client.on('ready', () => __awaiter(void 0, void 0, void 0, function* () {
    console.log('✅ WhatsApp conectado e pronto!');
    statusVal = "connected";
    // Busca todos os chats e guarda grupos, canais e listas de transmissão
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
    console.log(`📋 Total de grupos/canais monitorados: ${allGroups.length}`);
}));
/**
 * Função para enviar mensagens para grupos dinâmicos
 */
function sendToGroups(text_1, base64Image_1, mimeType_1) {
    return __awaiter(this, arguments, void 0, function* (text, base64Image, mimeType, targets = []) {
        if (targets.length === 0) {
            throw new Error('Nenhum grupo alvo especificado no payload da rota send.');
        }
        // Refresha a lista de grupos/canais para garantir
        if (allGroups.length === 0) {
            const chats = yield client.getChats();
            let channels = [];
            try {
                channels = (yield client.getChannels()) || [];
            }
            catch (e) { }
            const all = [...chats, ...channels];
            allGroups = all
                .filter((c) => c.isGroup || c.isChannel || (c.id && c.id._serialized && (c.id._serialized.includes('@newsletter') || c.id._serialized.includes('@broadcast'))))
                .map((c) => ({ name: c.name, id: c.id._serialized }));
            allGroups = allGroups.filter((v, i, a) => a.findIndex(t => (t.id === v.id)) === i);
        }
        // Filtra os que demos match
        const matchedGroups = allGroups.filter(g => targets.includes(g.name));
        if (matchedGroups.length === 0) {
            throw new Error(`Nenhum dos grupos/canais (${targets.join(', ')}) foi encontrado no seu Whatsapp! Certifique-se de que o bot faz parte deles.`);
        }
        for (const group of matchedGroups) {
            try {
                if (base64Image && (mimeType === null || mimeType === void 0 ? void 0 : mimeType.startsWith('image/'))) {
                    const media = new whatsapp_web_js_1.MessageMedia(mimeType, base64Image);
                    yield client.sendMessage(group.id, media, { caption: text });
                }
                else {
                    yield client.sendMessage(group.id, text);
                }
                console.log(`📤 Enviado com sucesso para: ${group.name}`);
            }
            catch (err) {
                console.error(`❌ Erro ao enviar para ${group.name}:`, err.message);
            }
            // Delay de 1.5s entre grupos para evitar bloqueios
            yield new Promise((res) => setTimeout(res, 1500));
        }
    });
}
// --- ROTAS DA API ---
app.get('/status', (req, res) => {
    res.json({
        status: statusVal,
        qr: qrCodeBase64
    });
});
app.post('/send', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    const { text, base64Image, mimeType, targets } = req.body;
    try {
        yield sendToGroups(text, base64Image, mimeType, targets);
        res.status(200).json({ status: 'ok', message: 'Mensagem enviada aos grupos.' });
    }
    catch (err) {
        res.status(500).json({ error: err.message });
    }
}));
// --- INICIALIZAÇÃO ---
const PORT = process.env.PORT || 4000;
client.initialize();
app.listen(PORT, () => console.log(`🚀 Servidor rodando na porta ${PORT}`));
