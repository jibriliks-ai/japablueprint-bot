
import os, logging, requests
from bs4 import BeautifulSoup
from flask import Flask, request
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import asyncio
import threading

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBSITE = "https://japablueprint.com.ng"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-app.onrender.com/webhook

logging.basicConfig(level=logging.INFO)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# --- WEBSITE BRAIN ---
def get_latest_posts(limit=3):
    try:
        r = requests.get(f"{WEBSITE}/feed/", timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        if "<item>" in r.text:
            soup = BeautifulSoup(r.text, "xml")
            items = soup.find_all("item")[:limit]
            out = []
            for it in items:
                title = it.title.text if it.title else "Post"
                link = it.link.text if it.link else WEBSITE
                out.append(f"• {title}\n{link}")
            return "🔥 Latest from Japablueprint:\n\n" + "\n\n".join(out) + f"\n\nMore 👉 {WEBSITE}"
    except Exception as e:
        logging.error(e)
    try:
        r = requests.get(WEBSITE, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        posts=[]
        for a in soup.select("h2 a, h3 a")[:limit]:
            if a.get_text(strip=True):
                posts.append(f"• {a.get_text(strip=True)}\n{a.get('href')}")
        if posts:
            return "🔥 Latest from Japablueprint:\n\n" + "\n\n".join(posts)
    except:
        pass
    return f"Visit latest guides 👉 {WEBSITE}/blog/"

def ask_ai(question: str) -> str:
    try:
        prompt = f"You are Japablueprint.com.ng AI - expert in Japan, Sweden POF 103140 SEK, Canada, UK, USA visas, jobs abroad. Friendly like Meta AI, bullet points, 2025 info. End with Full guide: {WEBSITE}. Question: {question}"
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"AI busy, visit {WEBSITE} for guides. Error: {e}"

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🇯🇵 Japablueprint AI LIVE!\n\nAsk me anything like Meta AI:\n• Sweden POF 103140?\n• Japan visa\n• Canada Japa\n\nCommands:\n/latest\n/latest @channel\n/post @channel message")

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = None
    if context.args and (context.args[0].startswith("@") or context.args[0].startswith("-100")):
        channel = context.args[0]
    text = get_latest_posts()
    if channel:
        try:
            await context.bot.send_message(chat_id=channel, text=text)
            await update.message.reply_text(f"✅ Posted to {channel}")
        except Exception as e:
            await update.message.reply_text(f"❌ Make me ADMIN in {channel}. Error: {e}")
    else:
        await update.message.reply_text(text)

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args)<2:
        await update.message.reply_text("Use: /post @channel Your message")
        return
    channel = context.args[0]
    msg = " ".join(context.args[1:])
    try:
        await context.bot.send_message(chat_id=channel, text=msg)
        await update.message.reply_text(f"✅ Posted to {channel}")
    except Exception as e:
        await update.message.reply_text(f"❌ Make me ADMIN. Error: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"): return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    ans = ask_ai(update.message.text)
    await update.message.reply_text(ans)

# Build app
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("latest", latest))
application.add_handler(CommandHandler("post", post_cmd))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# Flask for Render free web service
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running ✅"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    # This runs on FREE tier - wakes up when Telegram sends message
    async def process():
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    asyncio.run(process())
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # For Koyeb / Render free WEB SERVICE - use webhook mode
    if WEBHOOK_URL:
        # Set webhook once
        import requests as req
        try:
            req.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}")
            print(f"Webhook set to {WEBHOOK_URL}")
        except: pass
        run_flask()
    else:
        # Local polling mode
        print("Running in polling mode (local)")
        application.run_polling()
