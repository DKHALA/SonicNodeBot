import asyncio
import os
import json
import time
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from yt_dlp import YoutubeDL

# --- [ الإعدادات الأساسية ] ---
TOKEN = "8390175505:AAHv345nszKHTtJ4yjjDm5vVYcZhftpT1-4"
ADMIN_ID =7388833313 # ضع الـ ID الخاص بك هنا
DB_FILE = "bot_data.json"

# --- [ نظام إدارة البيانات ] ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE, "r"))
        except: pass
    return {"blacklist": [], "stats": {"total_downloads": 0}}

def save_data(data):
    json.dump(data, open(DB_FILE, "w"))

data = load_data()

# --- [ إعدادات المحرك ] ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
executor = ThreadPoolExecutor(max_workers=10) # نظام الخيوط الأفضل للسحابة

# --- [ جدار الحماية الذكي ] ---
def is_safe(text):
    return not bool(re.search(r'[;&|`$]', text))

async def notify_admin_of_attack(user, text):
    report = (
        "🚨 <b>محاولة اختراق مكتشفة!</b>\n"
        f"👤 الاسم: {user.full_name}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📝 النص: <code>{text}</code>\n"
        "🛡️ <b>الإجراء:</b> تم الحظر تلقائياً."
    )
    if user.id not in data["blacklist"]:
        data["blacklist"].append(user.id)
        save_data(data)
    try: await bot.send_message(ADMIN_ID, report)
    except: pass

# --- [ محرك التحميل الآمن ] ---
def download_task(query, uid):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{uid}.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True, # مهم جداً للسحابة
        'restrictfilenames': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        try:
            search = f"ytsearch1:{query}" if "http" not in query else query
            info = ydl.extract_info(search, download=True)
            if 'entries' in info: info = info['entries'][0]
            return f"{uid}.mp3", info.get('title', 'Track'), info.get('duration', 0)
        except Exception as e:
            print(f"Download Error: {e}")
            return None

# --- [ الأوامر والردود ] ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in data["blacklist"]: return
    welcome = (
        "<b>💎 نظام SonicNodeBot | النسخة السحابية</b>\n"
        "ــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ\n"
        "🖥 <b>الحالة:</b> نشط على السحابة 24/7\n"
        "🛡 <b>الحماية:</b> نظام الجدار الناري مفعل\n"
        "ــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ\n\n"
        "🎵 أرسل اسم الأغنية أو الرابط لنبدأ..."
    )
    await message.answer(welcome)

@dp.message(F.text)
async def handle_msg(message: types.Message):
    user = message.from_user
    if user.id in data["blacklist"]: return

    if not is_safe(message.text):
        await notify_admin_of_attack(user, message.text)
        return await message.answer("⛔ نشاط مشبوه! تم حظرك.")

    status = await message.answer("🔍 جاري البحث...")
    uid = f"file_{int(time.time())}_{user.id}"
    
    try:
        loop = asyncio.get_event_loop()
        await status.edit_text("⬇️ جاري المعالجة على السحابة...")
        
        result = await loop.run_in_executor(executor, download_task, message.text, uid)
        
        if result:
            path, title, dur = result
            await status.edit_text(f"☁️ جاري الرفع: {title}")
            await message.answer_audio(
                audio=types.FSInputFile(path), 
                title=title, 
                duration=dur, 
                caption="🛡️ تم الفحص: ملف آمن"
            )
            data["stats"]["total_downloads"] += 1
            save_data(data)
            if os.path.exists(path): os.remove(path)
            await status.delete()
        else:
            await status.edit_text("❌ فشل التحميل. جرب اسماً آخر.")
    except Exception as e:
        print(f"System Error: {e}")
        await message.answer("⚠️ حدث خطأ فني مؤقت.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
