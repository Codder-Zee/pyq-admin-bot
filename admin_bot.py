import os
import base64
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_FILE_PATH = os.getenv("GITHUB_FILE_PATH")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

UPLOAD_MODE = set()

# ===== GitHub helpers =====
def get_file_from_github():
    r = requests.get(GITHUB_API, headers=HEADERS, params={"ref": GITHUB_BRANCH})
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]

def update_file_on_github(new_text, sha, message):
    payload = {
        "message": message,
        "content": base64.b64encode(new_text.encode()).decode(),
        "sha": sha,
        "branch": GITHUB_BRANCH
    }
    r = requests.put(GITHUB_API, headers=HEADERS, json=payload)
    r.raise_for_status()

def count_questions(text):
    return sum(1 for line in text.splitlines() if line.strip().startswith("Q:"))

# ===== Telegram commands =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [["/newupdate", "/countall"]]
    await update.message.reply_text(
        "✅ Admin Bot Ready",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def count_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    text, _ = get_file_from_github()
    total = count_questions(text)
    await update.message.reply_text(
        f"📊 marathi.txt में कुल questions: {total}"
    )

async def new_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    UPLOAD_MODE.add(update.effective_user.id)
    await update.message.reply_text(
        "📝 नीचे नए questions paste करें\n\n"
        "Format वही रखें:\n"
        "Z: (optional)\n"
        "Q:\nA:\nB:\nC:\nD:"
    )

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID or uid not in UPLOAD_MODE:
        return

    new_questions = update.message.text.strip()
    old_text, sha = get_file_from_github()

    if not old_text.endswith("\n"):
        old_text += "\n\n"

    updated_text = old_text + new_questions + "\n\n"

    update_file_on_github(
        updated_text,
        sha,
        "Admin bot: add new questions"
    )

    UPLOAD_MODE.remove(uid)
    await update.message.reply_text("✅ Questions successfully add ho gaye")

# ===== MAIN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("countall", count_all))
app.add_handler(CommandHandler("newupdate", new_update))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))

app.run_polling()
