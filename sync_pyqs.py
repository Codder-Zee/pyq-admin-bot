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

# बटण आणि गिटहब फाईल पाथ मॅपिंग (फक्त नाव बदलले)
FILE_MAPPING = {
    "Marathi": "pyq_data/Marathi.txt",
    "English": "pyq_data/English.txt",
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

def get_updates(offset):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    r = requests.get(url, params={"offset": offset, "timeout": 30})
    r.raise_for_status()
    return r.json()["result"]

def get_repo_file(target_file):
    url = f"https://api.github.com/repos/{TARGET_REPO}/contents/{target_file}"
    r = requests.get(url, headers=HEADERS, params={"ref": BRANCH})
    if r.status_code == 404:
        return "", None
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]

def update_repo_file(target_file, content, sha):
    url = f"https://api.github.com/repos/{TARGET_REPO}/contents/{target_file}"
    payload = {
        "message": f"Nightly PYQ Sync - {target_file.split('/')[-1]}",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=HEADERS, json=payload)
    r.raise_for_status()

def count_questions(text):
    return sum(1 for line in text.splitlines() if line.strip().startswith("Q:"))

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    reply_markup = {
        "keyboard": [[{"text": "Marathi"}, {"text": "English"}, {"text": "Other"}]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    payload = {"chat_id": ADMIN_ID, "text": text, "reply_markup": reply_markup}
    requests.post(url, json=payload)

# --- Main Logic ---
def main():
    last_update = get_last_update()
    updates = get_updates(last_update + 1)

    if not updates:
        send_telegram("ℹ️ No new PYQs found.")
        return

    newest_update = last_update
    pending_questions = []
    detected_command = None

    for upd in updates:
        newest_update = max(newest_update, upd["update_id"])
        msg = upd.get("message")
        if not msg or str(msg["chat"]["id"]) != str(ADMIN_ID):
            continue
        text = msg.get("text", "").strip()
        if not text:
            continue
        if text in FILE_MAPPING:
            detected_command = text
            continue
        pending_questions.append(text)

    selected_file_key = detected_command if detected_command else "Other"
    target_file = FILE_MAPPING[selected_file_key]

    if detected_command and not pending_questions:
        try:
            repo_text, _ = get_repo_file(target_file)
            total = count_questions(repo_text)
        except Exception:
            total = 0
        send_telegram(f"📁 Selected File: {selected_file_key}\n📊 Total questions: {total}")
        save_last_update(newest_update)
        return

    if pending_questions:
        try:
            repo_text, sha = get_repo_file(target_file)
            new_content = "\n".join(pending_questions)
            if repo_text and not repo_text.endswith("\n"):
                repo_text += "\n" + new_content
            else:
                repo_text += new_content
            update_repo_file(target_file, repo_text, sha)
            total = count_questions(repo_text)
            send_telegram(f"✅ Questions add ho gaye\n📥 Added: {len(pending_questions)}\n📊 Total: {total}")
        except Exception as e:
            send_telegram(f"❌ Error updating GitHub for {selected_file_key}: {str(e)}")
    else:
        send_telegram("ℹ️ No new PYQs found.")

    save_last_update(newest_update)

if __name__ == "__main__":
    main()
    
