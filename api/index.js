const { Telegraf } = require('telegraf');
const express = require('express');
const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');

const bot = new Telegraf(process.env.TELEGRAM_TOKEN);
const HF_API_KEY = process.env.HF_API_KEY;
const HF_API_URL = 'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0';
const app = express();

app.use(express.json());

// Konfigurasi logging
console.log = (...args) => {
  const timestamp = new Date().toISOString();
  process.stdout.write(`[${timestamp}] ${args.join(' ')}\n`);
};

// Health check endpoint
app.get('/', (req, res) => {
  res.send('Bot is running');
});

// Handle perintah /start
bot.start((ctx) => ctx.reply('Halo! Saya bot pembuat gambar gratis. Kirim deskripsi gambar, misalnya: "A cat in a spaceship". Catatan: Generasi gambar bisa memakan waktu.'));

// Handle pesan teks
bot.on('text', async (ctx) => {
  const prompt = ctx.message.text;
  await ctx.reply(`Memproses: ${prompt}... Harap tunggu (bisa 10-30 detik).`);

  try {
    const response = await axios.post(
      HF_API_URL,
      {
        inputs: prompt,
        parameters: {
          num_inference_steps: 30,
          guidance_scale: 7.5,
        },
      },
      {
        headers: {
          Authorization: `Bearer ${HF_API_KEY}`,
          'Content-Type': 'application/json',
        },
        responseType: 'arraybuffer',
        timeout: 60000, // Timeout 60 detik untuk Hugging Face API
      }
    );

    if (response.status === 200) {
      const imagePath = path.join('/tmp', `temp_image_${ctx.from.id}_${Date.now()}.png`);
      await fs.writeFile(imagePath, response.data);
      await ctx.replyWithPhoto({ source: imagePath }, { caption: `Gambar untuk: ${prompt}` });
      await fs.unlink(imagePath);
    } else {
      await ctx.reply(`Gagal menghasilkan gambar: ${response.statusText}`);
    }
  } catch (error) {
    console.error('Error:', error.message);
    await ctx.reply('Terjadi kesalahan saat menghasilkan gambar. Coba lagi nanti.');
  }
});

// Webhook endpoint untuk Telegram
app.post('/webhook', async (req, res) => {
  try {
    await bot.handleUpdate(req.body);
    res.sendStatus(200);
  } catch (error) {
    console.error('Webhook error:', error.message);
    res.sendStatus(500);
  }
});

// Export untuk Vercel
module.exports = app;

// Set webhook saat startup (hanya sekali, tidak di setiap request)
const setWebhook = async () => {
  try {
    const webhookUrl = `${process.env.VERCEL_URL || 'https://your-vercel-app.vercel.app'}/webhook`;
    await bot.telegram.setWebhook(webhookUrl);
    console.log(`Webhook set to ${webhookUrl}`);
  } catch (error) {
    console.error('Failed to set webhook:', error.message);
  }
};

// Jalankan setWebhook sekali saat server start
setWebhook();
