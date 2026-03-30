import os
from telebot import TeleBot, types

# Replace 'YOUR_BOT_TOKEN_HERE' with your actual token 
# or set it in Render's environment variables as BOT_TOKEN
TOKEN = os.getenv('BOT_TOKEN', '8771123401:AAHhv3aZO8WYmzDiSdbE4YPj_WvdKbEPz00')
bot = TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    # Welcome Message
    welcome_text = (
        "👋 **Welcome to the Hub!**\n\n"
        "Your all-in-one station for coin management and airdrops. "
        "Select an option below to get started."
    )
    
    # Building the Keyboard Layout from your image
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    btn1 = types.KeyboardButton("🚀 Launch Coin")
    btn2 = types.KeyboardButton("📊 Transactions")
    btn3 = types.KeyboardButton("🎁 Airdrop")
    btn4 = types.KeyboardButton("🔑 Wallet")
    btn5 = types.KeyboardButton("📜 Logs")
    btn6 = types.KeyboardButton("❓ Help")
    btn7 = types.KeyboardButton("💬 Feedback")
    
    # Adding buttons in rows to match the screenshot
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.row(btn7)
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    bot.reply_to(message, "⚙️ This feature is currently under development. Stay tuned!")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
