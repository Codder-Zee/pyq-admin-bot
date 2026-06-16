import base64
import os
import requests

# --- Configuration ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = os.environ["ADMIN_ID"]
THUB_TOKEN = os.environ["THUB_TOKEN"]

TARGET_REPO = "Codder-Zee/talhathi-pyq-bot"
TARGET_FILE = "pyq_data/pyq.txt"
BRANCH = "main"
STATE_FILE = "last_update.txt"

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


def get_repo_file():
    url = f"https://api.github.com/repos/{TARGET_REPO}/contents/{TARGET_FILE}"
    r = requests.get(url, headers=HEADERS, params={"ref": BRANCH})
    r.raise_for_status()

    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def update_repo_file(content, sha):
    url = f"https://api.github.com/repos/{TARGET_REPO}/contents/{TARGET_FILE}"
    payload = {
        "message": "Nightly PYQ Sync",
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
    requests.post(url, json={"chat_id": ADMIN_ID, "text": text})


# --- Main Logic ---
def main():
    last_update = get_last_update()
    updates = get_updates(last_update + 1)

    if not updates:
        send_telegram("ℹ️ No new PYQs found.")
        return

    repo_text, sha = get_repo_file()
    added = 0
    newest_update = last_update

    for upd in updates:
        newest_update = max(newest_update, upd["update_id"])
        msg = upd.get("message")

        if not msg:
            continue

        if str(msg["chat"]["id"]) != str(ADMIN_ID):
            continue

        text = msg.get("text", "").strip()
        if not text:
            continue

        repo_text = repo_text.rstrip("\n") + "\n" + text
        added += 1

    if added > 0:
        update_repo_file(repo_text, sha)

    save_last_update(newest_update)
    total = count_questions(repo_text)

    send_telegram(
        f"✅ Questions add ho gaye\n"
        f"📥 Added messages: {added}\n"
        f"📊 Total questions: {total}"
    )


if __name__ == "__main__":
    main()
    
