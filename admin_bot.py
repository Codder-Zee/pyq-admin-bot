import telebot, os, json

BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DATA_FILE = "pyq_data/marathi.txt"
META_FILE = "meta.json"
UPLOAD_FILE = "uploads.json"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- helpers ----------
def admin_only(m): 
    return m.from_user.id == ADMIN_ID

def load_json(f, default):
    if not os.path.exists(f):
        return default
    with open(f, "r", encoding="utf-8") as fp:
        return json.load(fp)

def save_json(f, data):
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)

# ---------- states ----------
meta = load_json(META_FILE, {"history": [], "redo": []})
uploads = load_json(UPLOAD_FILE, {"buffer": []})


# ---------- commands ----------
@bot.message_handler(commands=["start"])
def start(m):
    if not admin_only(m): return
    bot.reply_to(m, "✅ PYQ Admin Bot Ready")

@bot.message_handler(commands=["lastpoll"])
def lastpoll(m):
    if not admin_only(m): return
    if not meta["history"]:
        bot.reply_to(m, "❌ No poll yet")
        return

    q = meta["history"][-1]
    text = f"📊 LAST POLL\n\n{q}"
    bot.reply_to(m, text)

@bot.message_handler(commands=["remaining"])
def remaining(m):
    if not admin_only(m): return
    total = sum(1 for l in open(DATA_FILE, encoding="utf-8") if l.startswith("Q:"))
    used = len(meta["history"])
    bot.reply_to(m, f"📌 Remaining Questions: {total - used}")

@bot.message_handler(commands=["newupload"])
def newupload(m):
    if not admin_only(m): return
    uploads["buffer"] = []
    save_json(UPLOAD_FILE, uploads)
    bot.reply_to(m, "✍️ Questions paste karo\nEnd me /done likho")

@bot.message_handler(commands=["done"])
def done(m):
    if not admin_only(m): return
    if not uploads["buffer"]:
        bot.reply_to(m, "❌ Kuch bhi upload nahi hua")
        return

    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write("\n\n" + "\n".join(uploads["buffer"]))

    meta["history"].append("\n".join(uploads["buffer"]))
    meta["redo"].clear()

    save_json(META_FILE, meta)
    uploads["buffer"] = []
    save_json(UPLOAD_FILE, uploads)

    bot.reply_to(m, "✅ Questions added successfully")

@bot.message_handler(commands=["undo"])
def undo(m):
    if not admin_only(m): return
    if not meta["history"]:
        bot.reply_to(m, "❌ Nothing to undo")
        return

    last = meta["history"].pop()
    meta["redo"].append(last)

    text = open(DATA_FILE, encoding="utf-8").read()
    text = text.replace(last, "").strip()

    open(DATA_FILE, "w", encoding="utf-8").write(text)
    save_json(META_FILE, meta)

    bot.reply_to(m, "↩️ Last upload undone")

@bot.message_handler(commands=["redo"])
def redo(m):
    if not admin_only(m): return
    if not meta["redo"]:
        bot.reply_to(m, "❌ Nothing to redo")
        return

    last = meta["redo"].pop()
    open(DATA_FILE, "a", encoding="utf-8").write("\n\n" + last)

    meta["history"].append(last)
    save_json(META_FILE, meta)

    bot.reply_to(m, "↪️ Redo successful")

@bot.message_handler(func=lambda m: admin_only(m))
def capture_text(m):
    uploads["buffer"].append(m.text)
    save_json(UPLOAD_FILE, uploads)

bot.infinity_polling()
