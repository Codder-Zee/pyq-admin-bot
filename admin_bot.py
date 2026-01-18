import telebot
import os

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # आपका Telegram ID
FILE_PATH = "marathi.txt"

bot = telebot.TeleBot(BOT_TOKEN)

waiting_for_upload = set()

# ================= HELPERS =================

def is_admin(message):
    return message.from_user.id == ADMIN_ID


def count_questions():
    if not os.path.exists(FILE_PATH):
        return 0
    count = 0
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("Q:"):
                count += 1
    return count


def extract_questions(text):
    lines = text.strip().splitlines()
    valid = []
    block = []

    for line in lines:
        if line.strip().startswith("Q:") and block:
            valid.append("\n".join(block))
            block = []
        block.append(line)

    if block:
        valid.append("\n".join(block))

    return valid


# ================= COMMANDS =================

@bot.message_handler(commands=["start"])
def start(message):
    if not is_admin(message):
        return

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ New Upload", "📊 Show Count")

    bot.send_message(
        message.chat.id,
        "✅ PYQ Admin Bot Ready\n\nChoose an option:",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda m: m.text == "📊 Show Count" or m.text == "/showCount")
def show_count(message):
    if not is_admin(message):
        return

    total = count_questions()
    bot.send_message(
        message.chat.id,
        f"📊 marathi.txt में कुल questions: {total}"
    )


@bot.message_handler(func=lambda m: m.text == "➕ New Upload" or m.text == "/newUpload")
def new_upload(message):
    if not is_admin(message):
        return

    waiting_for_upload.add(message.chat.id)
    bot.send_message(
        message.chat.id,
        "📝 नीचे questions paste करें\n\n"
        "Format example:\n"
        "Z: संदर्भ...\n"
        "Q: प्रश्न?\n"
        "A: ...\nB: ...\nC: ...\nD: ... *"
    )


@bot.message_handler(func=lambda m: m.chat.id in waiting_for_upload)
def receive_questions(message):
    if not is_admin(message):
        return

    text = message.text.strip()
    questions = extract_questions(text)

    if not questions:
        bot.send_message(
            message.chat.id,
            "❌ कोई valid question नहीं मिला"
        )
        return

    with open(FILE_PATH, "a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write("\n\n".join(questions))
        f.write("\n\n")

    waiting_for_upload.remove(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"✅ {len(questions)} questions successfully add हो चुके हैं"
    )


# ================= RUN =================
print("Admin bot running...")
bot.infinity_polling()
