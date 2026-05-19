import express from 'express';
import type { Request, Response } from 'express';
import { Client, LocalAuth, MessageMedia } from 'whatsapp-web.js';
import cors from 'cors';
import dotenv from 'dotenv';
import qrcode from 'qrcode';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Cache para armazenar os IDs encontrados (nome do grupo -> id do whatsapp)
let allGroups: { name: string; id: string }[] = [];
let statusVal: "disconnected" | "qr" | "connected" = "disconnected";
let qrCodeBase64: string = "";

const client = new Client({
  authStrategy: new LocalAuth(),
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

client.on('qr', async (qr: string) => {
  statusVal = "qr";
  try {
      qrCodeBase64 = await qrcode.toDataURL(qr); // Returns data:image/png;base64,...
  } catch (err) {
      console.error("Erro gerando QR base64:", err);
  }
});

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

async function refreshGroups() {
  try {
    const chats = await client.getChats();
    let channels: any[] = [];
    try {
      channels = (await (client as any).getChannels()) || [];
    } catch (e) {
      console.log("Sem método getChannels ou erro:", e);
    }

    const all = [...chats, ...channels];

    allGroups = all
      .filter((c) => c.isGroup || c.isChannel || (c.id && c.id._serialized && (c.id._serialized.includes('@newsletter') || c.id._serialized.includes('@broadcast'))))
      .map((c) => ({ name: c.name, id: c.id._serialized }));

    // Remove duplicados
    allGroups = allGroups.filter((v, i, a) => a.findIndex(t => (t.id === v.id)) === i);
  } catch (err: any) {
    throw err;
  }
}

client.on('ready', async () => {
  console.log('✅ WhatsApp conectado e pronto!');
  statusVal = "connected";
  try {
    await refreshGroups();
    console.log(`📋 Total de grupos/canais monitorados: ${allGroups.length}`);
  } catch (err: any) {
    console.error("Erro ao buscar chats no start:", err.message);
  }
});


// --- FILA DE MENSAGENS (serialização de envios concorrentes) ---
let messageQueue: any[] = [];
let isProcessing = false;
// ⚠️ O delay entre envios é controlado pelo bot Python (delay_segundos).
// Este servidor apenas serializa chamadas concorrentes — sem delay interno.

async function processQueue() {
  if (isProcessing || messageQueue.length === 0) return;
  isProcessing = true;

  while (messageQueue.length > 0) {
    const item = messageQueue.shift();
    console.log(`[Queue] Processando envio para grupos: ${item.targets.join(", ")}`);
    
    try {
      await sendToGroupsInternal(item.text, item.base64Image, item.mimeType, item.targets);
      console.log("[Queue] Envio concluído.");
    } catch (err: any) {
      console.error("[Queue] Erro ao processar item da fila:", err.message);
    }
  }

  isProcessing = false;
}

/**
 * Função interna para enviar mensagens (sem delay de fila)
 */
async function sendToGroupsInternal(text: string, base64Image?: string, mimeType?: string, targets: string[] = []) {
  if (statusVal !== "connected") {
    throw new Error(`WhatsApp não está conectado.`);
  }

  try {
    // Refresha a lista de grupos para garantir
    await refreshGroups();
  } catch (err: any) {
    console.warn("Aviso: Timeout ao atualizar lista de grupos, usando versao em cache", err.message);
  }

  const matchedGroups = allGroups.filter((g) => targets.includes(g.name));
  
  if (matchedGroups.length === 0) {
    throw new Error(`Nenhum dos grupos/canais (${targets.join(', ')}) foi encontrado no seu Whatsapp!`);
  }

  for (const group of matchedGroups) {
    try {
      if (base64Image && (mimeType?.startsWith("image/"))) {
        const media = new MessageMedia(mimeType, base64Image);
        await client.sendMessage(group.id, media, { caption: text });
      } else {
        await client.sendMessage(group.id, text);
      }
      console.log(`[Direct] Enviado para: ${group.name}`);
      // Pequeno delay de 3s entre grupos do mesmo lote
      await new Promise((res) => setTimeout(res, 3000));
    } catch (err: any) {
      console.error(`[Direct] Erro em ${group.name}:`, err.message);
    }
  }
}

// --- ROTAS DA API ---

app.get('/status', (req: Request, res: Response): void => {
    res.json({
        status: statusVal,
        qr: qrCodeBase64,
        queue_size: messageQueue.length
    });
});

app.post('/send', async (req: Request, res: Response): Promise<void> => {
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
});

// --- INICIALIZAÇÃO ---
const PORT = process.env.PORT || 4000;
client.initialize().catch((err: any) => {
  console.error("Failed to initialize WhatsApp client:", err);
});
app.listen(PORT, () => console.log(`🚀 Servidor rodando na porta ${PORT}`));