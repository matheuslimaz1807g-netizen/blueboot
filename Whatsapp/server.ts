import express from 'express';
import type { Request, Response } from 'express';
import { Client, LocalAuth, MessageMedia } from 'whatsapp-web.js';
import cors from 'cors';
import dotenv from 'dotenv';
import qrcode from 'qrcode'; // Use raw qrcode gen instead of terminal

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
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
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
  statusVal = "connected";
  qrCodeBase64 = "";
});

client.on('disconnected', () => {
    statusVal = "disconnected";
    qrCodeBase64 = "";
});

client.on('ready', async () => {
  console.log('✅ WhatsApp conectado e pronto!');
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
async function sendToGroups(text: string, base64Image?: string, mimeType?: string, targets: string[] = []) {
  if (targets.length === 0) {
    throw new Error('Nenhum grupo alvo especificado no payload da rota send.');
  }

  // Refresha a lista de grupos para garantir
  if (allGroups.length === 0) {
      const chats = await client.getChats();
      allGroups = chats.filter((c) => c.isGroup).map((c) => ({ name: c.name, id: c.id._serialized }));
  }

  // Filtra os que demos match
  const matchedGroups = allGroups.filter(g => targets.includes(g.name));
  if (matchedGroups.length === 0) {
      throw new Error(`Nenhum dos grupos (${targets.join(', ')}) foi encontrado no seu Whatsapp!`);
  }

  for (const group of matchedGroups) {
    try {
      if (base64Image && mimeType?.startsWith('image/')) {
        const media = new MessageMedia(mimeType, base64Image);
        await client.sendMessage(group.id, media, { caption: text });
      } else {
        await client.sendMessage(group.id, text);
      }
      console.log(`📤 Enviado com sucesso para: ${group.name}`);
    } catch (err: any) {
      console.error(`❌ Erro ao enviar para ${group.name}:`, err.message);
    }

    // Delay de 1.5s entre grupos para evitar bloqueios
    await new Promise((res) => setTimeout(res, 1500));
  }
}

// --- ROTAS DA API ---

app.get('/status', (req: Request, res: Response): void => {
    res.json({
        status: statusVal,
        qr: qrCodeBase64
    });
});

app.post('/send', async (req: Request, res: Response): Promise<void> => {
  const { text, base64Image, mimeType, targets } = req.body;

  try {
    await sendToGroups(text, base64Image, mimeType, targets);
    res.status(200).json({ status: 'ok', message: 'Mensagem enviada aos grupos.' });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// --- INICIALIZAÇÃO ---
const PORT = process.env.PORT || 4000;
client.initialize();
app.listen(PORT, () => console.log(`🚀 Servidor rodando na porta ${PORT}`));