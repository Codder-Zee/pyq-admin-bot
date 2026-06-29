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

# बटण आणि गिटहब फाईल पाथ मॅपिंग
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
    
    # कीबोर्ड बटन्स स्क्रीनवर कायम ठेवण्यासाठी
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
        "reply_markup": reply_markup
    }
    requests.post(url, json=payload)


# --- Main Logic ---
def main():
    last_update = get_last_update()
    updates = get_updates(last_update + 1)

    # 🛑 जर टेलिग्रामवर एकही नवीन मेसेज/बटण क्लिक आलेले नसेल
    if not updates:
        send_telegram("ℹ️ No new PYQs found.")
        return

    newest_update = last_update
    pending_questions = []
    detected_command = None

    # आलेल्या सर्व अपडेट्समधून डेटा गोळा करणे
    for upd in updates:
        newest_update = max(newest_update, upd["update_id"])
        msg = upd.get("message")

        if not msg or str(msg["chat"]["id"]) != str(ADMIN_ID):
            continue

        text = msg.get("text", "").strip()
        if not text:
            continue

        # जर युझरने बटण दाबलं असेल, तर कमांड अपडेट करा
        if text in FILE_MAPPING:
            detected_command = text
            continue

        # बटण सोडून आलेले इतर मेसेजेस (प्रश्न) लिस्टमध्ये टाका
        pending_questions.append(text)

    # गिटहब ॲक्शनसाठी बॅकअप: जर चालू रनमध्ये कोणतंच बटण दाबलं नसेल, तर ते DEFAULT_FILE (Other) मध्ये जाईल
    selected_file_key = detected_command if detected_command else "Other"
    target_file = FILE_MAPPING[selected_file_key]

    # 1️⃣ जर फक्त बटण दाबलंय पण नवीन प्रश्न एकही नाही
    if detected_command and not pending_questions:
        try:
            repo_text, _ = get_repo_file(target_file)
            total = count_questions(repo_text)
        except Exception:
            total = 0
        send_telegram(
            f"📁 Selected File: {selected_file_key}\n"
            f"📥 Added messages: 0\n"
            f"📊 Total questions: {total}"
        )
        save_last_update(newest_update)
        return

    # 2️⃣ जर नवीन प्रश्न आले असतील, तर ते योग्य फाईलमध्ये सेव्ह करा
    if pending_questions:
        try:
            # गिटहबवरून फाईलचा करंट डेटा आणा
            repo_text, sha = get_repo_file(target_file)
            
            # नवीन मेसेजेस कोणत्याही अतिरिक्त स्पेसशिवाय एकाखाली एक जोडणे
            new_content = "\n".join(pending_questions)
            if repo_text and not repo_text.endswith("\n"):
                repo_text += "\n" + new_content
            else:
                repo_text += new_content

            # गिटहबवर फाईल अपडेट करा
            update_repo_file(target_file, repo_text, sha)
            total = count_questions(repo_text)

            # मूळ बेस व्हर्जनसारखाच नेटका सिंगल रिप्लाय
            send_telegram(
                f"✅ Questions add ho gaye\n"
                f"📥 Added messages: {len(pending_questions)}\n"
                f"📊 Total questions: {total}"
            )
        except Exception as e:
            send_telegram(f"❌ Error updating GitHub for {selected_file_key}: {str(e)}")
    
    # 3️⃣ जर मेसेजेस आले पण ते व्हॅलिड नव्हते (रिकामे मेसेज)
    else:
        send_telegram("ℹ️ No new PYQs found.")

    # शेवटी स्टेट अपडेट करा जेणेकरून पुढच्या वेळी हेच प्रश्न पुन्हा रिपीट होणार नाहीत
    save_last_update(newest_update)


if __name__ == "__main__":
    main()
        
