import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = os.environ.get("BOT_TOKEN", "8325777653:AAF01nUdarHlwh33UWMjFtVEBKZdRrqV1Ok")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bot xotirasi (Aktiv o'yinlar va foydalanuvchilar holati)
games = {}
# poll_id orqali qaysi guruh/chatga tegishliligini bilish uchun:
poll_to_chat = {}

# 1. JSON fayldan savollarni yuklash
# 'questions.json' fayli main.py bilan bitta papkada bo'lishi kerak
try:
    with open("questions.json", "r", encoding="utf-8") as file:
        QUIZ_QUESTIONS = json.load(file)
    print(f"Muvaffaqiyatli yuklandi: {len(QUIZ_QUESTIONS)} ta savol.")
except FileNotFoundError:
    # Agar fayl topilmasa, test uchun vaqtinchalik savollar
    QUIZ_QUESTIONS = [
        {"question": "Python qaysi yili yaratilgan?", "options": ["1989", "1991", "1995", "2000"], "correct": "1991"},
        {"question": "O'zbekiston poytaxti qayer?", "options": ["Samarqand", "Buxoro", "Toshkent"], "correct": "Toshkent"}
    ]
    print("questions.json topilmadi, test savollari yuklandi.")

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Salom! Men universal Viktorina botman.\n\n"
        "Testni boshlash uchun /quiz buyrug'ini yuboring.\n"
        "*(Meni guruhga qo'shib, guruhda ham /quiz buyrug'ini berishingiz mumkin)*"
    )

@dp.message(Command("quiz"))
async def start_quiz_session(message: types.Message):
    chat_id = message.chat.id
    is_group = message.chat.type in ["group", "supergroup"]
    
    # Yangi o'yin sessiyasini ochamiz
    games[chat_id] = {
        "questions": QUIZ_QUESTIONS,
        "current_index": 0,
        "time_limit": 30, # Standart vaqt, inline tugma orqali o'zgaradi
        "results": {},    # user_id: {"name": name, "correct": 0, "total": 0}
        "is_group": is_group,
        "current_poll_id": None,
        "current_msg_id": None,
        "task": None      # Shaxsiy chatda vaqtni buzish (cancel) qilish uchun taymer taski
    }
    
    # Vaqtni tanlash tugmalari
    builder = InlineKeyboardBuilder()
    builder.button(text="15 Sekund", callback_data=f"time:15:{chat_id}")
    builder.button(text="30 Sekund", callback_data=f"time:30:{chat_id}")
    builder.button(text="1 Daqiqa", callback_data=f"time:60:{chat_id}")
    builder.adjust(3)
    
    await message.answer("⏱ Viktorina uchun savol taymerini tanlang:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("time:"))
async def set_time_and_start(callback: types.CallbackQuery):
    _, seconds, chat_id = callback.data.split(":")
    chat_id = int(chat_id)
    seconds = int(seconds)
    
    if chat_id not in games:
        return await callback.answer("Sessiya topilmadi. Qaytadan /quiz bering.", show_alert=True)
        
    games[chat_id]["time_limit"] = seconds
    await callback.message.delete()
    
    # Viktorina funksiyasini zudlik bilan chaqiramiz
    await send_next_question(chat_id)

async def send_next_question(chat_id):
    if chat_id not in games:
        return
        
    game = games[chat_id]
    idx = game["current_index"]
    questions = game["questions"]
    
    # Agar savollar tugagan bo'lsa, natijani chiqaramiz
    if idx >= len(questions):
        await finish_quiz(chat_id)
        return
        
    q = questions[idx]
    try:
        correct_index = q["options"].index(q["correct"])
    except ValueError:
        correct_index = 0
        
    # Viktorinani (Poll) guruhga yoki shaxsiyga yuborish
    poll_msg = await bot.send_poll(
        chat_id=chat_id,
        question=f"Savol {idx+1}/{len(questions)}:\n{q['question']}",
        options=q["options"],
        type="quiz",
        correct_option_id=correct_index,
        is_anonymous=False, # Kim javob berganini bilishimiz shart!
        explanation="Noto'g'ri javob!"
    )
    
    game["current_poll_id"] = poll_msg.poll.id
    game["current_msg_id"] = poll_msg.message_id
    poll_to_chat[poll_msg.poll.id] = chat_id
    
    # Taymerni ishga tushiramiz (Guruhda ham, shaxsiyda ham vaqt tugashini nazorat qiladi)
    game["task"] = asyncio.create_task(wait_for_timer(chat_id, game["time_limit"]))

async def wait_for_timer(chat_id, duration):
    await asyncio.sleep(duration)
    if chat_id in games:
        game = games[chat_id]
        # Guruhda vaqt tugagach so'rovnomani yopamiz va keyingi savolga o'tamiz
        try:
            await bot.stop_poll(chat_id, game["current_msg_id"])
        except:
            pass
        
        await asyncio.sleep(1.5) # Kichik tanaffus
        game["current_index"] += 1
        await send_next_question(chat_id)

# 2. Ovoz berish jarayonini ushlash (Foydalanuvchi variant tanlaganda)
@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    poll_id = poll_answer.poll_id
    if poll_id not in poll_to_chat:
        return
        
    chat_id = poll_to_chat[poll_id]
    if chat_id not in games:
        return
        
    game = games[chat_id]
    user_id = poll_answer.user.id
    user_name = poll_answer.user.full_name
    
    # Natijalarni hisoblash bazasini tekshirish
    if user_id not in game["results"]:
        game["results"][user_id] = {"name": user_name, "correct": 0, "total": 0}
        
    game["results"][user_id]["total"] += 1
    
    # Tanlangan variant to'g'ri ekanligini bilish
    idx = game["current_index"]
    q = game["questions"][idx]
    correct_index = q["options"].index(q["correct"])
    
    if poll_answer.option_ids[0] == correct_index:
        game["results"][user_id]["correct"] += 1

    # AGAR SHAXSIY CHAT BO'LSA - Kutmasdan darhol keyingi savolga o'tkazamiz
    if not game["is_group"]:
        # Joriy taymerni bekor qilamiz
        if game["task"]:
            game["task"].cancel()
            
        try:
            await bot.stop_poll(chat_id, game["current_msg_id"])
        except:
            pass
            
        game["current_index"] += 1
        # Keyingi savolni yuborish uchun biroz kutish (animatsiya chiroyli ko'rinishi uchun)
        await asyncio.sleep(1)
        await send_next_question(chat_id)

async def finish_quiz(chat_id):
    if chat_id not in games:
        return
        
    game = games[chat_id]
    results = game["results"]
    
    report = "🏁 **Viktorina yakunlandi! Natijalar:**\n\n"
    
    if not results:
        report += "Hech kim testda qatnashmadi yoki savollarga javob berilmadi."
    else:
        # Natijalarni to'g'ri javoblar soni bo'yicha yuqoridan pastga saralaymiz
        sorted_results = sorted(results.items(), key=lambda x: x[1]["correct"], reverse=True)
        
        for i, (u_id, data) in enumerate(sorted_results, 1):
            report += f"{i}. 👤 {data['name']} ➔ **{data['correct']} ta** to'g'ri ({data['total']} tadan)\n"
            
    await bot.send_message(chat_id, report, parse_mode="Markdown")
    
    # Xotirani tozalash
    if game["current_poll_id"] in poll_to_chat:
        del poll_to_chat[game["current_poll_id"]]
    del games[chat_id]

# Render uchun majburiy soxta veb-server
async def web_handle(request):
    return web.Response(text="Quiz Bot is running...")

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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
