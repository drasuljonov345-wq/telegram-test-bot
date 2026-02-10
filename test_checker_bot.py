import telebot
from telebot import types
import json
import os
from flask import Flask
from threading import Thread

# Bot tokeningizni shu yerga qo'ying
BOT_TOKEN = "8429569333:AAG0r_lWgsOMqxIB63DJMFr8tL34JJ9NN2A"

bot = telebot.TeleBot(BOT_TOKEN)

# Ma'lumotlarni saqlash uchun
DATA_FILE = "bot_data.json"

# Ma'lumotlar strukturasi
data = {
    "admin_id": None,      # Admin ID shu yerga saqlanadi
    "test_file_id": None,  # Test savollari fayl ID
    "answers": [],         # To'g'ri javoblar (kalitlar)
    "test_count": 0,       # Testlar soni
    "students": {}         # O'quvchilar javoblari
}

# Ma'lumotlarni yuklash
def load_data():
    global data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

# Ma'lumotlarni saqlash
def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Boshlang'ich ma'lumotlarni yuklash
load_data()

# /start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if data["admin_id"] is None:
        # Birinchi foydalanuvchi admin bo'ladi
        data["admin_id"] = user_id
        save_data()
        markup.add("📝 Test savollarini yuklash", "🔑 Kalitlarni yuklash")
        markup.add("📊 Natijalarni ko'rish", "🗑 Ma'lumotlarni tozalash")
        bot.send_message(message.chat.id, 
                        f"Assalomu alaykum! Siz admin sifatida ro'yxatdan o'tdingiz.\n\n"
                        f"Sizning ID: {user_id}", 
                        reply_markup=markup)
    elif user_id == data["admin_id"]:
        markup.add("📝 Test savollarini yuklash", "🔑 Kalitlarni yuklash")
        markup.add("📊 Natijalarni ko'rish", "🗑 Ma'lumotlarni tozalash")
        bot.send_message(message.chat.id, 
                        "Xush kelibsiz, Admin!", 
                        reply_markup=markup)
    else:
        markup.add("📥 Testni olish", "📤 Javoblarni yuborish")
        bot.send_message(message.chat.id, 
                        f"Assalomu alaykum! Test ishlash uchun quyidagi tartibda harakat qiling:\n\n"
                        f"1️⃣ Avval '📥 Testni olish' tugmasini bosing\n"
                        f"2️⃣ Test savollarini ko'ring va ishlang\n"
                        f"3️⃣ Keyin '📤 Javoblarni yuborish' tugmasini bosing\n\n"
                        f"Javoblaringizni quyidagi formatda yuboring:\n"
                        f"Ism Familiya\n"
                        f"ABCDABCD...", 
                        reply_markup=markup)

# Admin test savollarini yuklash
@bot.message_handler(func=lambda message: message.text == "📝 Test savollarini yuklash" and message.from_user.id == data.get("admin_id"))
def upload_test(message):
    bot.send_message(message.chat.id, 
                    "Test savollarini PDF, rasm (JPG/PNG) yoki dokument shaklida yuboring.\n\n"
                    "Bir nechta rasm bo'lsa, hammasini bitta xabarda yuboring.")
    bot.register_next_step_handler(message, process_test_file)

def process_test_file(message):
    # Rasmlar
    if message.photo:
        file_id = message.photo[-1].file_id  # Eng katta o'lchamdagi rasmni olish
        data["test_file_id"] = file_id
        save_data()
        bot.send_message(message.chat.id, 
                        f"✅ Test savollari (rasm) saqlandi!\n\n"
                        f"Endi kalitlarni yuklang: 🔑 Kalitlarni yuklash")
    # PDF yoki dokument
    elif message.document:
        file_id = message.document.file_id
        data["test_file_id"] = file_id
        save_data()
        bot.send_message(message.chat.id, 
                        f"✅ Test savollari (fayl) saqlandi!\n\n"
                        f"Endi kalitlarni yuklang: 🔑 Kalitlarni yuklash")
    else:
        bot.send_message(message.chat.id, 
                        "❌ Iltimos, rasm yoki PDF fayl yuboring!")

