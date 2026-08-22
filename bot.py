import logging
import aiosqlite
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
ApplicationBuilder, CommandHandler, CallbackQueryHandler,
MessageHandler, ContextTypes, filters, ConversationHandler
)

================= 1. CONFIGURATION =================

BOT_TOKEN = "8722471013:AAEVe52lDg3S1vGuvfDflyReg2R80-ruevs
"
ADMIN_CHAT_ID = 8889447610
TELEBIRR_NUMBER = "0955894342"
TELEBIRR_NAME = "Firaol"
CONTACT_SUPPORT_USER = "@ZTETOPUP"
DB_NAME = "zte_bot.db"

logging.basicConfig(
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
level=logging.INFO
)

Conversation States
(CHOOSING_PRODUCT, WAITING_FOR_UID, CONFIRMING_ORDER, WAITING_FOR_RECEIPT) = range(4)


================= 2. API & DATABASE LOGIC =================

async def get_ff_nickname(uid: str):
"""Free Fire ID Checker API Function"""
api_url = f"https://ff-api-check.vercel.app/api/ff?uid={uid}"

try:
async with aiohttp.ClientSession() as session:
async with session.get(api_url, timeout=5) as response:
if response.status == 200:
data = await response.json()
return (
data.get("nickname")
or data.get("name")
or data.get("PlayerName")
)
except Exception as e:
logging.error(f"ID Check Error: {e}")

return None


async def init_db():
"""Initialize Database and ensure all columns exist."""

async with aiosqlite.connect(DB_NAME) as db:

await db.execute('''
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
username TEXT,
wallet_balance REAL DEFAULT 0.0,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

await db.execute('''
CREATE TABLE IF NOT EXISTS orders (
order_id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
game TEXT,
product_name TEXT,
uid TEXT,
nickname TEXT DEFAULT 'N/A',
amount REAL,
payment_status TEXT DEFAULT 'Awaiting Payment',
order_status TEXT DEFAULT 'Pending',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

try:
await db.execute(
"ALTER TABLE orders ADD COLUMN nickname TEXT DEFAULT 'N/A'"
)
except Exception:
pass

await db.commit()


async def db_add_user(user_id: int, username: str):

async with aiosqlite.connect(DB_NAME) as db:
await db.execute(
'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
(user_id, username)
)
await db.commit()


async def db_get_wallet(user_id: int) -> float:

async with aiosqlite.connect(DB_NAME) as db:
async with db.execute(
'SELECT wallet_balance FROM users WHERE user_id = ?',
(user_id,)
) as cursor:

row = await cursor.fetchone()
return row[0] if row else 0.0


async def db_create_order(
user_id: int,
game: str,
product_name: str,
uid: str,
nickname: str,
amount: float
) -> int:

async with aiosqlite.connect(DB_NAME) as db:

cursor = await db.execute('''
INSERT INTO orders
(user_id, game, product_name, uid, nickname, amount)
VALUES (?, ?, ?, ?, ?, ?)
''', (
user_id,
game,
product_name,
uid,
nickname,
amount
))

await db.commit()
return cursor.lastrowid


async def db_get_orders(user_id: int):

async with aiosqlite.connect(DB_NAME) as db:

async with db.execute('''
SELECT order_id, game, product_name, amount, uid, order_status
FROM orders
WHERE user_id = ?
ORDER BY order_id DESC
LIMIT 5
''', (user_id,)) as cursor:

return await cursor.fetchall()


================= 3. BOT HANDLERS =================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

user = update.effective_user

username = user.username if user.username else user.first_name

await db_add_user(user.id, username)

text = (
"<b>✨ Welcome to ZTE TOPUP Bot! ✨</b>\n\n"
"Explore our products, games, check your orders, and get the best deals right here.\n\n"
"👇 <b>Choose an option below:</b>"
)

keyboard = [
[
InlineKeyboardButton(
"🛍️ PRODUCTS",
callback_data="products"
)
 ],
[
InlineKeyboardButton(
"🛒 MY CART",
callback_data="cart"
),
InlineKeyboardButton(
"💰 MY WALLET",
callback_data="wallet"
)
 ],
[
InlineKeyboardButton(
"📦 ORDERS",
callback_data="orders"
),
InlineKeyboardButton(
"🎧 CONTACT SUPPORT",
callback_data="support"
)
 ]
]

reply_markup = InlineKeyboardMarkup(keyboard)

if update.message:

await update.message.reply_text(
text,
reply_markup=reply_markup,
parse_mode="HTML"
)

else:

await update.callback_query.message.edit_text(
text,
reply_markup=reply_markup,
parse_mode="HTML"
)


async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

balance = await db_get_wallet(query.from_user.id)

text = f"💰 <b>Wallet Balance:</b> {balance:.2f} ETB"

keyboard = [
[
InlineKeyboardButton(
"➕ ADD FUNDS",
callback_data="add_funds"
)
 ],
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="main_menu"
)
 ]
]

