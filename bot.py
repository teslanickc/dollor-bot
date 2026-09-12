import os
import time
import json
import telebot
import requests
import schedule
import threading
from flask import Flask
from telebot import types

# دریافت توکن‌ها
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ALANCHAND_TOKEN = os.environ.get('ALANCHAND_API_TOKEN', 'توکن_آلن_چند_خودت')

if not TOKEN:
    raise ValueError("خطا: TELEGRAM_BOT_TOKEN تنظیم نشده!")

bot = telebot.TeleBot(TOKEN)

# فایل ذخیره‌سازی ترجیحات کاربران (JSON)
PREFS_FILE = "/tmp/users_prefs.json"

# لیست ارزهای موجود در API آلن‌چند
AVAILABLE_CURRENCIES = [
    {"code": "usd", "flag": "🇺🇸", "name": "دلار آمریکا"},
    {"code": "eur", "flag": "🇪🇺", "name": "یورو"},
    {"code": "aed", "flag": "🇪", "name": "درهم امارات"},
    {"code": "try", "flag": "🇹🇷", "name": "لیر ترکیه"},
    {"code": "gbp", "flag": "🇬🇧", "name": "پوند انگلیس"},
    {"code": "jpy", "flag": "🇯🇵", "name": "ین ژاپن"},
    {"code": "cny", "flag": "🇨🇳", "name": "یوان چین"},
    {"code": "chf", "flag": "🇨🇭", "name": "فرانک سوئیس"}
]

# --- توابع مدیریت داده‌ها ---
def load_prefs():
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_prefs(data):
    with open(PREFS_FILE, "w") as f:
        json.dump(data, f)

def get_user_prefs(chat_id):
    prefs = load_prefs()
    cid = str(chat_id)
    if cid not in prefs:
        # پیش‌فرض: فقط دلار برای کاربران جدید
        prefs[cid] = ["usd"] 
        save_prefs(prefs)
    return prefs[cid]

def toggle_currency(chat_id, code):
    prefs = load_prefs()
    cid = str(chat_id)
    user_prefs = prefs.get(cid, ["usd"])
    
    if code in user_prefs:
        user_prefs.remove(code)
    else:
        user_prefs.append(code)
        
    prefs[cid] = user_prefs
    save_prefs(prefs)
    return user_prefs

# --- تابع دریافت و ساخت پیام قیمت ---
def build_price_message(selected_codes):
    try:
        headers = {'Authorization': f'Bearer {ALANCHAND_TOKEN}'}
        symbols = ",".join(selected_codes)
        response = requests.get(
            f"https://api.alanchand.com?type=currency&symbols={symbols}",
            headers=headers, timeout=10
        )
        data = response.json()
        
        if not data:
            return "⚠️ خطا در دریافت اطلاعات"

        message = "💵 *قیمت لحظه‌ای ارزهای انتخابی شما*\n"
        message += "━━━━━━━━━━━━━━━━━━\n"
        
        if "usd" in data and data["usd"].get("updated_at"):
            message += f"🕒 {data['usd']['updated_at']}\n"
        message += "━━━━━━━━━━━━━━━━━━\n\n"
        
        for curr in AVAILABLE_CURRENCIES:
            if curr["code"] in selected_codes and curr["code"] in data:
                info = data[curr["code"]]
                sell = info.get("sell", 0)
                buy = info.get("buy", 0)
                change = info.get("dayChange", 0)
                
                arrow = "" if change > 0 else ("📉" if change < 0 else "➖")
                
                message += f"{curr['flag']} *{curr['name']}*\n"
                message += f"   💰 فروش: {sell:,} | خرید: {buy:,} {arrow}\n\n"
                
        message += "━━━━━━━━━━━━━━━━━━\n"
        message += "🤖 _تنظیمات: /settings_"
        return message

    except Exception as e:
        print(f"خطا در API: {e}")
        return "⚠️ خطا در اتصال به سرور قیمت."

# --- ساخت کیبورد تنظیمات ---
def get_settings_keyboard(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    current_prefs = get_user_prefs(chat_id)
    
    for curr in AVAILABLE_CURRENCIES:
        is_selected = curr["code"] in current_prefs
        symbol = "✅" if is_selected else "⚪️"
        btn = types.InlineKeyboardButton(
            f"{symbol} {curr['flag']} {curr['name']}",
            callback_data=f"toggle_{curr['code']}"
        )
        markup.add(btn)
        
    markup.add(types.InlineKeyboardButton("✅ بستن منو", callback_data="close_menu"))
    return markup

# --- ارسال خودکار (Broadcast) ---
def broadcast_price():
    prefs = load_prefs()
    for chat_id, selected_codes in prefs.items():
        if not selected_codes:
            continue # اگر کاربر هیچ ارزی انتخاب نکرده، پیامی نفرست
            
        message = build_price_message(selected_codes)
        try:
            bot.send_message(chat_id, message, parse_mode="Markdown")
        except Exception as e:
            print(f"خطا در ارسال به {chat_id}: {e}")
            # اگر کاربر ربات را بلاک کرده باشد، از لیست حذف می‌شود
            del prefs[chat_id]
            save_prefs(prefs)

# زمان‌بندی هر ۵ دقیقه
schedule.every(5).minutes.do(broadcast_price)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# --- Flask برای Render ---
app = Flask(__name__)
@app.route('/')
def home(): return "✅ ربات در حال اجراست!"
@app.route('/health')
def health(): return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# --- هندلرهای دستورات تلگرام ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    get_user_prefs(chat_id) # ایجاد تنظیمات پیش‌فرض
    price_msg = build_price_message(get_user_prefs(chat_id))
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⚙️ تنظیمات ارزها"), types.KeyboardButton("💰 قیمت لحظه‌ای"))
    
    bot.reply_to(
        message,
        f"سلام {message.from_user.first_name}! 👋\n\n"
        f"من قیمت ارزهایی که انتخاب کنی رو هر ۵ دقیقه برات می‌فرستم.\n"
        f"برای تغییر ارزها، دکمه 'تنظیمات' رو بزن.\n\n"
        f"{price_msg}",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(commands=['settings'])
def open_settings(message):
    bot.send_message(
        message.chat.id, 
        "لطفاً ارزهای مورد نظر خود را انتخاب کنید:\n(برای حذف، دوباره روی آن بزنید)",
        reply_markup=get_settings_keyboard(message.chat.id)
    )

@bot.message_handler(commands=['price'])
def get_price_now(message):
    prefs = get_user_prefs(message.chat.id)
    msg = build_price_message(prefs)
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "️ تنظیمات ارزها")
def settings_btn(message):
    open_settings(message)

@bot.message_handler(func=lambda message: message.text == "💰 قیمت لحظه‌ای")
def price_btn(message):
    get_price_now(message)

# --- هندلر دکمه‌های شیشه‌ای (Inline) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def handle_toggle(call):
    code = call.data.split('_')[1]
    chat_id = call.message.chat.id
    
    # تغییر وضعیت در دیتابیس
    toggle_currency(chat_id, code)
    
    # آپدیت کردن منوی دکمه‌ها بدون ارسال پیام جدید
    bot.edit_message_reply_markup(
        chat_id,
        call.message.message_id,
        reply_markup=get_settings_keyboard(chat_id)
    )
    bot.answer_callback_query(call.id, "تنظیمات ذخیره شد ✅")

@bot.callback_query_handler(func=lambda call: call.data == 'close_menu')
def close_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

print("✅ ربات با قابلیت انتخاب ارز در حال اجراست...")
bot.infinity_polling()
