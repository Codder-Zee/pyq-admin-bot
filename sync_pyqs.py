import base64
import os
import requests

# --- Configuration ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = os.environ["ADMIN_ID"]
THUB_TOKEN = os.environ["THUB_TOKEN"]

TARGET_REPO = "Codder-Zee/talhathi-pyq-bot"
BRANCH = "main"
STATE_FILE = "last_update.txt"
SELECTED_FILE_STATE = "selected_file.txt"

FILE_MAPPING = {
    "Marathi": "pyq_data/marathi.pyq",
    "English": "pyq_data/English.pyq",
    "Other": "pyq_data/pyq.txt",
}

DEFAULT_FILE = "pyq_data/pyq.txt"

HEADERS = {
    "Authorization": f"token {THUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


# --- Helper Functions ---
def get_last_update():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_last_update(update_id):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(update_id))


def get_current_target_file():
    try:
        with open(SELECTED_FILE_STATE, "r", encoding="utf-8") as f:
            file_path = f.read().strip()
            return file_path if file_path else DEFAULT_FILE
    except Exception:
        return DEFAULT_FILE


def save_current_target_file(file_path):
    with open(SELECTED_FILE_STATE, "w", encoding="utf-8") as f:
        f.write(file_path)


def get_updates(offset):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    r = requests.get(url, params={"offset": offset, "timeout": 30})
    r.raise_for_status()
    return r.json()["result"]


def get_repo_file(target_file):
    url = f"https://api.github.com/repos/{TARGET_REPO}/contents/{target_file}"
    r = requests.get(url, headers=HEADERS, params={"ref": BRANCH})
    r.raise_for_status()

    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def update_repo_file(target_file, content, sha):
    url = f"https://api.github.com/repos/{TARGET_REPO}/contents/{target_file}"
    payload = {
        "message": f"Nightly PYQ Sync - {target_file.split('/')[-1]}",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": BRANCH,
    }
    r = requests.put(url, headers=HEADERS, json=payload)
    r.raise_for_status()


def count_questions(text):
    return sum(1 for line in text.splitlines() if line.strip().startswith("Q:"))


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    reply_markup = {
        "keyboard": [
            [{"text": "Marathi"}, {"text": "English"}, {"text": "Other"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
    payload = {
        "chat_id": ADMIN_ID, 
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)


# --- Main Logic ---
def main():
    last_update = get_last_update()
    updates = get_updates(last_update + 1)

    # 🛑 जर नवीन मेसेजेस नसतील तर लगेच रिप्लाय द्या आणि एक्झिट करा
    if not updates:
        send_telegram("ℹ️ No new PYQs found.")
        return

    newest_update = last_update
    pending_text_list = []  # सर्व नवीन प्रश्न एकाच वेळी साठवण्यासाठी
    button_pressed = None

    for upd in updates:
        newest_update = max(newest_update, upd["update_id"])
        msg = upd.get("message")

        if not msg or str(msg["chat"]["id"]) != str(ADMIN_ID):
            continue

        text = msg.get("text", "").strip()
        if not text:
            continue

        # जर युझरने बटण दाबलं असेल
        if text in FILE_MAPPING:
            button_pressed = text
            selected_path = FILE_MAPPING[text]
            save_current_target_file(selected_path)
            continue

        # जर नॉर्मल मेसेज असेल तर लिस्टमध्ये गोळा करा
        pending_text_list.append(text)

    # 1️⃣ केस १: फक्त बटण दाबलं आहे, कोणताही मेसेज पाठवलेला नाही
    if button_pressed and not pending_text_list:
        target_file = FILE_MAPPING[button_pressed]
        try:
            repo_text, _ = get_repo_file(target_file)
            current_count = count_questions(repo_text)
        except Exception:
            current_count = 0
        send_telegram(f"📁 Selected File: *{button_pressed}*\n📊 Current Questions in this file: {current_count}")
        save_last_update(newest_update)
        return

    # 2️⃣ केस २: मेसेजेस आले आहेत (बटण दाबून किंवा न दाबता थेट)
    if pending_text_list:
        target_file = get_current_target_file()
        file_name_display = [name for name, path in FILE_MAPPING.items() if path == target_file]
        display_name = file_name_display[0] if file_name_display else "Other"

        try:
            # गिटहबवरून फाईल एकदाच डाऊनलोड करा
            repo_text, sha = get_repo_file(target_file)
            
            # सर्व मेसेजेस बॅचमध्ये एकत्र जोडा
            combined_new_text = "\n".join(pending_text_list)
            repo_text = repo_text.rstrip("\n") + "\n" + combined_new_text
            
            # गिटहबवर एकदाच अपडेट करा (एरर टाळण्यासाठी)
            update_repo_file(target_file, repo_text, sha)
            total = count_questions(repo_text)

            # 🎯 फक्त एकच फायनल रिप्लाय
            send_telegram(
                f"✅ Questions add ho gaye in *{display_name}*\n"
                f"📥 Added messages: {len(pending_text_list)}\n"
                f"📊 Total questions in this file: {total}"
            )
        except Exception as e:
            send_telegram(f"❌ Error updating GitHub for {display_name}: {str(e)}")

    # जर काहीच व्हॅलिड डेटा मॅच झाला नसेल तरी अपडेट आयडी सेव्ह करा
    elif newest_update > last_update:
        send_telegram("ℹ️ No new PYQs found.")

    save_last_update(newest_update)


if __name__ == "__main__":
    main()
    
