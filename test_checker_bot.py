"""
Test Tekshiruvchi Bot - Faqat O'qituvchi uchun
O'qituvchi kalit yuboradi, keyin talabalarning javob varaqlarini yuboradi
Bot har birini tekshirib natija beradi
"""

import telebot
from telebot import types
import json
import os
import re
from datetime import datetime
from PIL import Image
import pytesseract
import io

# Bot Token
BOT_TOKEN = "8429569333:AAG0r_lWgsOMqxIB63DJMFr8tL34JJ9NN2A"

# Admin ID - O'qituvchi
ADMIN_ID = 7244207532, 2002640746,  # Bu yerga o'z Telegram ID ni qo'ying

bot = telebot.TeleBot(BOT_TOKEN)

# Sessiya ma'lumotlari
session = {
    'answer_key': None,
    'total_questions': 0
}

def parse_answers(text):
    """
    Javoblarni parse qilish
    Format: 1A 2B 3C yoki 1)A 2)B 3)C yoki ABCDABC
    """
    answers = {}
    text = text.upper().strip()
    
    # Turli formatlarni qo'llab-quvvatlash
    patterns = [
        r'(\d+)\s*[).:\-]?\s*([A-E])',  # 1A, 1)A, 1.A, 1:A, 1-A
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            for match in matches:
                question_num = int(match[0])
                answer = match[1]
                answers[question_num] = answer
            if answers:
                return answers
    
    # Agar pattern topilmasa, faqat harflar: ABCDABC...
    letters = re.findall(r'[A-E]', text)
    if letters:
        for i, letter in enumerate(letters, 1):
            answers[i] = letter
    
    return answers

def extract_text_from_image(image_bytes):
    """Rasmdan matnni ajratib olish (OCR)"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang='eng')
        return text
    except Exception as e:
        print(f"OCR xatosi: {e}")
        return None

def check_answers(student_answers, answer_key):
    """Javoblarni tekshirish"""
    correct = 0
    wrong = 0
    empty = 0
    details = []
    
    total = len(answer_key)
    
    for question_num in sorted(answer_key.keys()):
        correct_answer = answer_key[question_num]
        student_answer = student_answers.get(question_num, '-')
        
        if student_answer == '-' or student_answer == '':
            empty += 1
            details.append(f"➖ {question_num}. Bo'sh (to'g'ri: {correct_answer})")
        elif student_answer == correct_answer:
            correct += 1
            details.append(f"✅ {question_num}. {student_answer}")
        else:
            wrong += 1
            details.append(f"❌ {question_num}. {student_answer} (to'g'ri: {correct_answer})")
    
    percentage = (correct / total * 100) if total > 0 else 0
    
    # Baho
    if percentage >= 90:
        grade = "A'lo (5)"
    elif percentage >= 70:
        grade = "Yaxshi (4)"
    elif percentage >= 50:
        grade = "Qoniqarli (3)"
    else:
        grade = "Qoniqarsiz (2)"
    
    return {
        'correct': correct,
        'wrong': wrong,
        'empty': empty,
        'total': total,
        'percentage': percentage,
        'grade': grade,
        'details': details
    }

# Start command
@bot.message_handler(commands=['start', 'help'])
def start(message):
    """Bot boshlanganda"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "⛔️ Kechirasiz, bu bot faqat o'qituvchi uchun!"
        )
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📝 Yangi kalit", "📋 Kalit ko'rish")
    markup.add("📊 Test tekshirish", "🗑 Kalitni o'chirish")
    markup.add("ℹ️ Qo'llanma")
    
    bot.send_message(
        message.chat.id,
        "🎓 Assalomu alaykum, O'qituvchi!\n\n"
        "🤖 Test Tekshiruvchi Bot\n\n"
        "📌 Qanday ishlaydi:\n"
        "1️⃣ Avval test kalitini yuklang\n"
        "2️⃣ Keyin talabalar javoblarini yuboring\n"
        "3️⃣ Bot har birini tekshiradi\n\n"
        "Boshlash uchun tugmalardan foydalaning:",
        reply_markup=markup
    )

# Yangi kalit
@bot.message_handler(func=lambda m: m.text == "📝 Yangi kalit")
def request_new_key(message):
    """Yangi kalit so'rash"""
    if message.from_user.id != ADMIN_ID:
        return
    
    msg = bot.send_message(
        message.chat.id,
        "📝 Test kalitini yuboring:\n\n"
        "📋 Qabul qilinadigan formatlar:\n\n"
        "1️⃣ Raqam bilan:\n"
        "   1A 2B 3C 4D 5A...\n"
        "   1)A 2)B 3)C 4)D...\n"
        "   1.A 2.B 3.C 4.D...\n\n"
        "2️⃣ Faqat harflar:\n"
        "   ABCDABCDABC...\n\n"
        "📌 Misol (20 savollik test):\n"
        "1A 2B 3C 4D 5A 6B 7C 8D 9A 10B 11C 12D 13A 14B 15C 16D 17A 18B 19C 20D"
    )
    bot.register_next_step_handler(msg, save_answer_key)

