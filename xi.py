#!/usr/bin/env python3
# telegram_deepai_polling_fixed.py
# Requirements: python-telegram-bot==13.15, requests

import os
import json
import logging
import requests
from pathlib import Path
from datetime import datetime
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ================ CONFIG ================
# নিরাপদভাবে টোকেন environment-এ রাখো
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8273934695:AAFlM1x5Jf3ukA3pROoDhGrYXJ3SKCamSlQ")

# তোমার (অ্যাডমিন) টেলিগ্রাম numeric ID এখানে সেট করো বা ENV থেকে নাও
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "7552513938"))

# DeepAI সেটিংস
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY", "tryit-99974563413-d55b1638b9f7372403addba76651d2e5")
DEEPAI_URL = os.getenv("DEEPAI_URL", "https://api.deepai.org/hacking_is_a_serious_crime")

# ইতিহাস ফাইল
HISTORY_FILE = Path(os.getenv("HISTORY_FILE", "histories.json"))
MAX_HISTORY_PER_CHAT = int(os.getenv("MAX_HISTORY_PER_CHAT", 25))
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", 4000))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", 25.0))
# =========================================

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fesa_bot")

# ensure history file exists
if not HISTORY_FILE.exists():
    try:
        HISTORY_FILE.write_text("{}", encoding="utf-8")
    except Exception:
        pass

def load_histories():
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Could not load histories: %s", e)
        return {}

def save_histories(h):
    try:
        HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to save histories: %s", e)

histories = load_histories()

def append_user_message(chat_id, text):
    h = histories.get(chat_id, [])
    h.append({"role": "user", "content": text})
    histories[chat_id] = h[-MAX_HISTORY_PER_CHAT:]
    save_histories(histories)

def append_assistant_message(chat_id, text):
    h = histories.get(chat_id, [])
    h.append({"role": "assistant", "content": text})
    histories[chat_id] = h[-MAX_HISTORY_PER_CHAT:]
    save_histories(histories)

# সুন্দর ভাবে ইউজারকে দেখানোর জন্য উত্তর ফরম্যাট
def format_reply_for_user(user, text):
    MAX_CHUNK = 4000
    header = (
        f"<b>💠 FESA-AI</b>\n"
        f"<i>{user.first_name if user.first_name else 'বন্ধু'}</i>, তোমার অনুরোধ পেয়েছি — "
        f"<code>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</code>\n\n"
    )
    developer_block = (
        "<b>ডেভেলপার পরিচিতি:</b>\n"
        "আমি একজন ডেভেলপার — <b>Mehadi</b>\n"
        "টিম: <b>Falcon-X Elite Security Asia (FESA)</b>\n\n"
    )
    footer = "\n\n— <i>Silent. Swift. Secure.</i>"
    body = str(text)

    if len(body) <= MAX_CHUNK:
        return header + developer_block + body + footer

    # যদি বড় হয়, প্রথম অংশ দিতে হবে
    return header + developer_block + body[:MAX_CHUNK] + "\n\n(পরবর্তী অংশ...)" + footer

