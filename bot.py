import os
import telebot
import threading
from flask import Flask
from telebot import types

# دریافت توکن از تنظیمات سرور
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    print("❌ خطا: توکن پیدا نشد! لطفاً Environment Variable را چک کنید.")
else:
    print("✅ توکن با موفقیت خوانده شد.")

bot = telebot.TeleBot(TOKEN)

# ساخت دکمه‌های شیشه‌ای
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
    try:
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
        
        # آپدیت کردن متن پیام
        bot.edit_message_text(
            text=response,
            chat_id=chat_id,
            message_id=call.message.message_id
        )
        # متوقف کردن حالت لودینگ دکمه
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        # جلوگیری از هنگ کردن ربات در صورت کلیک سریع یا خطای تلگرام
        print(f"خطای جزئی در دکمه: {e}")
        bot.answer_callback_query(call.id, text="صبر کن عزیزم...")

# --- بخش Flask برای بیدار نگه داشتن Render ---
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

# اجرای Flask در یک ترد جداگانه در پس‌زمینه
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# اجرای ربات (بهینه‌شده برای جلوگیری از کندی و مصرف کمتر منابع)
# ⚠️ مهم: این خط باید کاملاً به سمت چپ چسبیده باشد و هیچ فاصله‌ای قبل از آن نباشد
print("🚀 ربات در حال اجراست...")
bot.infinity_polling(timeout=60, allowed_updates=["message", "callback_query"])