def save_answer_key(message):
    """Kalitni saqlash"""
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text
    answer_key = parse_answers(text)
    
    if not answer_key:
        bot.send_message(
            message.chat.id,
            "❌ Kalit formatida xato!\n\n"
            "To'g'ri formatda yuboring:\n"
            "1A 2B 3C 4D...\n\n"
            "Yoki '📝 Yangi kalit' tugmasini qayta bosing."
        )
        return
    
    # Sessiyaga saqlash
    session['answer_key'] = answer_key
    session['total_questions'] = len(answer_key)
    
    # Kalitni ko'rsatish
    key_preview = []
    for num in sorted(answer_key.keys())[:10]:
        key_preview.append(f"{num}.{answer_key[num]}")
    
    preview_text = " ".join(key_preview)
    if len(answer_key) > 10:
        preview_text += f" ... (va yana {len(answer_key)-10} ta)"
    
    bot.send_message(
        message.chat.id,
        f"✅ Test kaliti saqlandi!\n\n"
        f"📊 Jami savollar: {len(answer_key)}\n\n"
        f"🔑 Kalit:\n{preview_text}\n\n"
        f"📋 To'liq kalitni ko'rish: '📋 Kalit ko'rish'\n"
        f"📊 Test tekshirish: '📊 Test tekshirish'"
    )

# Kalitni ko'rish
@bot.message_handler(func=lambda m: m.text == "📋 Kalit ko'rish")
def view_key(message):
    """Hozirgi kalitni ko'rsatish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    if not session['answer_key']:
        bot.send_message(
            message.chat.id,
            "❌ Hozircha kalit yuklanmagan!\n\n"
            "Kalit yuklash uchun '📝 Yangi kalit' tugmasini bosing."
        )
        return
    
    answer_key = session['answer_key']
    
    # Kalitni satrlar bo'yicha ajratish (har satrda 10 ta)
    lines = []
    items = sorted(answer_key.items())
    
    for i in range(0, len(items), 10):
        chunk = items[i:i+10]
        line = " ".join([f"{num}.{ans}" for num, ans in chunk])
        lines.append(line)
    
    key_text = "\n".join(lines)
    
    bot.send_message(
        message.chat.id,
        f"📋 Hozirgi test kaliti:\n\n"
        f"📊 Jami savollar: {session['total_questions']}\n\n"
        f"🔑 Kalit:\n{key_text}"
    )

# Kalitni o'chirish
@bot.message_handler(func=lambda m: m.text == "🗑 Kalitni o'chirish")
def delete_key(message):
    """Kalitni o'chirish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    if not session['answer_key']:
        bot.send_message(
            message.chat.id,
            "❌ O'chiriladigan kalit yo'q!"
        )
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Ha", callback_data="delete_yes"),
        types.InlineKeyboardButton("❌ Yo'q", callback_data="delete_no")
    )
    
    bot.send_message(
        message.chat.id,
        f"⚠️ Kalitni o'chirmoqchimisiz?\n\n"
        f"Kalit: {session['total_questions']} savol",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["delete_yes", "delete_no"])
def delete_confirmation(call):
    """O'chirish tasdig'i"""
    if call.from_user.id != ADMIN_ID:
        return
    
    if call.data == "delete_yes":
        session['answer_key'] = None
        session['total_questions'] = 0
        bot.edit_message_text(
            "✅ Kalit o'chirildi!\n\n"
            "Yangi kalit yuklash uchun '📝 Yangi kalit' tugmasini bosing.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.edit_message_text(
            "❌ Bekor qilindi",
            call.message.chat.id,
            call.message.message_id
        )

# Test tekshirish
@bot.message_handler(func=lambda m: m.text == "📊 Test tekshirish")
def request_test(message):
    """Test javobini so'rash"""
    if message.from_user.id != ADMIN_ID:
        return
    
    if not session['answer_key']:
        bot.send_message(
            message.chat.id,
            "❌ Avval kalit yuklang!\n\n"
            "'📝 Yangi kalit' tugmasini bosing."
        )
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"📝 Talaba javobini yuboring:\n\n"
        f"📊 Test: {session['total_questions']} savol\n\n"
        f"📋 Qabul qilinadigan formatlar:\n\n"
        f"1️⃣ Matn:\n"
        f"   1A 2B 3C 4D...\n"
        f"   ABCDABCD...\n\n"
        f"2️⃣ Rasm:\n"
        f"   Javob varag'ini suratga oling\n\n"
        f"3️⃣ Fayl:\n"
        f"   .txt fayl yuboring\n\n"
        f"💡 Bitta talaba javobini yuborganingizdan keyin,\n"
        f"qaytadan '📊 Test tekshirish' bosib keyingisini yuboring."
    )
    bot.register_next_step_handler(msg, check_student_test)

