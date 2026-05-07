"use strict";
var __importDefault =
  (this && this.__importDefault) ||
  function (mod) {
    return mod && mod.__esModule ? mod : { default: mod };
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
app.use(express_1.default.json({ limit: "10mb" }));
// Cache para armazenar os IDs encontrados (nome do grupo -> id do whatsapp)
let allGroups = [];
let statusVal = "disconnected";
let qrCodeBase64 = "";
const client = new whatsapp_web_js_1.Client({
  authStrategy: new whatsapp_web_js_1.LocalAuth(),
  webVersionCache: {
    type: "remote",
    remotePath:
      "https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html",
  },
  puppeteer: {
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--no-zygote",
      "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ],
  },
});
// --- EVENTOS DO WHATSAPP ---
client.on("qr", async (qr) => {
  statusVal = "qr";
  try {
    qrCodeBase64 = await qrcode_1.default.toDataURL(qr);
    console.log("New QR Code generated. Scan it on the dashboard.");
  } catch (err) {
    console.error("Erro gerando QR base64:", err);
  }
});
client.on("authenticated", () => {
  console.log("✅ Authenticated!");
  statusVal = "connected";
  qrCodeBase64 = "";
});
client.on("auth_failure", (msg) => {
  console.error("❌ Authentication failure:", msg);
  statusVal = "disconnected";
});
client.on("disconnected", (reason) => {
  console.warn("⚠️ Client disconnected:", reason);
  statusVal = "disconnected";
  qrCodeBase64 = "";
});
client.on("ready", async () => {
  console.log("✅ WhatsApp conectado e pronto!");
  statusVal = "connected";
  // Busca todos os chats e guarda apenas grupos
  const chats = await client.getChats();
  allGroups = chats
    .filter((c) => c.isGroup)
    .map((c) => ({ name: c.name, id: c.id._serialized }));
  console.log(`📋 Total de grupos monitorados: ${allGroups.length}`);
});
// --- FILA DE MENSAGENS (ANTI-BAN) ---
let messageQueue = [];
let isProcessing = false;
const SEND_DELAY = (parseInt(process.env.WHATSAPP_DELAY_MINUTES) || 15) * 60 * 1000;

async function processQueue() {
  if (isProcessing || messageQueue.length === 0) return;
  isProcessing = true;

  while (messageQueue.length > 0) {
    const item = messageQueue.shift();
    console.log(`[Queue] Processando envio para grupos: ${item.targets.join(", ")}`);
    
    try {
      await sendToGroupsInternal(item.text, item.base64Image, item.mimeType, item.targets);
      console.log("[Queue] Envio concluído.");
    } catch (err) {
      console.error("[Queue] Erro ao processar item da fila:", err.message);
    }

    if (messageQueue.length > 0) {
      console.log(`[Queue] Aguardando ${SEND_DELAY / 60000} minutos para o próximo disparo...`);
      await new Promise((res) => setTimeout(res, SEND_DELAY));
    }
  }

  isProcessing = false;
}

/**
 * Função interna para enviar mensagens (sem delay de fila)
 */
async function sendToGroupsInternal(text, base64Image, mimeType, targets = []) {
  if (statusVal !== "connected") {
    throw new Error(`WhatsApp não está conectado.`);
  }

  // Refresha a lista de grupos para garantir
  const chats = await client.getChats();
  allGroups = chats
    .filter((c) => c.isGroup)
    .map((c) => ({ name: c.name, id: c.id._serialized }));

  const matchedGroups = allGroups.filter((g) => targets.includes(g.name));
  
  for (const group of matchedGroups) {
    try {
      if (base64Image && (mimeType?.startsWith("image/"))) {
        const media = new whatsapp_web_js_1.MessageMedia(mimeType, base64Image);
        await client.sendMessage(group.id, media, { caption: text });
      } else {
        await client.sendMessage(group.id, text);
      }
      console.log(`[Direct] Enviado para: ${group.name}`);
      // Pequeno delay de 3s entre grupos do mesmo lote
      await new Promise((res) => setTimeout(res, 3000));
    } catch (err) {
      console.error(`[Direct] Erro em ${group.name}:`, err.message);
    }
  }
}

// --- ROTAS DA API ---
app.get("/status", (req, res) => {
  res.json({
    status: statusVal,
    qr: qrCodeBase64,
    queue_size: messageQueue.length,
    next_delay_min: isProcessing && messageQueue.length > 0 ? SEND_DELAY / 60000 : 0
  });
});

app.post("/send", async (req, res) => {
  const { text, base64Image, mimeType, targets } = req.body;

  if (!text && !base64Image) {
    return res.status(400).json({ error: "Conteúdo vazio" });
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
});
// --- INICIALIZAÇÃO ---
const PORT = process.env.PORT || 4000;
client.initialize().catch((err) => {
  console.error("Failed to initialize WhatsApp client:", err);
});
app.listen(PORT, () => console.log(`🚀 Servidor rodando na porta ${PORT}`));