await query.message.edit_text(
text,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode="HTML"
)


async def add_funds_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

text = (
"💳 <b>Payment Access & Deposit Instructions</b>\n\n"
"To deposit money into your bot wallet:\n"
f"1. Transfer your desired amount to Telebirr:\n"
f" • <b>Number:</b> <code>{TELEBIRR_NUMBER}</code>\n"
f" • <b>Name:</b> <b>{TELEBIRR_NAME}</b>\n\n"
f"2. Send the transaction <b>Receipt / Screenshot</b> to {CONTACT_SUPPORT_USER}.\n"
"3. Your wallet balance will be updated instantly by Admin!"
)

keyboard = [
[
InlineKeyboardButton(
"🔙 BACK TO WALLET",
callback_data="wallet"
)
 ]
]

await query.message.edit_text(
text,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode="HTML"
)


async def orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

orders = await db_get_orders(query.from_user.id)

if not orders:

text = "📦 <b>ምንም ዓይነት የቀድሞ Order የለዎትም።</b>"

else:

text = "📦 <b>የቀድሞ Orders ዝርዝር:</b>\n\n"

for ord_id, game, prod, amt, uid, status in orders:

text += (
f"🔹 <b>Order #{ord_id}</b>\n"
f"🎮 {game}\n"
f"💎 {prod}\n"
f"💰 {amt} ETB\n"
f"🆔 Target: <code>{uid}</code>\n"
f"Status: <b>{status}</b>\n"
f"━━━━━━━━━━━━━━\n"
)

keyboard = [
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="main_menu"
)
 ]
]

await query.message.edit_text(
text,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode="HTML"
)


async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

support_link = (
f"https://t.me/{CONTACT_SUPPORT_USER.replace('@', '')}"
)

keyboard = [
[
InlineKeyboardButton(
"💬 Chat with Support",
url=support_link
)
 ],
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="main_menu"
)
 ]
]

await query.message.edit_text(
"🎧 <b>Customer Support</b>\n\n"
"ለማንኛውም ጥያቄ ወይም እርዳታ ከታች ያለውን አዝራር ተጭነው ያግኙን።",
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode="HTML"
)


async def products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

keyboard = [
[
InlineKeyboardButton(
"🔧 MANUAL",
callback_data="manual"
),
InlineKeyboardButton(
"⚡ INSTANT",
callback_data="instant"
)
 ],
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="main_menu"
)
 ]
]

await query.message.edit_text(
"Choose Manual or Instant:",
reply_markup=InlineKeyboardMarkup(keyboard)
)


async def instant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

keyboard = [
[
InlineKeyboardButton(
"🎟️ VOUCHER",
callback_data="voucher"
),
InlineKeyboardButton(
"🆔 AUTO ID",
callback_data="auto_id"
)
 ],
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="products"
)
 ]
]

await query.message.edit_text(
"Choose instant type:",
reply_markup=InlineKeyboardMarkup(keyboard)
)


