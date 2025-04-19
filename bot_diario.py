import os
import logging
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# Carrega variáveis de ambiente locais (opcional em dev)
load_dotenv()

# Token protegido via env var
BOT_TOKEN = os.getenv("BOT_TOKEN")

FUNDO_PATH = "Fundo.jpeg"
FONTE_PATH = "SFUIDisplay-Bold.ttf"
RESOLUCAO_ALTA = (2160, 3840)
RESOLUCAO_FINAL = (1080, 1920)

# Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ /start recebido!")
    await update.message.reply_text("Bot pronto! Envie o link da matéria.")

# Quebra linhas
def quebra_linhas(texto, fonte, largura_max, draw):
    palavras = texto.split()
    linhas = []
    linha_atual = ""

    for palavra in palavras:
        teste = linha_atual + " " + palavra if linha_atual else palavra
        largura = draw.textlength(teste, font=fonte)
        if largura <= largura_max:
            linha_atual = teste
        else:
            linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)
    return linhas

# Extrai dados do link
def extract_info(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        container = soup.find('div', class_='news-ctn')
        title = container['data-page-title'].strip() if container and container.has_attr('data-page-title') else 'Título não encontrado.'
        image = soup.find('div', class_='news-details-image')
        image_url = image['data-thumb-url'] if image and image.has_attr('data-thumb-url') else None
        return title, image_url
    except Exception as e:
        logger.error(f"❌ Erro ao extrair informações: {e}")
        return "Erro ao acessar a página.", None

# Gera a imagem
def gerar_imagem(titulo, imagem_url):
    print("🧠 Gerando imagem em alta resolução...")
    fundo = Image.open(FUNDO_PATH).convert("RGB").resize(RESOLUCAO_ALTA)
    draw = ImageDraw.Draw(fundo)
    fonte = ImageFont.truetype(FONTE_PATH, 128)

    # Título alinhado à esquerda
    linhas = quebra_linhas(titulo, fonte, 1760, draw)  # 880*2
    x_texto = 180
    y_texto = 500
    for linha in linhas:
        draw.text((x_texto, y_texto), linha, font=fonte, fill="white")
        y_texto += 150  # espaçamento entre linhas ajustado

    # Imagem da matéria
    if imagem_url:
        try:
            response_img = requests.get(imagem_url, timeout=10)
            if response_img.status_code == 200:
                imagem = Image.open(BytesIO(response_img.content)).convert("RGB")
                imagem = imagem.resize((1800, 1200))
                fundo.paste(imagem, (180, 1200))
                print("✅ Imagem da matéria aplicada.")
        except Exception as e:
            print(f"⚠️ Erro ao carregar imagem: {e}")

    # Reduz e salva
    imagem_final = fundo.resize(RESOLUCAO_FINAL, Image.LANCZOS)
    buffer = BytesIO()
    imagem_final.save(buffer, format="JPEG")
    buffer.seek(0)

    with open("teste_saida.jpg", "wb") as f:
        f.write(buffer.getbuffer())

    return buffer

# Mensagem recebida
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Mensagem recebida.")
    if update.message and update.message.text:
        text = update.message.text.strip()
        chat_id = update.effective_chat.id

        if text.startswith("http") and "odiarioonline.com.br" in text:
            await update.message.reply_text("🔄 Processando o link...")
            titulo, imagem_url = extract_info(text)
            print(f"🔎 Título: {titulo}")
            print(f"🖼️ Imagem URL: {imagem_url}")
            imagem_final = gerar_imagem(titulo, imagem_url)
            await context.bot.send_document(chat_id=chat_id, document=imagem_final, filename="noticia.jpg", caption="✅ Imagem pronta!")
        else:
            await update.message.reply_text("❗ Envie um link válido do site O Diário Online.")
    else:
        print("⚠️ Mensagem sem texto.")

# Main
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN não definido.")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    logger.info("🤖 Bot rodando... Envie o link da matéria.")
    app.run_polling()

if __name__ == "__main__":
    main()