# Admin kalitlarni yuklash
@bot.message_handler(func=lambda message: message.text == "🔑 Kalitlarni yuklash" and message.from_user.id == data.get("admin_id"))
def upload_keys(message):
    if not data.get("test_file_id"):
        bot.send_message(message.chat.id, 
                        "⚠️ Avval test savollarini yuklang!\n"
                        "📝 Test savollarini yuklash tugmasini bosing.")
        return
    
    bot.send_message(message.chat.id, 
                    "To'g'ri javoblarni (kalitlarni) yuboring.\n\n"
                    "Format: ABCDABCDABCD...\n"
                    "Misol: ABCDABCDA (10 ta test uchun)")
    bot.register_next_step_handler(message, process_keys)

def process_keys(message):
    answers = message.text.strip().upper()
    
    # Faqat A, B, C, D harflari borligini tekshirish
    if not all(c in 'ABCD' for c in answers):
        bot.send_message(message.chat.id, 
                        "❌ Xato! Faqat A, B, C, D harflarini kiriting.")
        return
    
    data["answers"] = list(answers)
    data["test_count"] = len(answers)
    data["students"] = {}  # Yangi kalitlar kelganda o'quvchilarni tozalash
    save_data()
    
    bot.send_message(message.chat.id, 
                    f"✅ Kalitlar saqlandi!\n"
                    f"Testlar soni: {data['test_count']}\n"
                    f"Kalitlar: {answers}")

# O'quvchi test savollarini olish
@bot.message_handler(func=lambda message: message.text == "📥 Testni olish")
def get_test(message):
    if not data.get("test_file_id"):
        bot.send_message(message.chat.id, 
                        "❌ Hozircha test yuklanmagan. Admin bilan bog'laning.")
        return
    
    if not data.get("answers"):
        bot.send_message(message.chat.id, 
                        "❌ Test kalitlari hali yuklanmagan. Admin bilan bog'laning.")
        return
    
    # Test savollarini yuborish
    try:
        bot.send_message(message.chat.id, 
                        f"📝 Test savollari:\n"
                        f"Jami testlar soni: {data['test_count']}\n\n"
                        f"Testni ishlang va '📤 Javoblarni yuborish' tugmasini bosing!")
        
        # Fayl yuborish
        bot.send_document(message.chat.id, data["test_file_id"])
    except:
        # Agar dokument bo'lmasa, rasm deb yuborish
        try:
            bot.send_photo(message.chat.id, data["test_file_id"])
        except:
            bot.send_message(message.chat.id, 
                            "❌ Xatolik yuz berdi. Admin bilan bog'laning.")

# O'quvchi javoblarini yuborish
@bot.message_handler(func=lambda message: message.text == "📤 Javoblarni yuborish")
def submit_answers(message):
    if data["test_count"] == 0:
        bot.send_message(message.chat.id, 
                        "❌ Hozircha test kalitlari yuklanmagan. Admin bilan bog'laning.")
        return
    
    bot.send_message(message.chat.id, 
                    f"Ismingiz va javoblaringizni yuboring.\n\n"
                    f"Format:\n"
                    f"Ism Familiya\n"
                    f"ABCDABCD...\n\n"
                    f"Testlar soni: {data['test_count']}")
    bot.register_next_step_handler(message, process_student_answers)

def process_student_answers(message):
    try:
        lines = message.text.strip().split('\n')
        if len(lines) < 2:
            bot.send_message(message.chat.id, 
                            "❌ Xato format! Birinchi qatorda ismingiz, ikkinchi qatorda javoblaringiz bo'lishi kerak.")
            return
        
        student_name = lines[0].strip()
        student_answers = lines[1].strip().upper()
        
        # Faqat A, B, C, D harflari borligini tekshirish
        if not all(c in 'ABCD' for c in student_answers):
            bot.send_message(message.chat.id, 
                            "❌ Xato! Javoblarda faqat A, B, C, D harflarini kiriting.")
            return
        
        if len(student_answers) != data["test_count"]:
            bot.send_message(message.chat.id, 
                            f"❌ Xato! Siz {len(student_answers)} ta javob yubordingiz, "
                            f"lekin {data['test_count']} ta javob kerak.")
            return
        
        # Javoblarni tekshirish
        correct = 0
        for i in range(len(student_answers)):
            if student_answers[i] == data["answers"][i]:
                correct += 1
        
        # O'quvchi ma'lumotlarini saqlash
        data["students"][student_name] = {
            "answers": list(student_answers),
            "correct": correct,
            "total": data["test_count"]
        }
        save_data()
        
        bot.send_message(message.chat.id, 
                        f"✅ Javoblaringiz qabul qilindi!\n\n"
                        f"👤 {student_name}\n"
                        f"✔️ To'g'ri javoblar: {correct}/{data['test_count']}\n"
                        f"📊 Natija: {(correct/data['test_count']*100):.1f}%")
        
        # Adminni xabardor qilish
        if data["admin_id"]:
            bot.send_message(data["admin_id"], 
                            f"🆕 Yangi javob qabul qilindi!\n\n"
                            f"👤 {student_name}\n"
                            f"✔️ {correct}/{data['test_count']}")
        
    except Exception as e:
        bot.send_message(message.chat.id, 
                        f"❌ Xatolik yuz berdi: {str(e)}")

