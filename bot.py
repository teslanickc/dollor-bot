import os
import time
import telebot
import requests
import schedule
import threading
from flask import Flask

# دریافت توکن فقط از متغیرهای محیطی
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("خطا: متغیر TELEGRAM_BOT_TOKEN در سرور تنظیم نشده است!")

bot = telebot.TeleBot(TOKEN)

# ذخیره فایل در پوشه موقت (برای سازگاری با Docker)
USER_FILE = "/tmp/subscribed_users.txt"

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_user(chat_id):
    users = load_users()
    users.add(str(chat_id))
    with open(USER_FILE, "w") as f:
        for user in users:
            f.write(f"{user}\n")

def remove_user(chat_id):
    users = load_users()
    users.discard(str(chat_id))
    with open(USER_FILE, "w") as f:
        for user in users:
            f.write(f"{user}\n")

# دریافت قیمت دلار از API نوبیتکس (بازار آزاد)
def get_dollar_price():
    try:
        response = requests.get("https://api.nobitex.ir/v3/orderbook/USDTIRT", timeout=10)
        data = response.json()
        
        if "lastTradePrice" in data:
            price_rial = int(data["lastTradePrice"])
            price_toman = price_rial // 10
            return f"{price_toman:,} تومان"
        else:
            return "⚠️ خطا در دریافت قیمت"
    except Exception as e:
        print(f"خطا در نوبیتکس: {e}")
        try:
            # API جایگزین: تترلند
            response2 = requests.get("https://api.tetherland.com/currencies", timeout=10)
            data2 = response2.json()
            price = data2["data"]["currencies"]["USDT"]["price"]
            return f"{int(price):,} تومان"
        except Exception as e2:
            print(f"خطا در تترلند: {e2}")
            return "⚠️ خطا در اتصال. لطفاً دقایقی دیگر تلاش کنید."

# ارسال قیمت به همه کاربران
def broadcast_price():
    price = get_dollar_price()
    message = f"💵 *قیمت لحظه‌ای دلار*\n\n🔹 {price}\n\n🤖 _هر ۵ دقیقه به‌روزرسانی می‌شود._"
    
    users = load_users()
    for chat_id in users:
        try:
            bot.send_message(chat_id, message, parse_mode="Markdown")
        except Exception as e:
            print(f"خطا در ارسال به {chat_id}: {e}")
            remove_user(chat_id)

# زمان‌بندی هر ۵ دقیقه
schedule.every(5).minutes.do(broadcast_price)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# شروع زمان‌بند در پس‌زمینه
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# ← اضافه کردن Flask برای باز نگه داشتن پورت (مخصوص Render)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ ربات قیمت دلار در حال اجراست!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

# شروع Flask در یک ترد جداگانه
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# دستور /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_user(chat_id)
    price = get_dollar_price()
    bot.reply_to(
        message, 
        f"سلام {message.from_user.first_name}! 👋\n"
        f"✅ شما در لیست اطلاع‌رسانی قرار گرفتید.\n"
        f"هر ۵ دقیقه قیمت دلار برای شما ارسال می‌شود.\n\n"
        f"💰 قیمت فعلی: *{price}*\n\n"
        f"برای لغو: /stop",
        parse_mode="Markdown"
    )

# دستور /stop
@bot.message_handler(commands=['stop'])
def stop_updates(message):
    chat_id = message.chat.id
    remove_user(chat_id)
    bot.reply_to(message, "❌ اطلاع‌رسانی غیرفعال شد.\nبرای فعال‌سازی مجدد: /start")

# دستور /price
@bot.message_handler(commands=['price'])
def get_price_now(message):
    price = get_dollar_price()
    bot.reply_to(message, f"💰 قیمت فعلی دلار: *{price}*", parse_mode="Markdown")

print("✅ ربات در حال اجراست...")
bot.infinity_polling()
