import os
import re
import random
import logging
import tempfile
import requests
import yt_dlp
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

# DIVISÃO DE TAREFAS
YTDLP_SITES = ["youtube.com", "youtu.be", "soundcloud.com", "reddit.com"]
COBALT_SITES = ["instagram.com", "twitter.com", "x.com", "tiktok.com", "pinterest.com"]

ERRO_MSGS = [
    "𝘮𝘪𝘢𝘶... 🐱💔 não consegui baixar esse",
    "𝘮𝘪𝘢𝘶? 🐾 esse aqui me venceu...",
    "nyaa~ 🙀 esse link tá difícil demais pra mim",
    "*orelhas caídas* 😿 não rolou dessa vez",
]

def download_generic_file(url):
    """Baixa arquivos vindos do Cobalt identificando se é foto, vídeo ou áudio"""
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")

    suffix = ".mp4"
    if "audio" in content_type:
        suffix = ".mp3"
    elif "image" in content_type:
        suffix = ".jpg"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    for chunk in response.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name, content_type

async def process_with_ytdlp(url, message):
    """Processa links pesados usando yt-dlp"""
    logger.info(f"[yt-dlp] Processando: {url}")

    ydl_opts = {
        'outtmpl': os.path.join(tempfile.gettempdir(), 'gatinho_%(id)s.%(ext)s'),
        # Procura o melhor vídeo até 720p e junta com o melhor áudio
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        # Força o formato final a ser MP4 para rodar em qualquer celular
        'merge_output_format': 'mp4',
        'max_filesize': 50 * 1024 * 1024,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt'
    }

    if "soundcloud" in url.lower():
        ydl_opts['format'] = 'bestaudio/best'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = (
            info['requested_downloads'][0]['filepath']
            if 'requested_downloads' in info
            else ydl.prepare_filename(info)
        )

    with open(filename, "rb") as f:
        ext = filename.lower().split('.')[-1]
        if ext in ['mp3', 'm4a', 'wav', 'ogg']:
            await message.reply_audio(audio=f)
        elif ext in ['jpg', 'jpeg', 'png', 'webp']:
            await message.reply_photo(photo=f)
        else:
            await message.reply_video(video=f)
    os.unlink(filename)

async def process_with_cobalt(url, message):
    """Processa redes sociais e fotos usando a API do Cobalt"""
    logger.info(f"[Cobalt] Processando: {url}")
    response = requests.post(
        COBALT_API,
        json={"url": url},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=30
    )
    data = response.json()
    status = data.get("status")

    if status == "error":
        raise Exception(f"Cobalt error: {data.get('text')}")

    if status in ("tunnel", "redirect"):
        file_url = data.get("url")
        path, content_type = download_generic_file(file_url)
        with open(path, "rb") as f:
            if "image" in content_type:
                await message.reply_photo(photo=f)
            elif "audio" in content_type:
                await message.reply_audio(audio=f)
            else:
                await message.reply_video(video=f)
        os.unlink(path)

    elif status == "picker":
        items = data.get("picker", [])
        for item in items[:5]:
            path, content_type = download_generic_file(item["url"])
            with open(path, "rb") as f:
                if "image" in content_type:
                    await message.reply_photo(photo=f)
                else:
                    await message.reply_video(video=f)
            os.unlink(path)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    urls = URL_REGEX.findall(message.text)
    for url in urls:
        url_lower = url.lower()

        # Decide qual ferramenta usar
        use_ytdlp = any(site in url_lower for site in YTDLP_SITES)
        use_cobalt = any(site in url_lower for site in COBALT_SITES)

        if not use_ytdlp and not use_cobalt:
            logger.info(f"Link de site aleatório ignorado: {url}")
            continue

        try:
            if use_ytdlp:
                await process_with_ytdlp(url, message)
            elif use_cobalt:
                await process_with_cobalt(url, message)
            logger.info("Mídia enviada com sucesso!")
        except Exception as e:
            logger.error(f"Falha ao processar {url}: {e}")
            await message.reply_text(random.choice(ERRO_MSGS))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🐱 Bot gatinho HÍBRIDO rodando...")
    app.run_polling(allowed_updates=["message"])
