import os
import telebot
import threading
from flask import Flask
from telebot import types

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    print("❌ خطا: توکن پیدا نشد!")
else:
    print("✅ توکن با موفقیت خوانده شد.")

bot = telebot.TeleBot(TOKEN)

# ساخت دکمه‌های شیشه‌ای با حالت‌های جدید
def get_mood_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("دلتنگتم 🥺", callback_data="mood_miss"),
        types.InlineKeyboardButton("خسته‌م 😔", callback_data="mood_tired"),
        types.InlineKeyboardButton("خوشحالم 😄", callback_data="mood_happy"),
        types.InlineKeyboardButton("غمگینم 💔", callback_data="mood_sad")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    name = message.from_user.first_name
    bot.reply_to(
        message,
        f"سلام {name} جانِ من! 👋❤️\n"
        f"این ربات فقط برای تو ساخته شده تا هر وقت خواستی حال دلت رو بگی، من اینجام.\n"
        f"یکی از دکمه‌های پایین رو انتخاب کن 👇",
        reply_markup=get_mood_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_mood(call):
    chat_id = call.message.chat.id
    response = ""
    
    if call.data == "mood_miss":
        response = "یادته اولین قرارمون؟ اولین باری که دستتو گرفتم، همونجا دلم برات لرزید... ❤️"
        
    elif call.data == "mood_tired":
        response = "می‌دونم روز خسته‌کننده‌ای بوده عشقم. من اینجام، پیشتم. هر وقت خواستی فقط کافیه یه زنگ بهم بزنی. 🫂☕️"
        
    elif call.data == "mood_happy":
        response = "یادته لازانیایی که اون شب خونه ما درست کردی؟ من هر وقت به اون فکر می‌کنم، خوشحال می‌شم. 😍🍝"
        
    elif call.data == "mood_sad":
        response = "هر وقت غمگین می‌شم پانیذ جان، به این فکر می‌کنم که ما با هم ۱۷، ۱۸ سالگی اون جنگ و همه اون بدبختی‌ها رو گذروندیم. پس انقدر رابطه‌مون قویه که می‌تونیم با هم به هر چی می‌خوایم برسیم. 💪❤️"
    
    # آپدیت کردن پیام قبلی با پیام جدید
    bot.edit_message_text(
        text=response,
        chat_id=chat_id,
        message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id)

# --- بخش Flask برای بیدار نگه داشتن رندر ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ ربات عشق پانیذ در حال اجراست! ❤️"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

# اجرای فلask در یک ترد جداگانه
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# اجرای ربات (بدون هیچ فاصله اضافی در ابتدای خط)
print("🚀 ربات در حال اجراست...")
bot.infinity_polling(timeout=60)
