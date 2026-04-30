"""
Gera uma session string do Telegram para usar na VPS.
Execute UMA VEZ no seu computador local.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 39179009
API_HASH = "9037ff6e2a3ca9c44071f825f687fff1"
PHONE = input("Digite seu número (ex: +5562981416890): ").strip()

client = TelegramClient(StringSession(), API_ID, API_HASH)
client.start(phone=PHONE)
session_string = client.session.save()
client.disconnect()
print("\n✅ Sua SESSION STRING (copie tudo abaixo):")
print(session_string)
print("\nCole no .env.personal da VPS em TELEGRAM_SESSION_STRING=")
