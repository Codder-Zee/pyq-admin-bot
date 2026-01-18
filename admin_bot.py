import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

FILE_PATH = "pyq_data/marathi.txt"

# ----------------- helpers -----------------

def is_admin(update: Update):
    return update.effective_user.id == ADMIN_ID

def count_questions():
    if not os.path.exists(FILE_PATH):
        return 0
    count = 0
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("Q:"):
                count += 1
    return count

def append_questions(text):
    with open(FILE_PATH, "a", encoding="utf-8") as f:
        f.write("\n\n" + text.strip() + "\n")

# ----------------- commands -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    keyboard = [
        ["/newUpload", "/showCount"]
    ]

    await update.message.reply_text(
        "✅ PYQ Admin Bot Ready\n\nButtons use करें 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

async def new_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    context.user_data["awaiting_upload"] = True

    await update.message.reply_text(
        "📝 नीचे questions paste करें 👇\n\n(Format वही रखें जो पहले है)"
    )

async def show_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    total = count_questions()
    await update.message.reply_text(
        f"📊 marathi.txt में कुल questions: {total}"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    if context.user_data.get("awaiting_upload"):
        text = update.message.text.strip()

        if not text:
            await update.message.reply_text("❌ Empty input मिला")
            return

        append_questions(text)
        context.user_data["awaiting_upload"] = False

        await update.message.reply_text(
            "✅ Questions successfully added"
        )

# ----------------- main -----------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newUpload", new_upload))
    app.add_handler(CommandHandler("showCount", show_count))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Admin bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
