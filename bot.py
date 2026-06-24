import os
import re
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
COBALT_API = "https://cobalt-production-ce8d.up.railway.app"

URL_REGEX = re.compile(r'https?://[^\s]+')

ERRO_MSGS = [
    "𝘮𝘪𝘢𝘶... 🐱💔 não consegui baixar esse",
    "𝘮𝘪𝘢𝘶? 🐾 esse aqui me venceu...",
    "nyaa~ 🙀 esse link tá difícil demais pra mim",
    "*orelhas caídas* 😿 não rolou dessa vez",
]

import random

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
                try:
                    await message.reply_video(video=file_url)
                except Exception:
                    try:
                        await message.reply_audio(audio=file_url)
                    except Exception:
                        await message.reply_text(random.choice(ERRO_MSGS))

            elif status == "picker":
                items = data.get("picker", [])
                for item in items[:5]:
                    try:
                        await message.reply_video(video=item["url"])
                    except Exception:
                        try:
                            await message.reply_photo(photo=item["url"])
                        except Exception:
                            pass

            else:
                await message.reply_text(random.choice(ERRO_MSGS))

        except Exception:
            await message.reply_text(random.choice(ERRO_MSGS))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🐱 Bot gatinho rodando...")
    app.run_polling(allowed_updates=["message"])
