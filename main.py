import telebot
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8325777653:AAF01nUdarHlwh33UWMjFtVEBKZdRrqV1Ok"

bot = telebot.TeleBot(TOKEN)

with open("questions.json", "r", encoding="utf-8") as f:
    quizzes = json.load(f)

user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    for quiz_name in quizzes.keys():
        keyboard.add(KeyboardButton(quiz_name))

    bot.send_message(
        message.chat.id,
        "Quiz tanlang:",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text

    if text in quizzes:
        user_data[user_id] = {
            "quiz": text,
            "index": 0,
            "score": 0
        }

        send_question(message.chat.id, user_id)
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
        bot.send_message(
            message.chat.id,
            f"Test tugadi!\n\nNatija: {data['score']} / {len(quizzes[quiz_name])}"
        )

        del user_data[user_id]
    else:
        send_question(message.chat.id, user_id)

def send_question(chat_id, user_id):
    data = user_data[user_id]

    quiz_name = data["quiz"]
    index = data["index"]

    q = quizzes[quiz_name][index]

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    for option in q["options"]:
        keyboard.add(KeyboardButton(option))

    bot.send_message(
        chat_id,
        f"{index + 1}-savol\n\n{q['question']}",
        reply_markup=keyboard
    )

print("Bot ishladi...")
bot.infinity_polling()