# Natijalarni ko'rish (Admin uchun)
@bot.message_handler(func=lambda message: message.text == "📊 Natijalarni ko'rish" and message.from_user.id == data.get("admin_id"))
def view_results(message):
    if not data["students"]:
        bot.send_message(message.chat.id, 
                        "Hozircha hech kim javob yubormagan.")
        return
    
    result_text = f"📊 TEST NATIJALARI\n"
    result_text += f"Jami testlar soni: {data['test_count']}\n"
    result_text += f"Ishtirokchilar: {len(data['students'])}\n"
    result_text += "=" * 40 + "\n\n"
    
    # O'quvchilarni natijalar bo'yicha saralash
    sorted_students = sorted(data["students"].items(), 
                           key=lambda x: x[1]["correct"], 
                           reverse=True)
    
    for i, (name, info) in enumerate(sorted_students, 1):
        percentage = (info["correct"] / info["total"] * 100)
        result_text += f"{i}. {name}\n"
        result_text += f"   ✔️ {info['correct']}/{info['total']} ({percentage:.1f}%)\n\n"
    
    # Agar matn juda uzun bo'lsa, faylga yozish
    if len(result_text) > 4000:
        with open("natijalar.txt", "w", encoding="utf-8") as f:
            f.write(result_text)
        with open("natijalar.txt", "rb") as f:
            bot.send_document(message.chat.id, f, caption="📊 Test natijalari")
        os.remove("natijalar.txt")
    else:
        bot.send_message(message.chat.id, result_text)

# Ma'lumotlarni tozalash (Admin uchun)
@bot.message_handler(func=lambda message: message.text == "🗑 Ma'lumotlarni tozalash" and message.from_user.id == data.get("admin_id"))
def clear_data(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Ha, tozalash", callback_data="clear_yes"))
    markup.add(types.InlineKeyboardButton("❌ Yo'q, bekor qilish", callback_data="clear_no"))
    
    bot.send_message(message.chat.id, 
                    "⚠️ Barcha o'quvchilar javoblarini o'chirmoqchimisiz?\n"
                    "Kalitlar saqlanib qoladi.",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["clear_yes", "clear_no"])
def callback_clear(call):
    if call.data == "clear_yes":
        data["students"] = {}
        save_data()
        bot.edit_message_text("✅ O'quvchilar javoblari o'chirildi!", 
                            call.message.chat.id, 
                            call.message.message_id)
    else:
        bot.edit_message_text("❌ Bekor qilindi.", 
                            call.message.chat.id, 
                            call.message.message_id)

# Oddiy xabarlarni qabul qilish
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.send_message(message.chat.id, 
                    "Iltimos, tugmalardan foydalaning yoki /start bosing.")

# Flask app (Render uchun port ochish)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti! ✅"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    """Bot ishga tushirish funktsiyasi"""
    import time
    while True:
        try:
            print("Bot ishga tushmoqda...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Bot xatolik: {e}")
            print("5 soniyadan keyin qayta urinish...")
            time.sleep(5)

# Botni ishga tushirish
if __name__ == '__main__':
    # Portni olish
    port = int(os.environ.get('PORT', 10000))
    
    print(f"Flask server porti: {port}")
    
    # Botni alohida threadda ishga tushirish
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print("Bot thread ishga tushdi")
    
    # Flask serverni ishga tushirish (Render uchun)
    # Bu ASOSIY thread - port shu yerda ochiladi
    app.run(host='0.0.0.0', port=port, debug=False)
