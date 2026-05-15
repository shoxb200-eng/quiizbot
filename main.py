import asyncio
import json

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8325777653:AAF01nUdarHlwh33UWMjFtVEBKZdRrqV1Ok"

bot = Bot(token=TOKEN)
dp = Dispatcher()

with open("questions.json", "r", encoding="utf-8") as f:
    quizzes = json.load(f)

user_data = {}

@dp.message(CommandStart())
async def start(message: types.Message):
    buttons = []

    for quiz_name in quizzes.keys():
        buttons.append([KeyboardButton(text=quiz_name)])

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await message.answer(
        "Quiz tanlang:",
        reply_markup=keyboard
    )

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    if text in quizzes:
        user_data[user_id] = {
            "quiz": text,
            "index": 0,
            "score": 0
        }

        await send_question(message, user_id)
        return

    if user_id not in user_data:
        return

    data = user_data[user_id]
    quiz_name = data["quiz"]
    index = data["index"]

    current_question = quizzes[quiz_name][index]

    if text == current_question["answer"]:
        data["score"] += 1

    data["index"] += 1

    if data["index"] >= len(quizzes[quiz_name]):
        await message.answer(
            f"Test tugadi!\n\nNatija: {data['score']} / {len(quizzes[quiz_name])}"
        )

        del user_data[user_id]
    else:
        await send_question(message, user_id)

async def send_question(message, user_id):
    data = user_data[user_id]

    quiz_name = data["quiz"]
    index = data["index"]

    q = quizzes[quiz_name][index]

    buttons = []

    for option in q["options"]:
        buttons.append([KeyboardButton(text=option)])

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await message.answer(
        f"{index + 1}-savol\n\n{q['question']}",
        reply_markup=keyboard
    )

async def main():
    print("Bot ishladi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
