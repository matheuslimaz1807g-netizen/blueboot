# ==============================
# 🧩 Imports
# ==============================
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import re
import asyncio
import os
import requests
import unicodedata
import subprocess
import base64
from dotenv import load_dotenv

# Seus módulos de afiliados
from Affiliates.shopee_affiliate import gerar_link_afiliado_shopee
from Affiliates.aliexpress_affiliate import gerar_links_afiliado_aliexpress
from Affiliates.MercadoLivre_affiliate import gerar_link_mercadolivre

# ==============================
# 🔑 Config
# ==============================
load_dotenv()

api_id   = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
TOKEN    = os.getenv("TELEGRAM_TOKEN")

client            = TelegramClient("session", api_id, api_hash)
destination_group = None
last_id           = None

ALI_APP_KEY    = os.getenv("ALIEXPRESS_APP_KEY")
ALI_APP_SECRET = os.getenv("ALIEXPRESS_APP_SECRET")
ALI_TRACKING_ID = os.getenv("ALIEXPRESS_TRACKING_ID")

SOURCE      = 'https://t.me/testemfoox'
DESTINATION = 'https://t.me/testemfoox'

# ==============================
# ✂️ LIMPEZA DE TEXTO (sem IA)
# ==============================
def limpar_texto(texto: str) -> str:
    """
    Remove a primeira linha (frase de impacto) e retorna
    o restante da mensagem sem linhas em branco iniciais.

    Exemplo de entrada:
        PRA VOCE SE SENTIR UM ALFA DE VERDADE

        👕 Kit 6 Camisetas Alpha
        💵 De R$257 por R$129
        - Cupom MELIACHA

    Saída:
        👕 Kit 6 Camisetas Alpha
        💵 De R$257 por R$129
        - Cupom MELIACHA
    """
    linhas = texto.splitlines()

    # Pula a primeira linha não-vazia (frase de impacto)
    i = 0
    for i, linha in enumerate(linhas):
        if linha.strip():          # primeira linha com conteúdo
            i += 1                 # marca como "consumida"
            break

    # Descarta linhas vazias imediatamente após a frase de impacto
    while i < len(linhas) and not linhas[i].strip():
        i += 1

    # Remove linhas que começam com # (hashtags de outros grupos)
    linhas_limpas = [l for l in linhas[i:] if not l.strip().startswith("#")]

    # Remove linhas vazias extras que possam ter sobrado no final
    return "\n".join(linhas_limpas).strip()

# ==============================
# 🔥 UTILITÁRIOS
# ==============================
def expandir_link(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=5)
        return response.url
    except:
        return url

def fechar_brave():
    try:
        if os.name == 'nt':
            subprocess.call(['taskkill', '/F', '/IM', 'brave.exe'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.call(['pkill', '-f', 'brave'])
    except:
        pass

# ==============================
# ⚙️ PROCESSAR MENSAGEM
# ==============================
async def process_message(msg):
    global last_id, destination_group

    if msg.id == last_id:
        return
    last_id = msg.id

    text = unicodedata.normalize("NFKD", msg.raw_text or "")
    if not text:
        return

    print(f"\n💬 Recebido original (ID: {msg.id})")

    # --- 1. CONVERSÃO DE LINKS ---
    ml_pattern         = r'(https?://(?:www\.)?(?:mercadolivre\.com(?:\.br)?|meli\.la)/[^\s]+)'
    shopee_pattern     = r'(https?://(?:www\.)?(?:shopee\.com\.br|s\.shopee\.com\.br)/[^\s]+)'
    aliexpress_pattern = r'(?:https?://)?(?:www\.)?(?:aliexpress\.com|a\.aliexpress\.com)/[^\s]+'

    # Mercado Livre
    links_ml = re.findall(ml_pattern, text)
    for link in links_ml:
        try:
            exp = expandir_link(link)
            aff = gerar_link_mercadolivre(exp)
            if aff:
                text = text.replace(link, aff)
        except:
            pass
        finally:
            fechar_brave()

    # AliExpress
    ali_raw = re.findall(aliexpress_pattern, text)
    if ali_raw:
        try:
            ali_links = [l if l.startswith("http") else "https://" + l for l in ali_raw]
            affs = gerar_links_afiliado_aliexpress(ali_links, ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID)
            for orig, new in zip(ali_raw, affs):
                if new:
                    text = text.replace(orig, new)
        except:
            pass

    # Shopee
    shopee_links = re.findall(shopee_pattern, text)
    for link in shopee_links:
        try:
            aff = await gerar_link_afiliado_shopee(link)
            if aff:
                text = text.replace(link, aff)
        except:
            pass

    # --- 2. LIMPEZA DE TEXTO ---
    text = limpar_texto(text)
    print("✅ Texto limpo (primeira linha removida).")

    # --- 3. DOWNLOAD MÍDIA ---
    image_path = None
    if msg.media and isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument)):
        try:
            image_path = f"temp_{msg.id}.jpg"
            await msg.download_media(file=image_path)
        except Exception as e:
            print(f"Erro ao baixar imagem: {e}")

    # --- 4. ENVIO FINAL ---
    try:
        if image_path:
            await client.send_file(destination_group, image_path, caption=text)
        else:
            await client.send_message(destination_group, text)
        print("✅ Enviado para Telegram.")

        wpp_payload = {"text": text}
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                wpp_payload["base64Image"] = base64.b64encode(f.read()).decode('utf-8')
                wpp_payload["mimeType"]    = "image/jpeg"

        requests.post("http://localhost:4000/send", json=wpp_payload, timeout=15)
        print("✅ Enviado para WhatsApp API.")

    except Exception as e:
        print(f"❌ Erro no disparo final: {e}")
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

# ==============================
# 🔥 ESCUTAR E MAIN
# ==============================
@client.on(events.NewMessage(chats=SOURCE))
async def handler(event):
    await process_message(event.message)

async def main():
    global destination_group
    await client.start(bot_token=TOKEN)
    await client.get_dialogs()

    try:
        destination_group = await client.get_entity(DESTINATION)
    except Exception as e:
        print(f"Erro ao localizar canal de destino: {e}")
        return

    print(f"\n🚀 Apenas Promo Rodando!")
    print(f"📡 Monitorando: {SOURCE}")

    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot encerrado manualmente.")