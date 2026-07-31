import os
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# ==================== 1. إعدادات البوت والقناة ====================
BOT_TOKEN = "8921454803:AAERzszqcJINxuOL4Bj5clYNR5IplE1HUDI"
CHANNEL_ID = "@wanasatt"  # معرف قناتك
CHANNEL_URL = "https://t.me/wanasatt"  # رابط قناتك
PROXY_URL = ""  # اختياري: ضعه إن كان لديك بروكسي (e.g. "http://user:pass@ip:port")

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== 2. خادم خفيف لإبقاء البوت مستيقظاً 24/7 ====================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==================== 3. فحص الاشتراك الإجباري ====================
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"❌ خطأ أثناء فحص الاشتراك: {e}")
        # في حال وجود خطأ يتيح للمستخدم المرور لكي لا يتوقف البوت عن الرد
        return True

def send_subscription_message(chat_id):
    markup = InlineKeyboardMarkup()
    btn_channel = InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_URL)
    btn_confirm = InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="check_sub")
    markup.add(btn_channel)
    markup.add(btn_confirm)
    
    bot.send_message(
        chat_id,
        "⚠️ عذراً عزيزي!\n\nيجب عليك الاشتراك في قناة البوت الرسمية لاستخدام الخدمة.",
        reply_markup=markup
    )

# ==================== 4. معالجة الأوامر والرسائل ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    print(f"📩 استلمت أمر /start من المستخدم: {message.from_user.id}")
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        send_subscription_message(message.chat.id)
        return
    
    bot.reply_to(
        message,
        "👋 أهلاً بك في بوت التحميل الشامل (@VideoHubDownloader_bot)!\n\n"
        "أرسل لي رابط الفيديو من أي منصة (يوتيوب، تيك توك، إنستغرام، إلخ) وسأقوم بتحميله لك مباشرة."
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ تم التأكد، يمكنك الآن استخدام البوت!")
        bot.send_message(call.message.chat.id, "أرسل لي رابط الفيديو الآن 🚀")
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك بعد! يرجى الانضمام للقناة أولاً.", show_alert=True)

# ==================== 5. معالجة روابط الفيديو ====================
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith(("http://", "https://")))
def handle_download(message):
    user_id = message.from_user.id
    url = message.text.strip()
    print(f"🔗 استلمت رابط للتحميل: {url}")

    if not is_subscribed(user_id):
        send_subscription_message(message.chat.id)
        return

    status_msg = bot.reply_to(message, "⏳ جاري معالجة الرابط وتجاوز قيود التحميل...")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = 'cookies.txt'

    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL

    try:
        os.makedirs("downloads", exist_ok=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            title = info.get('title', 'فيديو')

        bot.edit_message_text("⬆️ جاري رفع الفيديو إلى تلغرام...", message.chat.id, status_msg.message_id)

        markup = InlineKeyboardMarkup()
        btn_channel = InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_URL)
        markup.add(btn_channel)

        with open(file_path, 'rb') as video_file:
            bot.send_video(
                message.chat.id,
                video_file,
                caption=f"🎬 {title}\n\n🤖 تم التحميل بواسطة @VideoHubDownloader_bot",
                reply_markup=markup
            )

        if os.path.exists(file_path):
            os.remove(file_path)
        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        print(f"❌ Download Error: {e}")
        bot.edit_message_text(
            "❌ حدث خطأ أثناء تحميل الفيديو.\n"
            "تأكد من صحة الرابط أو حاول مجدداً لاحقاً.",
            message.chat.id,
            status_msg.message_id
        )

# ==================== 6. تشغيل السيرفر والبوت ====================
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("🚀 Bot starting polling...")
    bot.infinity_polling(skip_pending=True)
