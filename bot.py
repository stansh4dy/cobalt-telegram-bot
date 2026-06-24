import os
import re
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
COBALT_API = "https://cobalt-production-ce8d.up.railway.app"

URL_REGEX = re.compile(r'https?://[^\s]+')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    urls = URL_REGEX.findall(message.text)
    if not urls:
        return

    for url in urls:
        try:
            response = requests.post(
                COBALT_API,
                json={"url": url},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=30
            )
            data = response.json()
            status = data.get("status")

            if status == "tunnel" or status == "redirect":
                file_url = data.get("url")
                await message.reply_text("⬇️ Baixando mídia...")
                await message.reply_video(video=file_url)

            elif status == "picker":
                items = data.get("picker", [])
                await message.reply_text(f"🎬 Encontrei {len(items)} mídias, enviando...")
                for item in items[:5]:
                    await message.reply_video(video=item["url"])

            else:
                error = data.get("error", {}).get("code", "erro desconhecido")
                await message.reply_text(f"❌ Não consegui baixar: {error}")

        except Exception as e:
            await message.reply_text(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot rodando...")
    app.run_polling()
