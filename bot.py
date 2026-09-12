import os
import random
import telebot
import threading
from flask import Flask
from telebot import types

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'توکن_ربات_خودت')
bot = telebot.TeleBot(TOKEN)

love_messages = [
    "تو بهترین اتفاقی هستی که تو زندگیم افتاده ❤️",
    "یادته اولین بار که همدیگه رو دیدیم چقدر استرس داشتم؟ 😄",
    "چشمات قشنگ‌ترین چیز دنیاست ✨",
    "مرسی که همیشه هستی و حالمو خوب می‌کنی 🥰",
    "دوستت دارم، بیشتر از دیروز و کمتر از فردا!"
]

def get_mood_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("خسته‌م 😔", callback_data="mood_tired"),
        types.InlineKeyboardButton("دلتنگتم ", callback_data="mood_miss"),
        types.InlineKeyboardButton("خوشحالم ", callback_data="mood_happy"),
        types.InlineKeyboardButton("یه چیز بامزه بگو 😂", callback_data="mood_funny")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    name = message.from_user.first_name
    bot.reply_to(
        message,
        f"سلام {name} جان! 👋❤️\n"
        f"این ربات فقط برای تو ساخته شده تا هر وقت خواستی حال دلت رو بگی یا یه لبخند روی لبت بیاد.\n"
        f"یکی از دکمه‌های پایین رو انتخاب کن 👇",
        reply_markup=get_mood_keyboard()
    )

@bot.message_handler(commands=['love'])
def send_random_love(message):
    msg = random.choice(love_messages)
    bot.reply_to(message, f"💌 پیام مخصوص تو:\n\n{msg}")

@bot.callback_query_handler(func=lambda call: True)
def handle_mood(call):
    chat_id = call.message.chat.id
    
    if call.data == "mood_tired":
        response = "زود برو استراحت کن عزیزم. تو امروز خیلی زحمت کشیدی. یه چای یا قهوه برای خودت بریز ☕️💖"
    elif call.data == "mood_miss":
        response = "منم همینطور! کاش الان پیشت بودم و محکم بغلت می‌کردم. زود می‌بینمت ❤️"
    elif call.data == "mood_happy":
        response = "خندیدن تو، دنیای منو قشنگ می‌کنه. همیشه همینطور بخند 😍🌟"
    elif call.data == "mood_funny":
        response = "می‌دونی چرا برنامه‌نویسا عینک می‌زنن؟ چون نمی‌تونن C# (سی‌شارپ) کنن! 😂 (ببخشید بد بود ولی خندیدی دیگه!)"
    
    bot.edit_message_text(
        text=response,
        chat_id=chat_id,
        message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id)

# --- اضافه کردن Flask برای باز نگه داشتن پورت در Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ ربات عشق در حال اجراست! ❤️"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

print("✅ ربات عشق در حال اجراست...")
bot.infinity_polling(drop_pending_updates=True, timeout=60)
