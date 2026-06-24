import os
import re
import random
import logging
import tempfile
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL_REGEX = re.compile(r'https?://[^\s]+')

# LISTA DE SITES PERMITIDOS
SITES_PERMITIDOS = [
    "instagram.com", "twitter.com", "x.com", "tiktok.com", 
    "reddit.com", "soundcloud.com", "youtube.com", "youtu.be", "pinterest.com"
]

ERRO_MSGS = [
    "𝘮𝘪𝘢𝘶... 🐱💔 não consegui baixar esse",
    "𝘮𝘪𝘢𝘶? 🐾 esse aqui me venceu...",
    "nyaa~ 🙀 esse link tá difícil demais pra mim",
    "*orelhas caídas* 😿 não rolou dessa vez",
]

def is_allowed_url(url):
    return any(site in url.lower() for site in SITES_PERMITIDOS)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    urls = URL_REGEX.findall(message.text)
    if not urls:
        return

    for url in urls:
        if not is_allowed_url(url):
            logger.info(f"Link ignorado (não é rede social): {url}")
            continue

        logger.info(f"Iniciando yt-dlp para: {url}")
        
        # Configurações de Download do Gatinho
        ydl_opts = {
            'outtmpl': os.path.join(tempfile.gettempdir(), 'gatinho_%(id)s.%(ext)s'),
            # Pega o melhor formato que já tenha vídeo e áudio juntos
            'format': 'best[ext=mp4]/best', 
            # Limite rígido do Telegram: 50MB
            'max_filesize': 50 * 1024 * 1024, 
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        # Se for SoundCloud, queremos apenas o áudio
        if "soundcloud" in url.lower():
            ydl_opts['format'] = 'bestaudio/best'

        try:
            logger.info("Baixando arquivo...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Descobre o nome do arquivo que foi salvo
                if 'requested_downloads' in info:
                    filename = info['requested_downloads'][0]['filepath']
                else:
                    filename = ydl.prepare_filename(info)
                    
            logger.info(f"Sucesso! Arquivo salvo em: {filename}")

            # Identifica se é vídeo, áudio ou foto pela extensão
            with open(filename, "rb") as f:
                ext = filename.lower().split('.')[-1]
                
                if ext in ['mp3', 'm4a', 'wav', 'ogg']:
                    await message.reply_audio(audio=f)
                elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                    await message.reply_photo(photo=f)
                else:
                    await message.reply_video(video=f)
                    
            # Gato limpo: apaga o arquivo temporário
            os.unlink(filename) 
            logger.info("Mídia enviada pro grupo com sucesso!")

        # Tratamento de erros específicos do yt-dlp
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"O yt-dlp recusou o link. Motivo: {e}")
            await message.reply_text(random.choice(ERRO_MSGS))
        except Exception as e:
            logger.error(f"Erro geral inexperado: {e}")
            await message.reply_text(random.choice(ERRO_MSGS))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🐱 Bot gatinho turbinado com yt-dlp rodando...")
    app.run_polling(allowed_updates=["message"])
