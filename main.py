import os
import asyncio
from io import BytesIO
from docx import Document
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = os.environ.get("BOT_TOKEN", "8325777653:AAF01nUdarHlwh33UWMjFtVEBKZdRrqV1Ok")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bot xotirasi
games = {} 

def parse_docx(file_bytes):
    """Docx faylini o'qib, savollar ro'yxatini ajratib oladi"""
    doc = Document(BytesIO(file_bytes))
    questions = []
    
    current_q = None
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
            
        if text.startswith('#'):
            if current_q:
                questions.append(current_q)
            current_q = {"question": text[1:].strip(), "options": [], "correct": None}
        elif text.startswith('$') and current_q:
            current_q["options"].append(text[1:].strip())
        elif text.startswith('*') and current_q:
            opt = text[1:].strip()
            current_q["options"].append(opt)
            current_q["correct"] = opt
            
    if current_q:
        questions.append(current_q)
    return questions

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Salom! Men haqiqiy Viktorina (Poll) botman. Menga `.docx` formatidagi test faylini yuboring.\n"
        "Fayl formati:\n# Savol\n$ Variant\n* To'g'ri javob"
    )

@dp.message(F.document)
async def handle_docs(message: types.Message):
    if not message.document.file_name.endswith('.docx'):
        return await message.answer("Iltimos, faqat `.docx` (Word) fayl yuboring.")
        
    file_info = await bot.get_file(message.document.file_id)
    file_bytes = await bot.download_file(file_info.file_path)
    
    try:
        questions = parse_docx(file_bytes.read())
        if not questions:
            return await message.answer("Fayldan savollar topilmadi. Formatni tekshiring.")
            
        chat_id = message.chat.id
        games[chat_id] = {
            "questions": questions,
            "current_index": 0
        }
        
        # Taymerni tanlash tugmalari
        builder = InlineKeyboardBuilder()
        builder.button(text="15 Sekund", callback_data=f"time:15:{chat_id}")
        builder.button(text="30 Sekund", callback_data=f"time:30:{chat_id}")
        builder.button(text="1 Daqiqa", callback_data=f"time:60:{chat_id}")
        builder.adjust(3)
        
        await message.answer(f"Fayl qabul qilindi. {len(questions)} ta savol topildi. Taymerni tanlang:", reply_markup=builder.as_markup())
    except Exception as e:
        await message.answer(f"Faylni o'qishda xatolik: {e}")

@dp.callback_query(F.data.startswith("time:"))
async def set_time(callback: types.CallbackQuery):
    _, seconds, chat_id = callback.data.split(":")
    chat_id = int(chat_id)
    seconds = int(seconds)
    
    if chat_id not in games:
        return await callback.answer("O'yin topilmadi yoki eskirgan.", show_alert=True)
        
    await callback.message.delete()
    asyncio.create_task(run_poll_quiz(chat_id, seconds))

async def run_poll_quiz(chat_id, time_limit):
    if chat_id not in games:
        return
    game = games[chat_id]
    questions = game["questions"]
    
    for idx, q in enumerate(questions):
        if chat_id not in games:
            break
            
        # To'g'ri javobning indeksini topamiz (Telegramga indeks kerak)
        try:
            correct_index = q["options"].index(q["correct"])
        except ValueError:
            correct_index = 0  # Agar xatolik bo'lsa, birinchisini belgilaydi
            
        # Haqiqiy Telegram Viktorinasini yuborish (send_poll)
        # explanation - foydalanuvchi noto'g'ri bossa, to'g'ri javob tushuntirishi
        poll_msg = await bot.send_poll(
            chat_id=chat_id,
            question=f"Savol {idx+1}/{len(questions)}:\n{q['question']}",
            options=q["options"],
            type="quiz",  # Viktorina rejimi
            correct_option_id=correct_index,
            is_anonymous=False,  # Ovoz bergan odamlar ko'rinishi uchun FALSE bo'lishi shart!
            explanation="Kechirasiz, bu noto'g'ri javob edi!"
        )
        
        # Belgilangan vaqtchalik kutamiz (15, 30 yoki 60 soniya)
        await asyncio.sleep(time_limit)
        
        # Vaqt tugagach, so'rovnomani yopamiz (Ovoz berish to'xtaydi, lekin foizlar ko'rinib turadi)
        try:
            await bot.stop_poll(chat_id, poll_msg.message_id)
        except Exception as e:
            print(f"Pollni to'xtatishda xatolik: {e}")
            
        # Savollar orasida 2 soniya kichik tanaffus (hammasi ketma-ket yopishib ketmasligi uchun)
        await asyncio.sleep(2)

    await bot.send_message(chat_id, "🏁 **Barcha testlar yakunlandi!**")
    if chat_id in games:
        del games[chat_id]

# Render uchun soxta veb-server
async def web_handle(request):
    return web.Response(text="Bot muvaffaqiyatli ishlamoqda!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', web_handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    print("Bot va Soxta Server tayyor...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