async def auto_id_games(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

keyboard = [
[
InlineKeyboardButton(
"🔥 FREE FIRE MIDDLE EAST",
callback_data="ff_me"
)
 ],
[
InlineKeyboardButton(
"🎮 PUBG MOBILE",
callback_data="pubg"
)
 ],
[
InlineKeyboardButton(
"⭐ TELEGRAM STARS & PREMIUM",
callback_data="tg_prem"
)
 ],
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="instant"
)
 ]
]

await query.message.edit_text(
"Select a game / service:",
reply_markup=InlineKeyboardMarkup(keyboard)
)


================= FREE FIRE =================

async def ff_products(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

context.user_data['game'] = 'Free Fire'

keyboard = [
[
InlineKeyboardButton(
"🌐 110 DIAMOND → 187 ETB",
callback_data="prod_110 DIAMOND_187"
)
 ],
[
InlineKeyboardButton(
"💎 221 DIAMOND → 372 ETB",
callback_data="prod_221 DIAMOND_372"
)
 ],
[
InlineKeyboardButton(
"💎 331 DIAMOND → 552 ETB",
callback_data="prod_331 DIAMOND_552"
)
 ],
[
InlineKeyboardButton(
"💎 583 DIAMOND → 917 ETB",
callback_data="prod_583 DIAMOND_917"
)
 ],
[
InlineKeyboardButton(
"💎 1,160 DIAMOND → 1,832 ETB",
callback_data="prod_1160 DIAMOND_1832"
)
 ],
[
InlineKeyboardButton(
"💎 2,340 DIAMOND → 3,662 ETB",
callback_data="prod_2340 DIAMOND_3662"
)
 ],
[
InlineKeyboardButton(
"🚀 Lv 6 (120 💎) → 95 ETB",
callback_data="prod_Lv 6 Pass_95"
)
 ],
[
InlineKeyboardButton(
"🚀 Lv 30 (350 💎) → 277 ETB",
callback_data="prod_Lv 30 Pass_277"
)
 ],
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="auto_id"
)
 ]
]

await query.message.edit_text(
"Select Free Fire Product:",
reply_markup=InlineKeyboardMarkup(keyboard)
)

return CHOOSING_PRODUCT


================= PUBG =================

