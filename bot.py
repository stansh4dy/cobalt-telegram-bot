import os
import re
import requests
import random
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
COBALT_API = "https://cobalt-production-ce8d.up.railway.app"

URL_REGEX = re.compile(r'https?://[^\s]+')

ERRO_MSGS = [
    "𝘮𝘪𝘢𝘶... 🐱💔 não consegui baixar esse",
    "𝘮𝘪𝘢𝘶? 🐾 esse aqui me venceu...",
    "nyaa~ 🙀 esse link tá difícil demais pra mim",
    "*orelhas caídas* 😿 não rolou dessa vez",
]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    urls = URL_REGEX.findall(message.text)
    if not urls:
        return

    for url in urls:
        logger.info(f"Link recebido: {url}")
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
            logger.info(f"Resposta cobalt: {data}")

            if status == "tunnel" or status == "redirect":
                file_url = data.get("url")
                try:
                    await message.reply_video(video=file_url)
                    logger.info("Vídeo enviado com sucesso")
                except Exception as e:
                    logger.info(f"Não é vídeo, tentando áudio: {e}")
                    try:
                        await message.reply_audio(audio=file_url)
                        logger.info("Áudio enviado com sucesso")
                    except Exception as e2:
                        logger.error(f"Falhou envio: {e2}")
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
                logger.warning(f"Status inesperado: {status} | Data: {data}")
                await message.reply_text(random.choice(ERRO_MSGS))

        except Exception as e:
            logger.error(f"Erro geral: {e}")
            await message.reply_text(random.choice(ERRO_MSGS))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🐱 Bot gatinho rodando...")
    app.run_polling(allowed_updates=["message"])
