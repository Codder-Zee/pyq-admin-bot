import os
import requests
import base64
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_FILE_PATH = os.getenv("GITHUB_FILE_PATH")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

WAITING_UPLOAD = set()


# ----------------- helpers -----------------

def get_file():
    r = requests.get(GITHUB_API, headers=HEADERS, params={"ref": GITHUB_BRANCH})
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def update_file(new_content, sha, msg):
    payload = {
        "message": msg,
        "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": GITHUB_BRANCH
    }
    r = requests.put(GITHUB_API, headers=HEADERS, json=payload)
    r.raise_for_status()


def count_questions(text):
    return sum(1 for line in text.splitlines() if line.strip().startswith("Q:"))


# ----------------- commands -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [["/newUpload", "/countall"]]
    await update.message.reply_text(
        "Admin panel ready 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def new_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    WAITING_UPLOAD.add(update.effective_user.id)
    await update.message.reply_text(
        "📥 Ab questions paste karo (exact format me).\n\n"
        "Paste karne ke baad automatically file update ho jayegi."
    )


async def receive_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in WAITING_UPLOAD:
        return

    WAITING_UPLOAD.remove(uid)
    new_block = update.message.text.strip()

    old_text, sha = get_file()

    updated_text = old_text.rstrip() + "\n\n" + new_block + "\n"

    update_file(updated_text, sha, "Admin: added new questions")

    total = count_questions(updated_text)

    await update.message.reply_text(
        f"✅ Questions add ho gaye.\n\n📊 Total questions: {total}"
    )


async def count_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    text, _ = get_file()
    total = count_questions(text)

    await update.message.reply_text(
        f"📊 marathi.txt me kul questions: {total}"
    )


# ----------------- main -----------------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("newUpload", new_upload))
app.add_handler(CommandHandler("countall", count_all))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_questions))

app.run_polling()
