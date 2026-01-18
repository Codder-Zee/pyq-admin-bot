import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_FILE_PATH = os.getenv("GITHUB_FILE_PATH")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

BASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

UPLOAD_MODE = {}

# ---------- GitHub helpers ----------

def get_file():
    r = requests.get(BASE_API, headers=headers, params={"ref": GITHUB_BRANCH})
    data = r.json()
    content = requests.utils.unquote(data["content"])
    text = bytes(content, "utf-8").decode("base64") if False else data
    import base64
    return base64.b64decode(data["content"]).decode(), data["sha"]

def update_file(new_text, sha, message):
    import base64
    payload = {
        "message": message,
        "content": base64.b64encode(new_text.encode()).decode(),
        "sha": sha,
        "branch": GITHUB_BRANCH
    }
    requests.put(BASE_API, headers=headers, json=payload)

def count_questions(text):
    return sum(1 for line in text.splitlines() if line.strip().startswith("Q:"))

# ---------- Telegram handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    kb = [["/newUpload", "/showCount"]]
    await update.message.reply_text(
        "🛠 PYQ Admin Bot Ready",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def show_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text, _ = get_file()
    count = count_questions(text)
    await update.message.reply_text(f"📊 marathi.txt में कुल questions: {count}")

async def new_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    UPLOAD_MODE[update.effective_user.id] = True
    await update.message.reply_text(
        "📝 नीचे questions paste करें.\n\nFormat वही होना चाहिए:\nZ:\nQ:\nA:\nB:\nC:\nD:"
    )

async def receive_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID or not UPLOAD_MODE.get(uid):
        return

    new_block = update.message.text.strip()
    old_text, sha = get_file()

    if not old_text.endswith("\n"):
        old_text += "\n\n"

    updated = old_text + new_block + "\n\n"

    update_file(updated, sha, "Admin bot: add new questions")
    UPLOAD_MODE[uid] = False

    await update.message.reply_text("✅ Questions successfully add ho chuke hain.")

# ---------- MAIN ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("showCount", show_count))
app.add_handler(CommandHandler("newUpload", new_upload))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_questions))

app.run_polling()
