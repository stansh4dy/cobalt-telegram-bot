import os
import re
import requests
import random
import logging
import tempfile
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

def download_file(url):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    suffix = ".mp4"
    if "audio" in response.headers.get("content-type", ""):
        suffix = ".mp3"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    for chunk in response.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name, response.headers.get("content-type", "")

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
            logger.info(f"Resposta cobalt: {status}")

            if status in ("tunnel", "redirect"):
                file_url = data.get("url")
                filename = data.get("filename", "")
                try:
                    logger.info("Baixando arquivo...")
                    path, content_type = download_file(file_url)
                    logger.info(f"Arquivo baixado: {path} | tipo: {content_type}")
                    with open(path, "rb") as f:
                        if "audio" in content_type or filename.endswith(".mp3"):
                            await message.reply_audio(audio=f)
                        else:
                            await message.reply_video(video=f)
                    os.unlink(path)
                    logger.info("Enviado com sucesso!")
                except Exception as e:
                    logger.error(f"Erro no envio: {e}")
                    await message.reply_text(random.choice(ERRO_MSGS))

            elif status == "picker":
                items = data.get("picker", [])
                for item in items[:5]:
                    try:
                        path, content_type = download_file(item["url"])
                        with open(path, "rb") as f:
                            if "audio" in content_type:
                                await message.reply_audio(audio=f)
                            else:
                                await message.reply_video(video=f)
                        os.unlink(path)
                    except Exception as e:
                        logger.error(f"Erro picker: {e}")

            else:
                logger.warning(f"Status inesperado: {data}")
                await message.reply_text(random.choice(ERRO_MSGS))

        except Exception as e:
            logger.error(f"Erro geral: {e}")
            await message.reply_text(random.choice(ERRO_MSGS))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🐱 Bot gatinho rodando...")
    app.run_polling(allowed_updates=["message"])
