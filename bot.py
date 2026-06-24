import os
import re
import requests
import random
import logging
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
COBALT_API = "https://cobalt-production-ce8d.up.railway.app"

SUPPORTED_DOMAINS = [
    "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "reddit.com", "soundcloud.com", "streamable.com", "vimeo.com",
    "twitch.tv", "tumblr.com", "vk.com", "ok.ru",
    "bsky.app", "bsky.social", "dailymotion.com", "snapchat.com",
    "facebook.com", "fb.watch", "youtube.com", "youtu.be"
]

URL_REGEX = re.compile(r'https?://[^\s\]>]+')

ERRO_MSGS = [
    "𝘮𝘪𝘢𝘶... 🐱💔 não consegui baixar esse",
    "𝘮𝘪𝘢𝘶? 🐾 esse aqui me venceu...",
    "nyaa~ 🙀 esse link tá difícil demais pra mim",
    "*orelhas caídas* 😿 não rolou dessa vez",
]

def is_supported(url):
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def download_file(url):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    suffix = ".mp3" if "audio" in content_type else ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    size = 0
    for chunk in response.iter_content(chunk_size=8192):
        tmp.write(chunk)
        size += len(chunk)
    tmp.close()
    return tmp.name, content_type, size

async def send_media(message, path, content_type, filename):
    with open(path, "rb") as f:
        if "audio" in content_type or filename.endswith(".mp3"):
            await message.reply_audio(audio=f)
        elif "image" in content_type or filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
            await message.reply_photo(photo=f)
        else:
            await message.reply_video(video=f)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    urls = URL_REGEX.findall(message.text)
    if not urls:
        return

    for url in urls:
        if not is_supported(url):
            logger.info(f"Ignorado (não é rede social): {url}")
            continue

        logger.info(f"Link recebido: {url}")
        try:
            response = requests.post(
                COBALT_API,
                json={"url": url},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=30
            )
            data = response.json()
            status = data.get("status")
            logger.info(f"Status cobalt: {status}")

            if status in ("tunnel", "redirect"):
                file_url = data.get("url")
                filename = data.get("filename", "")
                try:
                    path, content_type, size = download_file(file_url)
                    if size == 0:
                        os.unlink(path)
                        await message.reply_text(random.choice(ERRO_MSGS))
                        continue
                    await send_media(message, path, content_type, filename)
                    os.unlink(path)
                    logger.info("Enviado com sucesso!")
                except Exception as e:
                    logger.error(f"Erro envio: {e}")
                    await message.reply_text(random.choice(ERRO_MSGS))

            elif status == "picker":
                items = data.get("picker", [])
                for item in items[:5]:
                    try:
                        path, content_type, size = download_file(item["url"])
                        if size == 0:
                            os.unlink(path)
                            continue
                        await send_media(message, path, content_type, item.get("url", ""))
                        os.unlink(path)
                    except Exception as e:
                        logger.error(f"Erro picker item: {e}")

            elif status == "error":
                error_code = data.get("error", {}).get("code", "")
                logger.warning(f"Erro cobalt: {error_code}")
                if error_code in ("error.api.link.unsupported", "error.api.fetch.fail"):
                    pass
                else:
                    await message.reply_text(random.choice(ERRO_MSGS))

            else:
                logger.warning(f"Status desconhecido: {data}")

        except Exception as e:
            logger.error(f"Erro geral: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🐱 Bot gatinho rodando...")
    app.run_polling(allowed_updates=["message"])
