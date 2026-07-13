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

// Cache para armazenar os IDs encontrados (nome -> id do whatsapp)
let allTargets: { name: string; id: string; type: "channel" | "group" }[] = [];
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

async function applyChannelMediaCompatibilityPatch() {
  try {
    const result = await (client as any).pupPage.evaluate(() => {
      const webWindow = window as any;
      const msgModelClass = webWindow.require?.('WAWebCollections')?.Msg?.modelClass;

      if (!msgModelClass?.prototype) {
        return { applied: false, reason: 'Msg model indisponivel' };
      }

      if (typeof msgModelClass.prototype.avParams === 'function') {
        return { applied: false, reason: 'avParams ja existe' };
      }

      msgModelClass.prototype.avParams = function (this: any) {
        const raw = typeof this.toJSON === 'function' ? this.toJSON() : {};
        const mediaData = this.mediaData && typeof this.mediaData.toJSON === 'function'
          ? this.mediaData.toJSON()
          : (this.mediaData || {});
        const mediaObject = this.mediaObject || {};

        return {
          ...raw,
          ...mediaData,
          type: this.type ?? raw.type,
          mimetype: this.mimetype ?? mediaData.mimetype,
          filehash: this.filehash ?? mediaData.filehash ?? mediaObject.filehash,
          encFilehash: this.encFilehash ?? mediaData.encFilehash,
          uploadhash: this.uploadhash ?? mediaData.uploadhash,
          directPath: this.directPath ?? mediaData.directPath,
          mediaKey: this.mediaKey ?? mediaData.mediaKey,
          mediaKeyTimestamp: this.mediaKeyTimestamp ?? mediaData.mediaKeyTimestamp,
          size: this.size ?? mediaData.size ?? mediaObject.size,
          width: this.width ?? mediaData.width,
          height: this.height ?? mediaData.height,
          mediaHandle: this.mediaHandle ?? mediaData.mediaHandle,
          caption: this.caption ?? mediaData.caption,
          isGif: this.isGif ?? mediaData.isGif,
          isPtt: this.isPtt ?? mediaData.isPtt,
          waveform: this.waveform ?? mediaData.waveform,
          streamingSidecar: this.streamingSidecar ?? mediaData.streamingSidecar,
          firstFrameSidecar: this.firstFrameSidecar ?? mediaData.firstFrameSidecar,
        };
      };

      return { applied: true, reason: 'fallback avParams instalado' };
    });

    console.log(`[Compat] Patch de midia para canais: ${result.reason}`);
  } catch (err: any) {
    console.warn("[Compat] Nao foi possivel aplicar patch de midia para canais:", err.message);
  }
}

// --- EVENTOS DO WHATSAPP ---

client.on('qr', async (qr: string) => {
  statusVal = "qr";
  try {
    // QR maior + margem + correção alta = mais fácil de ler no painel / celular
    qrCodeBase64 = await qrcode.toDataURL(qr, {
      errorCorrectionLevel: 'M',
      type: 'image/png',
      margin: 2,
      width: 400,
      color: { dark: '#000000', light: '#FFFFFF' },
    });
    console.log('📱 Novo QR Code gerado (escaneie em até ~20s)');
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

async function refreshTargets() {
  try {
    const chats = await client.getChats();
    let channels: any[] = [];
    try {
      channels = (await (client as any).getChannels()) || [];
    } catch (e) {
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
          type: isGrp ? 'group' : 'channel' as const
        };
      });

    // Remove duplicados
    allTargets = allTargets.filter((v, i, a) => a.findIndex(t => (t.id === v.id)) === i);
  } catch (err: any) {
    throw err;
  }
}

client.on('ready', async () => {
  console.log('✅ WhatsApp conectado e pronto!');
  statusVal = "connected";
  try {
    await applyChannelMediaCompatibilityPatch();
    await refreshTargets();
    console.log(`📋 Total de canais/grupos monitorados: ${allTargets.length}`);
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
    console.log(`[Queue] Processando envio para destinos: ${item.targets.join(", ")}`);
    
    try {
      const result = await sendToDestinationsInternal(item.text, item.base64Image, item.mimeType, item.targets);
      console.log(`[Queue] Envio concluído. Sucessos: ${result.successCount}. Falhas: ${result.failureCount}.`);
    } catch (err: any) {
      console.error("[Queue] Erro ao processar item da fila:", err.message);
    }
  }

  isProcessing = false;
}

/**
 * Função interna para enviar mensagens para destinos (canais ou grupos)
 */
async function sendToDestinationsInternal(text: string, base64Image?: string, mimeType?: string, targets: string[] = []) {
  if (statusVal !== "connected") {
    throw new Error(`WhatsApp não está conectado.`);
  }

  try {
    await refreshTargets();
  } catch (err: any) {
    console.warn("Aviso: Timeout ao atualizar lista de chats, usando versao em cache", err.message);
  }

  const matchedChats: { name: string; id: string; type: string }[] = [];

  for (const target of targets) {
    let parsedTargetName = target;
    let expectedType: "channel" | "group" | null = null;

    if (target.startsWith("channel:")) {
      parsedTargetName = target.replace("channel:", "");
      expectedType = "channel";
    } else if (target.startsWith("group:")) {
      parsedTargetName = target.replace("group:", "");
      expectedType = "group";
    }

    const found = allTargets.find((t) => {
      if (t.name !== parsedTargetName) return false;
      if (expectedType !== null && t.type !== expectedType) return false;
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
  const failures: string[] = [];

  for (const chat of matchedChats) {
    try {
      let sentMessage: any;
      if (base64Image && (mimeType?.startsWith("image/"))) {
        const media = new MessageMedia(mimeType, base64Image);
        sentMessage = await client.sendMessage(chat.id, media, { caption: text });
      } else {
        sentMessage = await client.sendMessage(chat.id, text);
      }
      if (!sentMessage) {
        throw new Error("whatsapp-web.js retornou envio vazio/null");
      }
      console.log(`[Direct] Enviado para ${chat.type === 'group' ? 'grupo' : 'canal'}: ${chat.name}`);
      successCount += 1;
      // Pequeno delay de 3s entre destinos do mesmo lote
      await new Promise((res) => setTimeout(res, 3000));
    } catch (err: any) {
      failureCount += 1;
      failures.push(`${chat.name} (${chat.type}): ${err.message}`);
      console.error(`[Direct] Erro em ${chat.name} (${chat.type}):`, err.message);
    }
  }

  if (successCount === 0) {
    throw new Error(`Todos os destinos falharam: ${failures.join('; ')}`);
  }

  return { successCount, failureCount };
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