def check_student_test(message):
    """Talaba testini tekshirish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    if not session['answer_key']:
        bot.send_message(message.chat.id, "❌ Kalit topilmadi!")
        return
    
    student_answers = None
    student_name = "Talaba"
    
    # Matn
    if message.text:
        student_answers = parse_answers(message.text)
    
    # Rasm
    elif message.photo:
        bot.send_message(message.chat.id, "🔄 Rasmdan matn o'qilmoqda...")
        
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # OCR
            text = extract_text_from_image(downloaded_file)
            
            if text:
                student_answers = parse_answers(text)
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Rasmdan matn o'qib bo'lmadi!\n\n"
                    "Iltimos:\n"
                    "• Aniq rasm yuboring\n"
                    "• Yoki javoblarni matn ko'rinishida yuboring"
                )
                return
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Javoblarni matn ko'rinishida yuboring."
            )
            return
    
    # Fayl
    elif message.document:
        if message.document.mime_type == 'text/plain':
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            text = downloaded_file.decode('utf-8')
            student_answers = parse_answers(text)
        else:
            bot.send_message(
                message.chat.id,
                "❌ Faqat .txt fayl qabul qilinadi!"
            )
            return
    
    # Rasm caption dan nom olish
    if message.caption:
        student_name = message.caption
    
    if not student_answers:
        bot.send_message(
            message.chat.id,
            "❌ Javoblar tanilmadi!\n\n"
            "To'g'ri formatda yuboring:\n"
            "1A 2B 3C 4D...\n\n"
            "Yoki qaytadan '📊 Test tekshirish' bosing."
        )
        return
    
    # Tekshirish
    result = check_answers(student_answers, session['answer_key'])
    
    # Tafsilotlarni formatlash
    details_lines = []
    for i in range(0, len(result['details']), 5):
        chunk = result['details'][i:i+5]
        details_lines.append("\n".join(chunk))
    
    details_text = "\n\n".join(details_lines[:4])  # Birinchi 20 ta savol
    
    if len(result['details']) > 20:
        details_text += f"\n\n... va yana {len(result['details']) - 20} ta savol"
    
    # Natijani yuborish
    result_message = (
        f"{'='*30}\n"
        f"📊 NATIJA\n"
        f"{'='*30}\n\n"
        f"👤 Talaba: {student_name}\n\n"
        f"✅ To'g'ri: {result['correct']}\n"
        f"❌ Noto'g'ri: {result['wrong']}\n"
        f"➖ Bo'sh: {result['empty']}\n"
        f"📊 Jami: {result['total']}\n\n"
        f"📈 Foiz: {result['percentage']:.1f}%\n"
        f"🎓 Baho: {result['grade']}\n\n"
        f"{'='*30}\n"
        f"TAFSILOTLAR:\n"
        f"{'='*30}\n\n"
        f"{details_text}"
    )
    
    bot.send_message(message.chat.id, result_message)
    
    # Keyingi test uchun taklif
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Test tekshirish", "📋 Kalit ko'rish")
    
    bot.send_message(
        message.chat.id,
        "✅ Tekshiruv tugadi!\n\n"
        "Keyingi talaba javobini tekshirish uchun\n"
        "'📊 Test tekshirish' tugmasini bosing.",
        reply_markup=markup
    )

# Qo'llanma
@bot.message_handler(func=lambda m: m.text == "ℹ️ Qo'llanma")
def show_guide(message):
    """Qo'llanmani ko'rsatish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    guide_text = (
        "📖 QO'LLANMA\n\n"
        "1️⃣ KALIT YUKLASH:\n"
        "   • '📝 Yangi kalit' tugmasini bosing\n"
        "   • Kalitni yuboring (1A 2B 3C...)\n\n"
        "2️⃣ TEST TEKSHIRISH:\n"
        "   • '📊 Test tekshirish' tugmasini bosing\n"
        "   • Talaba javobini yuboring\n"
        "   • Rasm yuborsangiz, caption da\n"
        "     talaba nomini yozing\n\n"
        "3️⃣ KALIT FORMATLAR:\n"
        "   ✅ 1A 2B 3C 4D...\n"
        "   ✅ 1)A 2)B 3)C...\n"
        "   ✅ ABCDABCD...\n\n"
        "4️⃣ JAVOB FORMATLAR:\n"
        "   📝 Matn: 1A 2B 3C...\n"
        "   📷 Rasm: javob varag'i\n"
        "   📄 Fayl: .txt fayl\n\n"
        "5️⃣ MASLAHATLAR:\n"
        "   💡 Rasm aniq bo'lishi kerak\n"
        "   💡 Rasm caption da nom yozing\n"
        "   💡 Bir vaqtda bitta test tekshiring\n\n"
        "❓ Yordam kerakmi? /start bosing"
    )
    
    bot.send_message(message.chat.id, guide_text)

# Botni ishga tushirish
if __name__ == '__main__':
    print("="*50)
    print("🤖 Test Tekshiruvchi Bot ishga tushdi!")
    print("="*50)
    print(f"📋 Admin ID: {ADMIN_ID}")
    print("⌨️  Botni to'xtatish: Ctrl+C")
    print("="*50)
    bot.infinity_polling()
