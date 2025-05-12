from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
import os
import logging
from datetime import datetime
import tempfile

# Inisialisasi Flask
app = Flask(__name__)

# Konfigurasi logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
HF_API_KEY = os.getenv('HF_API_KEY')
HF_API_URL = 'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0'

# Inisialisasi Bot dan Dispatcher
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Handler untuk perintah /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Halo! Saya bot pembuat gambar gratis. Kirim deskripsi gambar, misalnya: "A cat in a spaceship". '
        'Catatan: Proses bisa memakan waktu 10-30 detik.'
    )

# Handler untuk pesan teks
def generate_image(update: Update, context: CallbackContext) -> None:
    prompt = update.message.text
    update.message.reply_text(f'Memproses: {prompt}... Harap tunggu (bisa 10-30 detik).')

    try:
        # Panggil Hugging Face API
        headers = {
            'Authorization': f'Bearer {HF_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'inputs': prompt,
            'parameters': {
                'num_inference_steps': 30,
                'guidance_scale': 7.5
            }
        }
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            # Simpan gambar sementara di /tmp
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', dir='/tmp', delete=False)
            temp_file.write(response.content)
            temp_file.close()

            # Kirim gambar ke pengguna
            with open(temp_file.name, 'rb') as photo:
                update.message.reply_photo(
                    photo=photo,
                    caption=f'Gambar untuk: {prompt}'
                )
            
            # Hapus file sementara
            os.unlink(temp_file.name)
        else:
            update.message.reply_text(f'Gagal menghasilkan gambar: {response.status_text}')
    except Exception as e:
        logger.error(f'Error generating image: {str(e)}')
        update.message.reply_text('Terjadi kesalahan saat menghasilkan gambar. Coba lagi n  n/a

# Tambahkan handler ke dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, generate_image))

# Health check endpoint
@app.route('/')
def health_check():
    return 'Bot is running'

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return 'OK'

# Set webhook saat startup
def set_webhook():
    webhook_url = os.getenv('VERCEL_URL', 'https://your-vercel-app.vercel.app') + '/webhook'
    bot.set_webhook(webhook_url)
    logger.info(f'Webhook set to {webhook_url}')

if __name__ == '__main__':
    set_webhook()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
