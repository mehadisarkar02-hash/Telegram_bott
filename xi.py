#!/usr/bin/env python3

#!/usr/bin/env python3
# telegram_deepai_polling.py
# Requirements: python-telegram-bot==13.15, requests

import os, json, time, logging, requests
from pathlib import Path
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

#================ CONFIG =================

সরাসরি টোকেন বসানো (তুমি চাইলে শুধুমাত্র হোস্টিং/লোকাল টেস্টের জন্য)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8273934695:AAFlM1x5Jf3ukA3pROoDhGrYXJ3SKCamSlQ")

এডমিন চ্যাট আইডি (এখানে নিজের Telegram ID বসাও বা ENV থেকে সেট করো)

উদাহরণ: ADMIN_CHAT_ID = 7552513938

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "7552513938"))

DeepAI API key (env var না থাকলে demo key ব্যবহার হবে)

DEEPAI_API_KEY = os.getenv( "DEEPAI_API_KEY", "tryit-99974563413-d55b1638b9f7372403addba76651d2e5" )

DeepAI URL

DEEPAI_URL = os.getenv( "DEEPAI_URL", "https://api.deepai.org/hacking_is_a_serious_crime" )

HISTORY_FILE = Path("histories.json") MAX_HISTORY_PER_CHAT = 25

==========================================

LOGGING

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') logger = logging.getLogger(name)

HISTORY helpers

def load_histories(): if HISTORY_FILE.exists(): try: return json.loads(HISTORY_FILE.read_text(encoding="utf-8")) except: return {} return {}

def save_histories(h): try: HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8") except Exception as e: logger.warning("Failed to save histories: %s", e)

histories = load_histories()

def append_user_message(chat_id, text): h = histories.get(chat_id, []) h.append({"role":"user","content": text}) histories[chat_id] = h[-MAX_HISTORY_PER_CHAT:] save_histories(histories)

def append_assistant_message(chat_id, text): h = histories.get(chat_id, []) h.append({"role":"assistant","content": text}) histories[chat_id] = h[-MAX_HISTORY_PER_CHAT:] save_histories(histories)

utility: nice formatting for replies

def format_reply_for_user(user, text): # সংক্ষিপ্তকরণ: খুব বড় উত্তর হলে অংশে পাঠাও MAX_CHUNK = 4000 header = f"<b>FESA-AI</b> — তোমার ব্যক্তিগত সহায়ক " header += f"<i>{user.first_name if user.first_name else 'বন্ধু'}</i>, আমি তোমার প্রশ্নটি পেয়েছি — ({datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC)

" footer = "

— <i>Falcon-X Elite Security Asia (FESA)</i> Silent. Swift. Secure." body = str(text) if len(body) <= MAX_CHUNK: return header + body + footer # যদি বড় হয়, প্রথম অংশ পাঠাই এবং বাকিটা আলাদা মেসেজে পাঠানোর জন্য রিটার্ন করি return header + body[:MAX_CHUNK] + "

(পরবর্তী অংশ...)" + footer

DeepAI call

def call_deepai(chat_id): if chat_id not in histories: return "আমি প্রস্তুত — এখনো কোনো history নেই।" data = { "chat_style":"chat", "chatHistory": json.dumps(histories[chat_id], ensure_ascii=False), "model":"standard", "hacker_is_stinky":"very_stinky", "enabled_tools": '["image_generator"]' } headers = {"api-key": DEEPAI_API_KEY, "User-Agent":"telegram-deepai-bot/1.0"} try: resp = requests.post(DEEPAI_URL, headers=headers, data=data, timeout=25) except requests.RequestException as e: logger.error("DeepAI request failed: %s", e) return f"Request failed: {e}" if resp.status_code != 200: logger.warning("DeepAI status %s", resp.status_code) # try to pull message from JSON try: j = resp.json() if isinstance(j, dict) and j.get("message"): return j.get("message") except: pass return f"Server error ({resp.status_code})" body = resp.text.strip() # parse JSON if possible if body.startswith("{") or "application/json" in resp.headers.get("content-type",""): try: j = resp.json() if isinstance(j, dict): if isinstance(j.get("message"), str): return j["message"] elif isinstance(j.get("data"), dict): return json.dumps(j["data"], ensure_ascii=False) return json.dumps(j, ensure_ascii=False) except: return body return body

Telegram handlers

def start(update: Update, context: CallbackContext): user = update.effective_user chat_id = str(update.effective_chat.id) # সুন্দর স্টার্ট মেসেজ welcome = ( f"<b>আসসালামু আলাইকুম {user.first_name if user.first_name else ''}!</b>

" "আমি তোমার FESA-AI বট — যেকোনো মেসেজ পাঠাও, আমি চেষ্টা করে উত্তর দিব। " "টীকা: ব্যক্তিগত/গোপন তথ্য এখানে পাঠাবেন না।" ) try: update.message.reply_text(welcome, parse_mode=ParseMode.HTML) except Exception as e: logger.error("Failed to send welcome: %s", e) # এডমিনকে নোটিফাই কর try: admin_text = ( f"🔔 <b>নোটিফিকেশন</b> " f"ব্যবহারকারী শুরু করলো: <b>{user.full_name}</b> " f"ইউজারনেম: @{user.username if user.username else 'N/A'} " f"চ্যাট আইডি: {chat_id} " f"সময় (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}" ) context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode=ParseMode.HTML) except Exception as e: logger.warning("Failed to notify admin (%s): %s", ADMIN_CHAT_ID, e)

def help_cmd(update: Update, context: CallbackContext): help_text = ( "প্রশ্ন পাঠান — আমি তোমাকে উত্তর দেব।

" "কিছু টিপস: " "• স্পষ্টভাবে লিখো (যেমন: 'পাইথনে ফাইল কিভাবে পড়ব?') " "• যদি কোড পাঠাও, কোড ব্লক হিসাবে পাঠাও। " ) update.message.reply_text(help_text)

def handle_message(update: Update, context: CallbackContext): msg = update.message chat_id = str(msg.chat_id) text = msg.text or "" logger.info("Msg from %s: %s", chat_id, text[:200]) append_user_message(chat_id, text) reply = call_deepai(chat_id) append_assistant_message(chat_id, reply)

# সুন্দর করে ফরম্যাট করে পাঠাও; যদি বড় হয়, ভাগ করে পাঠাও
formatted = format_reply_for_user(msg.from_user, reply)
try:
    msg.reply_text(formatted, parse_mode=ParseMode.HTML)
    # যদি মূল উত্তর অনেক বড় হয় এবং কাটা হয়ে থাকে, বাকিটা আলাদা পাঠাতে পারো
    MAX_CHUNK = 4000
    if len(str(reply)) > MAX_CHUNK:
        remaining = str(reply)[MAX_CHUNK:]
        msg.reply_text(remaining)
except Exception as e:
    logger.error("Send failed: %s", e)

def main(): if not TELEGRAM_TOKEN: print("Error: TELEGRAM_TOKEN সেট করো (env var) অথবা কোডে বসাও।") return updater = Updater(token=TELEGRAM_TOKEN, use_context=True) dp = updater.dispatcher dp.add_handler(CommandHandler("start", start)) dp.add_handler(CommandHandler("help", help_cmd)) dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message)) print("Bot started (polling)") updater.start_polling() updater.idle()

if name == "main": main()