# DeepAI কল
def call_deepai(chat_id):
    if chat_id not in histories or len(histories[chat_id]) == 0:
        return "আমি প্রস্তুত — এখনো কোনো history নেই।"
    # truncate too-long messages
    history = histories[chat_id]
    for m in history:
        if len(m.get("content", "")) > MAX_MESSAGE_LENGTH:
            m["content"] = m["content"][:MAX_MESSAGE_LENGTH] + "...(truncated)"
    data = {
        "chat_style": "chat",
        "chatHistory": json.dumps(history, ensure_ascii=False),
        "model": "standard",
        "enabled_tools": '["image_generator"]'
    }
    headers = {"api-key": DEEPAI_API_KEY, "User-Agent": "telegram-deepai-bot/1.0"}
    try:
        resp = requests.post(DEEPAI_URL, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logger.error("DeepAI request failed: %s", e)
        return f"DeepAI অনুরোধ ব্যর্থ: {e}"
    if resp.status_code != 200:
        logger.warning("DeepAI returned status %s", resp.status_code)
        try:
            j = resp.json()
            if isinstance(j, dict) and j.get("message"):
                return j.get("message")
        except Exception:
            pass
        return f"DeepAI সার্ভার ত্রুটি ({resp.status_code})"
    ctype = resp.headers.get("content-type", "")
    text = resp.text.strip()
    if text.startswith("{") or "application/json" in ctype:
        try:
            j = resp.json()
            if isinstance(j, dict):
                if isinstance(j.get("message"), str):
                    return j["message"]
                elif isinstance(j.get("data"), dict):
                    return json.dumps(j["data"], ensure_ascii=False)
            return json.dumps(j, ensure_ascii=False)
        except Exception:
            return text
    return text

# ----------------- Telegram handlers -----------------
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    welcome = (
        f"<b>আসসালামু আলাইকুম {user.first_name if user.first_name else ''}!</b>\n\n"
        "আমি তোমার <b>FESA-AI</b> বট — এখানে তোমার প্রশ্ন দ্রুত ও স্টাইল করে উত্তর পাবেন।\n\n"
        "<b>ডেভেলপার:</b> Mehadi\n"
        "<b>টিম:</b> Falcon-X Elite Security Asia (FESA)\n\n"
        "ব্যবহার টিপস: সংক্ষিপ্ত ও স্পষ্ট প্রশ্ন দাও।"
    )
    try:
        update.message.reply_html(welcome)
    except Exception as e:
        logger.error("Failed to send welcome: %s", e)

    # notify admin
    try:
        context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"🔔 নতুন ইউজার বট চালু করেছে\n"
                f"নাম: {user.full_name}\n"
                f"ইউজারনেম: @{user.username if user.username else 'N/A'}\n"
                f"আইডি: {user.id}\n"
                f"সময় (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        )
    except Exception as e:
        logger.warning("Failed to notify admin: %s", e)

def help_cmd(update: Update, context: CallbackContext):
    help_text = (
        "কমান্ড:\n"
        "/start - বট শুরু\n"
        "/help - সাহায্য\n"
        "/history - শেষ কিছু মেসেজের সংক্ষিপ্তভিত্তিক তালিকা\n"
        "/clearhistory - তোমার চ্যাট ইতিহাস মুছে ফেলা\n\n"
        "শুধু টেক্সট পাঠাও — আমি উত্তর দেব।"
    )
    update.message.reply_text(help_text)

def history_cmd(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    h = histories.get(chat_id, [])
    if not h:
        update.message.reply_text("তোমার কোনো history নেই।")
        return
    preview = []
    for e in h[-10:]:
        role = e.get("role")
        content = e.get("content", "")
        content = (content[:300] + "...") if len(content) > 300 else content
        preview.append(f"{role}: {content}")
    update.message.reply_text("\n\n".join(preview))

def clearhistory_cmd(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    if chat_id in histories:
        histories.pop(chat_id, None)
        save_histories(histories)
    update.message.reply_text("তোমার history মুছে ফেলা হয়েছে।")

def handle_message(update: Update, context: CallbackContext):
    msg = update.message
    chat_id = str(msg.chat_id)
    text = msg.text or ""
    logger.info("Msg from %s: %s", chat_id, text[:200])

    if not text.strip():
        msg.reply_text("খালি মেসেজ পেলাম — কিছু লিখে পাঠাও।")
        return

    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH] + "\n...(truncated)"

    # দ্রুত প্রাথমিক acknowledgement পাঠানো (ফাস্ট রেসপন্স অনুভব করাবে)
    try:
        ack = msg.reply_text("✅ অনুমোদন করা হলো — তোমার উত্তর করছি...")  # দ্রুত দেখা যাবে
    except Exception:
        ack = None

    append_user_message(chat_id, text)

    # মূল উত্তর আনো (synchronous); API ধীর হলে acknowledgement দেখে ইউজার তাড়াতাড়ি বুঝবে
    reply = call_deepai(chat_id)
    append_assistant_message(chat_id, reply)

    # স্টাইল্ড সম্পূর্ণ উত্তর পাঠাও
    formatted = format_reply_for_user(msg.from_user, reply)
    try:
        msg.reply_text(formatted, parse_mode=ParseMode.HTML)
        # যদি খুব বড় হয়, অতিরিক্ত অংশও পাঠাও
        if len(str(reply)) > 4000:
            remaining = str(reply)[4000:]
            msg.reply_text(remaining)
    except Exception as e:
        logger.error("Send failed: %s", e)

# ----------------- main -----------------
def main():
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN সেট করা নেই।")
        return
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("history", history_cmd))
    dp.add_handler(CommandHandler("clearhistory", clearhistory_cmd))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    logger.info("Bot started (polling)")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