async def pubg_products(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

context.user_data['game'] = 'PUBG Mobile'

keyboard = [
[
InlineKeyboardButton(
"🎫 60 UC → 185 ETB",
callback_data="prod_60 UC_185"
)
 ],
[
InlineKeyboardButton(
"🪙 60 WOW Coins → 240 ETB",
callback_data="prod_60 WOW Coins_240"
)
 ],
[
InlineKeyboardButton(
"📦 First Purchase Pack → 250 ETB",
callback_data="prod_First Purchase Pack_250"
)
 ],
[
InlineKeyboardButton(
"👑 Prime (1 Month) → 250 ETB",
callback_data="prod_Prime 1Mo_250"
)
 ],
[
InlineKeyboardButton(
"📦 Weekly Deal Pack 1 → 270 ETB",
callback_data="prod_Weekly Deal Pack 1_270"
)
 ],
[
InlineKeyboardButton(
"🔫 Upgradable Firearm Materials Pack → 600 ETB",
callback_data="prod_Firearm Pack_600"
)
 ],
[
InlineKeyboardButton(
"👑 Prime (3 Months) → 700 ETB",
callback_data="prod_Prime 3Mo_700"
)
 ],
[
InlineKeyboardButton(
"📦 Weekly Deal Pack 2 → 800 ETB",
callback_data="prod_Weekly Deal Pack 2_800"
)
 ],
[
InlineKeyboardButton(
"🎖️ Weekly Mythic Emblem Value Pack → 800 ETB",
callback_data="prod_Mythic Emblem Val_800"
)
 ],
[
InlineKeyboardButton(
"🎫 325 UC → 880 ETB",
callback_data="prod_325 UC_880"
)
 ],
[
InlineKeyboardButton(
"🪙 325 WOW Coins → 920 ETB",
callback_data="prod_325 WOW Coins_920"
)
 ],
[
InlineKeyboardButton(
"🎖️ Mythic Emblem Pack → 950 ETB",
callback_data="prod_Mythic Emblem Pack_950"
)
 ],
[
InlineKeyboardButton(
"👑 Prime (6 Months) → 1,200 ETB",
callback_data="prod_Prime 6Mo_1200"
)
 ],
[
InlineKeyboardButton(
"🎟️ Elite Pass LV1-50 → 1,250 ETB",
callback_data="prod_Elite Pass LV1-50_1250"
)
 ],
[
InlineKeyboardButton(
"🎫 660 UC → 1,750 ETB",
callback_data="prod_660 UC_1750"
)
 ],
[
InlineKeyboardButton(
"🌟 Prime Plus (1 Month) → 1,850 ETB",
callback_data="prod_Prime Plus 1Mo_1850"
)
 ],
[
InlineKeyboardButton(
"🪙 660 WOW Coins → 2,100 ETB",
callback_data="prod_660 WOW Coins_2100"
)
 ],
[
InlineKeyboardButton(
"👑 Prime (12 Months) → 2,300 ETB",
callback_data="prod_Prime 12Mo_2300"
)
 ],
[
InlineKeyboardButton(
"🎟️ Elite Pass LV1-100 → 2,450 ETB",
callback_data="prod_Elite Pass LV1-100_2450"
)
 ],
[
InlineKeyboardButton(
"🔙 BACK",
callback_data="auto_id"
)
 ]
]

await query.message.edit_text(
"Select PUBG Mobile Product:",
reply_markup=InlineKeyboardMarkup(keyboard)
)

return CHOOSING_PRODUCT


================= TELEGRAM STARS & PREMIUM =================
ONLY THE STARS PRICES HAVE BEEN CHANGED

async def tg_products(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

context.user_data['game'] = 'Telegram'

keyboard = [
[InlineKeyboardButton(
"⭐ 50 Stars → 300 ETB",
callback_data="prod_50 Stars_300"
)],

[InlineKeyboardButton(
"⭐ 75 Stars → 450 ETB",
callback_data="prod_75 Stars_450"
)],

[InlineKeyboardButton(
"⭐ 100 Stars → 600 ETB",
callback_data="prod_100 Stars_600"
)],

[InlineKeyboardButton(
"⭐ 150 Stars → 900 ETB",
callback_data="prod_150 Stars_900"
)],

[InlineKeyboardButton(
"⭐ 250 Stars → 1500 ETB",
callback_data="prod_250 Stars_1500"
)],

[InlineKeyboardButton(
"⭐ 350 Stars → 2100 ETB",
callback_data="prod_350 Stars_2100"
)],

[InlineKeyboardButton(
"⭐ 500 Stars → 3000 ETB",
callback_data="prod_500 Stars_3000"
)],

[InlineKeyboardButton(
"⭐ 750 Stars → 4500 ETB",
callback_data="prod_750 Stars_4500"
)],

[InlineKeyboardButton(
"⭐ 1000 Stars → 6000 ETB",
callback_data="prod_1000 Stars_6000"
)],

[InlineKeyboardButton(
"⭐ 1500 Stars → 9000 ETB",
callback_data="prod_1500 Stars_9000"
)],

[InlineKeyboardButton(
"⭐ 2500 Stars → 15000 ETB",
callback_data="prod_2500 Stars_15000"
)],

# Premium prices remain exactly as before
[InlineKeyboardButton(
"👑 3 Months Premium → 2,650 ETB",
callback_data="prod_3Mo Premium_2650"
)],

[InlineKeyboardButton(
"👑 6 Months Premium → 3,600 ETB",
callback_data="prod_6Mo Premium_3600"
)],

[InlineKeyboardButton(
"👑 12 Months Premium → 6,500 ETB",
callback_data="prod_12Mo Premium_6500"
)],

[InlineKeyboardButton(
"🔙 BACK",
callback_data="auto_id"
)]
]

await query.message.edit_text(
"Select Telegram Package:",
reply_markup=InlineKeyboardMarkup(keyboard)
)

return CHOOSING_PRODUCT


================= ASK UID =================

async def ask_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):

query = update.callback_query
await query.answer()

parts = query.data.rsplit("_", 2)

context.user_data['selected_product'] = parts[1]
context.user_data['price'] = float(parts[2])

game_name = context.user_data.get(
'game',
'Game'
)

prompt_text = (
"Please enter your Telegram Username "
"(e.g. @username):"
if game_name == "Telegram"
else f"Please enter your {game_name} UID:"
)

await query.message.edit_text(prompt_text)

return WAITING_FOR_UID


================= VALIDATE UID =================

async def validate_and_summary(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

uid = update.message.text.strip()

game = context.user_data.get(
'game',
'Game'
)

if game == "Telegram":

if not uid.startswith("@") or len(uid) < 3:

await update.message.reply_text(
"⚠️ <b>የተሳሳተ Telegram Username!</b>\n"
"እባክዎን ከ <code>@</code> ጋር ያስገቡ "
"(ምሳሌ: @username):",
parse_mode="HTML"
)

return WAITING_FOR_UID

else:

if not (
uid.isdigit()
and 5 <= len(uid) <= 15
):

await update.message.reply_text(
"⚠️ <b>የተሳሳተ Game UID!</b>\n"
"እባክዎን ትክክለኛ ቁጥር ብቻ ያስገቡ:",
parse_mode="HTML"
)

return WAITING_FOR_UID

nickname = "N/A"

if game == "Free Fire":

loading_msg = await update.message.reply_text(
"🔍 <b>Game ID እየተረጋገጠ ነው...</b>",
parse_mode="HTML"
)

fetched_name = await get_ff_nickname(uid)

if fetched_name:
nickname = fetched_name

await loading_msg.delete()

context.user_data['uid'] = uid
context.user_data['nickname'] = nickname

prod = context.user_data.get(
'selected_product'
)

price = context.user_data.get(
'price'
)

id_label = (
"Username"
if game == "Telegram"
else "UID"
)

text = (
"📦 <b>Order Summary</b>\n\n"
f"🎮 <b>Service:</b> {game}\n"
f"👤 <b>Account Name:</b> "
f"<code>{nickname}</code>\n"
f"🆔 <b>{id_label}:</b> "
f"<code>{uid}</code>\n"
f"💎 <b>Product:</b> {prod}\n"
f"💰 <b>Price:</b> {price} ETB"
)

keyboard = [
[
InlineKeyboardButton(
"💳 CHECKOUT",
callback_data="checkout"
)
 ],
[
InlineKeyboardButton(
"🔙 CANCEL",
callback_data="auto_id"
)
 ]
]

await update.message.reply_text(
text,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode="HTML"
)

return CONFIRMING_ORDER


================= CHECKOUT =================

async def checkout(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

query = update.callback_query
await query.answer()

uid = context.user_data.get('uid')

nickname = context.user_data.get(
'nickname',
'N/A'
)

game = context.user_data.get(
'game',
'Game'
)

prod = context.user_data.get(
'selected_product'
)

price = context.user_data.get(
'price',
0.0
)

try:

order_id = await db_create_order(
query.from_user.id,
game,
prod,
uid,
nickname,
price
)

context.user_data['order_id'] = order_id

except Exception as e:

logging.error(
f"Checkout Error: {e}"
)

await query.message.edit_text(
"⚠️ <b>ስህተት ተፈጥሯል!</b>\n\n"
"እባክዎን /start ይበሉ።",
parse_mode="HTML"
)

return CONFIRMING_ORDER

payment_info = (
f"📱 <b>የክፍያ መንገድ: Telebirr</b>\n\n"
f"🔍 <b>Order Summary (#Order {order_id})</b>\n"
f"🎮 <b>አገልግሎት:</b> {game}\n"
f"💎 <b>ምርት:</b> {prod}\n"
f"🆔 <b>Target:</b> <code>{uid}</code>\n"
f"💰 <b>የሚከፍሉት ብር:</b> "
f"<b>{price} ETB</b>\n\n"
f"━━━━━━━━━━━━━━━━━━━━\n"
f"📲 <b>የ Telebirr ሂሳብ መረጃ:</b>\n"
f"• የስልክ ቁጥር: "
f"<code>{TELEBIRR_NUMBER}</code>\n"
f"• ስም: <b>{TELEBIRR_NAME}</b>\n"
f"━━━━━━━━━━━━━━━━━━━━\n\n"
f"⚠️ <b>ማሳሰቢያ:</b> "
f"ክፍያውን በ Telebirr ከፈጸሙ በኋላ "
f"የክፍያውን <b>Screenshot "
f"(ደረሰኝ) ፎቶ</b> እዚህ ይላኩ!"
)

await query.message.edit_text(
payment_info,
parse_mode="HTML"
)

return WAITING_FOR_RECEIPT


================= RECEIVE RECEIPT =================

async def receive_receipt(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

user = update.effective_user

photo = update.message.photo[-1].file_id

order_id = context.user_data.get(
'order_id'
)

game = context.user_data.get(
'game',
'Game'
)

uid = context.user_data.get(
'uid'
)

nickname = context.user_data.get(
'nickname',
'N/A'
)

prod = context.user_data.get(
'selected_product'
)

await update.message.reply_text(
"⏳ <b>ደረሰኝዎ ተቀብለናል! "
"በአድሚን እየተረጋገጠ ነው። "
"በጥቂት ደቂቃዎች ውስጥ ይላካል።</b>",
parse_mode="HTML"
)

username = (
f"@{user.username}"
if user.username
else "No Username"
)

caption = (
f"📥 <b>አዲስ የ TOPUP ትዕዛዝ "
f"(#Order {order_id})!</b>\n\n"
f"👤 <b>ተጠቃሚ:</b> "
f"{username} "
f"(ID: <code>{user.id}</code>)\n"
f"🎮 <b>አገልግሎት:</b> {game}\n"
f"👤 <b>Account Name:</b> "
f"<code>{nickname}</code>\n"
f"💎 <b>ምርት:</b> {prod}\n"
f"🆔 <b>Target ID/Username:</b> "
f"<code>{uid}</code>"
)

keyboard = [
[
InlineKeyboardButton(
"✅ Approve & Send",
callback_data=(
f"approve_{order_id}{user.id}{uid}"
)
)
 ],
[
InlineKeyboardButton(
"❌ Reject",
callback_data=(
f"reject_{order_id}_{user.id}"
)
)
 ]
]

await context.bot.send_photo(
chat_id=ADMIN_CHAT_ID,
photo=photo,
caption=caption,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode="HTML"
)

return ConversationHandler.END


================= RECEIPT ERROR =================

async def receipt_error(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

await update.message.reply_text(
"⚠️ <b>እባክዎን የክፍያውን "
"Screenshot (ፎቶ) ብቻ ይላኩ! "
"ጽሁፍ አይፈቀድም።</b>",
parse_mode="HTML"
)

return WAITING_FOR_RECEIPT


================= ADMIN ACTION =================

async def admin_action_callback(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

query = update.callback_query
await query.answer()

data = query.data.split("_")

action = data[0]
order_id = data[1]

if action == "approve":

user_id = data[2]
uid = "_".join(data[3:])

await query.edit_message_caption(
caption=(
f"✅ <b>Order #{order_id} "
f"ተፈጽሟል!</b>\n"
f"Target: <code>{uid}</code> "
f"በአድሚን ጸድቋል።"
),
parse_mode="HTML"
)

success_message = (
"🎉 <b>ውድ ደንበኞቻችን "
"ግብይትዎ ተጠናቋል!</b>\n\n"
"እኛን <b>ZTE TOPUP</b> "
"ስለመረጡ ከልብ እናመሰግናለን።\n\n"
"ሌላ ግብይት መፈጸም ከፈለጉ "
"የሁል ጊዜ ምርጫዎ "
"<b>ZTE TOPUP</b> እናንተ ጋር ነው! ❤️\n\n"
"🔄 አዲስ ትዕዛዝ ለመጀመር "
"ከታች ያለውን ይጫኑ:\n"
"/start"
)

await context.bot.send_message(
chat_id=int(user_id),
text=success_message,
parse_mode="HTML"
)

elif action == "reject":

user_id = data[2]

await query.edit_message_caption(
caption=(
f"❌ <b>Order #{order_id} "
f"በአድሚን ተሰርዟል።</b>"
),
parse_mode="HTML"
)

await context.bot.send_message(
chat_id=int(user_id),
text=(
f"❌ <b>Order #{order_id} "
f"ውድቅ ተደርጓል። "
f"እባክዎን Support ያግኙ።</b>"
),
parse_mode="HTML"
)


================= POST INIT =================

async def post_init(application):

await init_db()


================= EXECUTION =================

def main():

app = (
ApplicationBuilder()
.token(BOT_TOKEN)
.post_init(post_init)
.build()
)

order_conv = ConversationHandler(

entry_points=[

CallbackQueryHandler(
ff_products,
pattern=r"^ff_me$`"
),

CallbackQueryHandler(
pubg_products,
pattern=r"^pubg`$"
),

CallbackQueryHandler(
tg_products,
pattern=r"^tg_prem$`"
)
],

states={

CHOOSING_PRODUCT: [

CallbackQueryHandler(
ask_uid,
pattern=r"^prod_"
)
],

WAITING_FOR_UID: [

MessageHandler(
filters.TEXT & ~filters.COMMAND,
validate_and_summary
)
],

CONFIRMING_ORDER: [

CallbackQueryHandler(
checkout,
pattern=r"^checkout`$"
)
],

WAITING_FOR_RECEIPT: [

MessageHandler(
filters.PHOTO,
receive_receipt
),

MessageHandler(
filters.TEXT & ~filters.COMMAND,
receipt_error
)
]
},

fallbacks=[
CommandHandler(
'start',
start_command
),

CallbackQueryHandler(
auto_id_games,
pattern=r"^auto_id$`"
)
],

allow_reentry=True
)

app.add_handler(
CommandHandler(
'start',
start_command
)
)

app.add_handler(order_conv)

app.add_handler(
CallbackQueryHandler(
start_command,
pattern=r"^main_menu`$"
)
)

app.add_handler(
CallbackQueryHandler(
products_menu,
pattern=r"^products$`"
)
)

app.add_handler(
CallbackQueryHandler(
instant_menu,
pattern=r"^instant`$"
)
)

app.add_handler(
CallbackQueryHandler(
auto_id_games,
pattern=r"^auto_id$`"
)
)

app.add_handler(
CallbackQueryHandler(
wallet_handler,
pattern=r"^wallet`$"
)
)

app.add_handler(
CallbackQueryHandler(
add_funds_handler,
pattern=r"^add_funds$`"
)
)

app.add_handler(
CallbackQueryHandler(
orders_handler,
pattern=r"^orders`$"
)
)

app.add_handler(
CallbackQueryHandler(
support_handler,
pattern=r"^support$"
)
)

app.add_handler(
CallbackQueryHandler(
admin_action_callback,
pattern=r"^(approve_|reject_)"
)
)

print(
"🤖 ZTE TOPUP Bot is running successfully..."
)

app.run_polling()


if name == 'main':
main
