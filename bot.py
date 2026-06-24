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

# LISTA DE SITES PERMITIDOS - O bot só vai reagir a esses sites!
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

def download_file(url):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    
    content_type = response.headers.get("content-type", "")
    
    # Define a extensão correta com base no tipo de arquivo
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    urls = URL_REGEX.findall(message.text)
    if not urls:
        return

    for url in urls:
        # Se for um link de site aleatório, ignora
        if not is_allowed_url(url):
            logger.info(f"Link ignorado (não é rede social): {url}")
            continue

        logger.info(f"Link recebido para processar: {url}")
        
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
            
            # Se deu erro lá no Cobalt, vamos registrar O MOTIVO
            if status == "error":
                motivo = data.get("text", "Erro desconhecido")
                logger.error(f"O Cobalt recusou o link. Motivo: {motivo}")
                await message.reply_text(random.choice(ERRO_MSGS))
                continue

            logger.info(f"Status Cobalt: {status}")

            if status in ("tunnel", "redirect"):
                file_url = data.get("url")
                filename = data.get("filename", "")
                
                try:
                    logger.info("Baixando arquivo do Cobalt...")
                    path, content_type = download_file(file_url)
                    logger.info(f"Arquivo baixado: {path} | tipo: {content_type}")
                    
                    with open(path, "rb") as f:
                        if "audio" in content_type or filename.endswith(".mp3"):
                            await message.reply_audio(audio=f)
                        elif "image" in content_type or filename.endswith((".jpg", ".png")):
                            await message.reply_photo(photo=f)
                        else:
                            await message.reply_video(video=f)
                            
                    os.unlink(path) # Limpa o arquivo temp
                    logger.info("Mídia enviada com sucesso pro grupo!")
                    
                except Exception as e:
                    logger.error(f"Erro ao baixar/enviar para o Telegram: {e}")
                    await message.reply_text(random.choice(ERRO_MSGS))
                    
            elif status == "picker":
                items = data.get("picker", [])
                for item in items[:5]: # Pega no máximo 5 itens de uma galeria
                    try:
                        path, content_type = download_file(item["url"])
                        with open(path, "rb") as f:
                            if "audio" in content_type:
                                await message.reply_audio(audio=f)
                            elif "image" in content_type:
                                await message.reply_photo(photo=f)
                            else:
                                await message.reply_video(video=f)
                        os.unlink(path)
                    except Exception as e:
                        logger.error(f"Erro em item do picker: {e}")
                        
            else:
                logger.warning(f"Status inesperado recebido: {data}")
                await message.reply_text(random.choice(ERRO_MSGS))
                
        except Exception as e:
            logger.error(f"Erro na requisição ao Cobalt: {e}")
            await message.reply_text(random.choice(ERRO_MSGS))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🐱 Bot gatinho rodando e filtrando links...")
    app.run_polling(allowed_updates=["message"])
