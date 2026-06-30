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

# योग्य फाईल पाथ्स (तुमच्या गरजेनुसार .txt फॉरमॅट)
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

    # 1️⃣ आधी सर्व मेसेज पूर्णपणे लूप फिरवून सेपरेट करून घ्या (काहीही पुश न करता)
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
        
        # कोणतीही डुप्लिकेट टाळण्यासाठी फक्त मेसेज लिस्टमध्ये ॲड करा
        pending_questions.append(text)

    # कोणती फाईल वापरायची ते ठरवा
    selected_file_key = detected_command if detected_command else "Other"
    target_file = FILE_MAPPING[selected_file_key]

    # २) केस १: फक्त बटण दाबलंय पण नवीन प्रश्न एकही पाठवलेला नाही
    if detected_command and not pending_questions:
        try:
            repo_text, _ = get_repo_file(target_file)
            total = count_questions(repo_text)
        except Exception:
            total = 0
        send_telegram(f"📁 Selected File: {selected_file_key}\n📊 Total questions: {total}")
        save_last_update(newest_update)
        return

    # ३) केस २: नवीन प्रश्न आले आहेत (आता हे मुख्य लूपच्या बाहेर फक्त १ वेळच रन होईल)
    if pending_questions:
        try:
            # गिटहबवरून फाईलचा करंट डेटा आणा
            repo_text, sha = get_repo_file(target_file)
            
            # 📊 जुने प्रश्न मोजा (Old Count)
            old_count = count_questions(repo_text)
            
            # नवीन मेसेजेस कोणत्याही स्पेसशिवाय एकाखाली एक जोडणे
            new_content = "\n".join(pending_questions)
            if repo_text and not repo_text.endswith("\n"):
                repo_text += "\n" + new_content
            else:
                repo_text += new_content
            
            # गिटहबवर सिंगल पुश (यामुळे 409 एरर किंवा री-अपलोड होणार नाही)
            update_repo_file(target_file, repo_text, sha)
            
            # 📊 नवीन टोटल काउंट
            total_count = count_questions(repo_text)
            
            # 🎯 तुमच्या गरजेनुसार परफेक्ट रिप्लाय फॉरमॅट
            send_telegram(
                f"✅ Questions add ho gaye in *{selected_file_key}.txt*\n"
                f"📊 Previous questions: {old_count}\n"
                f"📥 Newly added: {len(pending_questions)}\n"
                f"📈 Total questions now: {total_count}"
            )
        except Exception as e:
            send_telegram(f"❌ Error updating GitHub for {selected_file_key}: {str(e)}")
    else:
        send_telegram("ℹ️ No new PYQs found.")

    # शेवटी अपडेट आयडी सेव्ह करा जेणेकरून हे प्रश्न पुन्हा प्रोसेस होणार नाहीत
    save_last_update(newest_update)


if __name__ == "__main__":
    main()
    
