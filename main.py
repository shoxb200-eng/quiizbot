import os
import asyncio
from io import BytesIO
from docx import Document
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8325777653:AAF01nUdarHlwh33UWMjFtVEBKZdRrqV1Ok"  # Bot tokeningizni shu yerga yozing

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bot xotirasi (Ma'lumotlar bazasi o'rniga vaqtinchalik)
# Ishlab chiqarishda buni Redis yoki PostgreSQL qilish tavsiya etiladi
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

def get_quiz_keyboard(options, q_index, time_limit, chat_id):
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"ans:{q_index}:{i}:{time_limit}:{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Salom! Men Quiz botman. Menga `.docx` formatidagi test faylini yuboring.\n"
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
            "current_index": 0,
            "results": {},  # user_id: {"name": x, "correct": 0, "total": 0}
            "answered_users": set(),
            "is_group": message.chat.type in ["group", "supergroup"]
        }
        
        # Taymerni tanlash
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
    asyncio.create_task(run_quiz(chat_id, seconds))

async def run_quiz(chat_id, time_limit):
    game = games[chat_id]
    questions = game["questions"]
    
    for idx, q in enumerate(questions):
        game["current_index"] = idx
        game["answered_users"].clear()
        
        text = f"❓ **Savol {idx+1}/{len(questions)}**:\n\n{q['question']}\n\n⏱ Vaqt: {time_limit} sekund"
        msg = await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_quiz_keyboard(q["options"], idx, time_limit, chat_id))
        
        await asyncio.sleep(time_limit)
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except:
            pass

    # O'yin tugadi, natijalarni chiqarish
    results = game["results"]
    if game["is_group"]:
        report = "🏁 **Test yakunlandi! Guruh natijalari:**\n\n"
        if not results:
            report += "Hech kim qatnashmadi."
        for u_id, data in results.items():
            report += f"👤 {data['name']} -> {data['correct']} ta to'g'ri, {data['total'] - data['correct']} ta noto'g'ri\n"
    else:
        # Shaxsiy chat uchun
        user_id = list(results.keys())[0] if results else None
        if user_id:
            data = results[user_id]
            report = f"🏁 **Test tugadi! Sizning natijangiz:**\n\nTo'g'ri: {data['correct']} ta\nNoto'g'ri: {data['total'] - data['correct']} ta"
        else:
            report = "Test yakunlandi, lekin javoblar qayd etilmadi."
            
    await bot.send_message(chat_id, report, parse_mode="Markdown")
    del games[chat_id]

@dp.callback_query(F.data.startswith("ans:"))
async def handle_answer(callback: types.CallbackQuery):
    _, q_index, opt_index, time_limit, chat_id = callback.data.split(":")
    q_index, opt_index, chat_id = int(q_index), int(opt_index), int(chat_id)
    user_id = callback.from_user.id
    name = callback.from_user.full_name
    
    if chat_id not in games:
        return await callback.answer("Bu test yakunlangan.", show_alert=True)
        
    game = games[chat_id]
    
    if game["current_index"] != q_index:
        return await callback.answer("Bu savolning vaqti tugagan!", show_alert=True)
        
    if user_id in game["answered_users"] and game["is_group"]:
        return await callback.answer("Siz bu savolga javob berib bo'ldingiz!", show_alert=True)
        
    game["answered_users"].add(user_id)
    
    if user_id not in game["results"]:
        game["results"][user_id] = {"name": name, "correct": 0, "total": 0}
        
    q = game["questions"][q_index]
    chosen_option = q["options"][opt_index]
    
    game["results"][user_id]["total"] += 1
    is_correct = (chosen_option == q["correct"])
    
    if is_correct:
        game["results"][user_id]["correct"] += 1
        await callback.answer("To'g'ri javob!", show_alert=False)
    else:
        await callback.answer("Noto'g'ri javob!", show_alert=False)

    # Shaxsiy chatda javob berganda darhol keyingi savolga o'tish (taymerni kutmaslik uchun)
    if not game["is_group"]:
        # Bu sodda versiyada shaxsiy chatda ham taymer tugashini kutadi, guruhda esa hamma kutadi.
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
