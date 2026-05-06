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
      "--disable-accelerated-2d-canvas",
      "--no-zygote",
      "--single-process",
      "--disable-gpu",
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
/**
 * Função para enviar mensagens para grupos dinâmicos
 */
async function sendToGroups(text, base64Image, mimeType, targets = []) {
  if (statusVal !== "connected") {
    throw new Error(
      `WhatsApp não está conectado (Status: ${statusVal}). Por favor, escaneie o QR Code no dashboard.`,
    );
  }
  if (targets.length === 0) {
    throw new Error("Nenhum grupo alvo especificado no payload da rota send.");
  }
  // Refresha a lista de grupos para garantir
  if (allGroups.length === 0) {
    const chats = await client.getChats();
    allGroups = chats
      .filter((c) => c.isGroup)
      .map((c) => ({ name: c.name, id: c.id._serialized }));
  }
  // Filtra os que demos match
  const matchedGroups = allGroups.filter((g) => targets.includes(g.name));
  if (matchedGroups.length === 0) {
    throw new Error(
      `Nenhum dos grupos (${targets.join(", ")}) foi encontrado no seu Whatsapp! Verifique se você faz parte desses grupos.`,
    );
  }
  for (const group of matchedGroups) {
    try {
      if (
        base64Image &&
        (mimeType === null || mimeType === void 0
          ? void 0
          : mimeType.startsWith("image/"))
      ) {
        const media = new whatsapp_web_js_1.MessageMedia(mimeType, base64Image);
        await client.sendMessage(group.id, media, { caption: text });
      } else {
        await client.sendMessage(group.id, text);
      }
      console.log(`📤 Enviado com sucesso para: ${group.name}`);
    } catch (err) {
      console.error(`❌ Erro ao enviar para ${group.name}:`, err.message);
      throw new Error(
        `Erro ao enviar mensagem para ${group.name}: ${err.message}`,
      );
    }
    // Delay de 1.5s entre grupos para evitar bloqueios
    await new Promise((res) => setTimeout(res, 1500));
  }
}
// --- ROTAS DA API ---
app.get("/status", (req, res) => {
  res.json({
    status: statusVal,
    qr: qrCodeBase64,
  });
});
app.post("/send", async (req, res) => {
  const { text, base64Image, mimeType, targets } = req.body;
  // Validação básica do payload
  if (!text && !base64Image) {
    res
      .status(400)
      .json({ error: "É necessário fornecer 'text' ou 'base64Image'" });
    return;
  }
  if (!Array.isArray(targets) || targets.length === 0) {
    res
      .status(400)
      .json({ error: "É necessário fornecer 'targets' como array não vazio" });
    return;
  }
  try {
    await sendToGroups(text, base64Image, mimeType, targets);
    res
      .status(200)
      .json({ status: "ok", message: "Mensagem enviada aos grupos." });
  } catch (err) {
    console.error("API /send Error:", err.message);
    res.status(500).json({ error: err.message });
  }
});
// --- INICIALIZAÇÃO ---
const PORT = process.env.PORT || 4000;
client.initialize().catch((err) => {
  console.error("Failed to initialize WhatsApp client:", err);
});
app.listen(PORT, () => console.log(`🚀 Servidor rodando na porta ${PORT}`));
