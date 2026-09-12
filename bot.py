import os
import time
import json
import telebot
import requests
import schedule
import threading
from flask import Flask
from telebot import types

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
# کلید Navasan را اینجا یا در Environment Variables رندر وارد کنید
NAVASAN_KEY = os.environ.get('NAVASAN_API_KEY', 'کلید_رایگان_خود_را_اینجا_بگذارید')

if not TOKEN:
    raise ValueError("خطا: TELEGRAM_BOT_TOKEN تنظیم نشده!")

bot = telebot.TeleBot(TOKEN)
PREFS_FILE = "/tmp/users_prefs.json"

# لیست کامل ارزها با کدهای مخصوص Navasan
AVAILABLE_CURRENCIES = [
    {"code": "usd", "flag": "🇺🇸", "name": "دلار آمریکا"},
    {"code": "eur", "flag": "🇪🇺", "name": "یورو"},
    {"code": "gbp", "flag": "🇧", "name": "پوند انگلیس"},
    {"code": "aed", "flag": "🇦🇪", "name": "درهم امارات"},
    {"code": "try", "flag": "🇹", "name": "لیر ترکیه"},
    {"code": "jpy", "flag": "🇯🇵", "name": "ین ژاپن (۱۰۰ ین)"},
    {"code": "cny", "flag": "🇨", "name": "یوان چین"},
    {"code": "chf", "flag": "🇨🇭", "name": "فرانک سوئیس"}
]

# --- مدیریت داده‌ها ---
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

# --- دریافت قیمت از Navasan ---
def fetch_navasan_data():
    try:
        # درخواست به API ناوسان
        response = requests.get(f"https://api.navasan.tech/latest/?api_key={NAVASAN_KEY}", timeout=10)
        data = response.json()
        if data.get("success"):
            return data.get("data", {})
        return None
    except Exception as e:
        print(f"خطا در Navasan: {e}")
        return None

# --- ساخت پیام ---
def build_price_message(selected_codes):
    market_data = fetch_navasan_data()
    
    message = "💵 *قیمت لحظه‌ای بازار آزاد*\n"
    message += "━━━━━━━━━━━━━━━━━━\n"
    if market_data and "usd" in market_data:
        message += f" {market_data['usd'].get('time', '')}\n"
    message += "━━━━━━━━━━━━━━━━━━\n\n"
    
    if not market_data:
        return "️ خطا در اتصال به سرور قیمت. لطفاً دقایقی دیگر تلاش کنید."

    for curr in AVAILABLE_CURRENCIES:
        if curr["code"] in selected_codes and curr["code"] in market_data:
            info = market_data[curr["code"]]
            price = info.get("price", 0)
            change = info.get("change", 0)
            
            # فرمت‌بندی تغییرات
            if change > 0:
                arrow = f" (+{change:,})"
            elif change < 0:
                arrow = f"📉 ({change:,})"
            else:
                arrow = "➖ (0)"
                
            message += f"{curr['flag']} *{curr['name']}*\n"
            message += f"   💰 {int(price):,} تومان {arrow}\n\n"
            
    message += "━━━━━━━━━━━━━━━━━━\n"
    message += "🤖 _تنظیمات: /settings_"
    return message

# --- کیبورد تنظیمات ---
def get_settings_keyboard(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    current_prefs = get_user_prefs(chat_id)
    
    for curr in AVAILABLE_CURRENCIES:
        is_selected = curr["code"] in current_prefs
        symbol = "✅" if is_selected else "⚪️"
        btn = types.InlineKeyboardButton(
            f"{symbol} {curr['flag']} {curr['name']}",
            callback_data=f"toggle_{curr['code']}"
        )
        markup.add(btn)
    markup.add(types.InlineKeyboardButton("🔒 بستن منو", callback_data="close_menu"))
    return markup

# --- ارسال خودکار ---
def broadcast_price():
    prefs = load_prefs()
    for chat_id, selected_codes in prefs.items():
        if not selected_codes: continue
        message = build_price_message(selected_codes)
        try:
            bot.send_message(chat_id, message, parse_mode="Markdown")
        except Exception as e:
            print(f"خطا در ارسال به {chat_id}: {e}")
            del prefs[chat_id]
            save_prefs(prefs)

schedule.every(5).minutes.do(broadcast_price)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_scheduler, daemon=True).start()

# --- Flask برای Render ---
app = Flask(__name__)
@app.route('/')
def home(): return "✅ ربات در حال اجراست!"
@app.route('/health')
def health(): return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

# --- دستورات تلگرام ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    get_user_prefs(chat_id)
    price_msg = build_price_message(get_user_prefs(chat_id))
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⚙️ تنظیمات ارزها"), types.KeyboardButton("💰 قیمت لحظه‌ای"))
    
    bot.reply_to(message, f"سلام {message.from_user.first_name}! 👋\n\n{price_msg}", 
                 parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['settings'])
def open_settings(message):
    bot.send_message(message.chat.id, "ارزهای مورد نظر خود را انتخاب کنید:", 
                     reply_markup=get_settings_keyboard(message.chat.id))

@bot.message_handler(commands=['price'])
def get_price_now(message):
    msg = build_price_message(get_user_prefs(message.chat.id))
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "️ تنظیمات ارزها")
def settings_btn(m): open_settings(m)

@bot.message_handler(func=lambda m: m.text == "💰 قیمت لحظه‌ای")
def price_btn(m): get_price_now(m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def handle_toggle(call):
    code = call.data.split('_')[1]
    toggle_currency(call.message.chat.id, code)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, 
                                  reply_markup=get_settings_keyboard(call.message.chat.id))
    bot.answer_callback_query(call.id, "ذخیره شد ✅")

@bot.callback_query_handler(func=lambda call: call.data == 'close_menu')
def close_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

print("✅ ربات با API ناوسان آماده است...")
bot.infinity_polling()
