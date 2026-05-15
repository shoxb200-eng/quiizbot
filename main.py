import os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

# 1. Render uchun kichik server (o'chib qolmaslik uchun)
app = Flask('')

@app.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# 2. Quiz Bot qismi
TOKEN = os.getenv("TOKEN") # Tokenni Render sozlamalaridan olamiz

async def start(update: Update, context):
    await update.message.reply_text("Quiz botga xush kelibsiz! /quiz buyrug'ini yuboring.")

async def quiz(update: Update, context):
    question = "O'zbekistondagi eng baland tog' cho'qqisi qaysi?"
    options = ["Hazrati Sulton", "Adelung", "Besh-tor", "Gissar"]
    
    await update.message.reply_poll(
        question=question,
        options=options,
        type='quiz',
        correct_option_id=0, # Hazrati Sulton to'g'ri javob
        explanation="Hazrati Sulton cho'qqisi 4643 metr balandlikka ega."
    )

if __name__ == '__main__':
    # Serverni alohida oqimda ishga tushiramiz
    Thread(target=run_flask).start()
    
    # Botni ishga tushiramiz
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("quiz", quiz))
    
    print("Bot yoqildi...")
    app_bot.run_polling()
