from telethon import TelegramClient

api_id = 39179009
api_hash = '9037ff6e2a3ca9c44071f825f687fff1'

client = TelegramClient('session', api_id, api_hash)

async def main():
    dialogs = await client.get_dialogs()
    
    canal_alvo = None

    for dialog in dialogs:
        print(f"Nome: {dialog.name}")
        print(f"ID: {dialog.id}")
        print("-" * 30)

        # 🔎 troca aqui pelo nome do canal que você viu no print
        if dialog.name == "La Promotion - Promoções":
            canal_alvo = dialog

    # ⚠️ se não achou o canal
    if not canal_alvo:
        print("Canal não encontrado!")
        return

    print("\nPegando mensagens...\n")

    messages = await client.get_messages(canal_alvo, limit=10)

    for msg in messages:
        print(f"[{msg.date}] {msg.text}")
        print("-" * 50)


with client:
    client.loop.run_until_complete(main())