import os
import time
import telebot
import requests
import schedule
import threading
from flask import Flask

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("خطا: TELEGRAM_BOT_TOKEN تنظیم نشده!")

bot = telebot.TeleBot(TOKEN)

# فایل ذخیره کاربران
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

# دریافت قیمت از نوبیتکس
def get_price(pair):
    try:
        response = requests.get(f"https://api.nobitex.ir/v3/orderbook/{pair}", timeout=10)
        data = response.json()
        if "lastTradePrice" in data:
            return int(data["lastTradePrice"]) // 10
        return None
    except Exception as e:
        print(f"خطا در نوبیتکس ({pair}): {e}")
        return None

# ساخت پیام قیمت (دلار، یورو، پوند)
def build_price_message():
    usd = get_price("USDTIRT")
    eur = get_price("EURIRT")
    gbp = get_price("GBPIRT")

    message = "💵 *قیمت لحظه‌ای ارزها (بازار آزاد)*\n"
    message += "━━━━━━━━━━━━━━━━━━\n"
    message += f"🕒 {time.strftime('%Y-%m-%d %H:%M')}\n"
    message += "━━━━━━━━━━━━━━━━━━\n\n"

    message += f"🇺 *دلار (تتر)*\n   💰 {usd:,} تومان\n\n" if usd else "🇸 *دلار*: ⚠️ خطا\n\n"
    message += f"🇪🇺 *یورو*\n   💰 {eur:,} تومان\n\n" if eur else "🇪🇺 *یورو*: ⚠️ خطا\n\n"
    message += f"🇬🇧 *پوند*\n   💰 {gbp:,} تومان\n\n" if gbp else "🇬🇧 *پوند*: ⚠️ خطا\n\n"

    message += "━━━━━━━━━━━━━━━━━━\n"
    message += "🤖 _به‌روزرسانی خودکار هر ۵ دقیقه_"
    return message

# ارسال خودکار به همه کاربران
def broadcast_price():
    message = build_price_message()
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

threading.Thread(target=run_scheduler, daemon=True).start()

# Flask برای Render
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ ربات در حال اجراست!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

# دستورات ربات
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_user(chat_id)
    price_msg = build_price_message()
    bot.reply_to(
        message,
        f"سلام {message.from_user.first_name}! 👋\n\n"
        f"✅ شما در لیست اطلاع‌رسانی قرار گرفتید.\n"
        f"هر ۵ دقیقه قیمت دلار، یورو و پوند برات ارسال می‌شه.\n\n"
        f"{price_msg}\n\n"
        f" دستورات:\n"
        f"/price - دریافت قیمت لحظه‌ای\n"
        f"/stop - لغو اطلاع‌رسانی",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['price'])
def get_price_now(message):
    msg = build_price_message()
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_updates(message):
    chat_id = message.chat.id
    remove_user(chat_id)
    bot.reply_to(message, "❌ اطلاع‌رسانی غیرفعال شد.\nبرای فعال‌سازی: /start")

print("✅ ربات ساده با نوبیتکس در حال اجراست...")
bot.infinity_polling(drop_pending_updates=True, timeout=60)
