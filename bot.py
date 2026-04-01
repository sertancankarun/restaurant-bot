import os
import random
from datetime import datetime

from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("TOKEN") or "BURAYA_TOKEN"
ADMIN_ID = int(os.getenv("ADMIN_ID") or "BURAYA_ADMIN_ID")

OPEN = 10
CLOSE = 23

MENU_ITEMS = {
    "pizza": 150,
    "burger": 120,
    "ayran": 30,
    "kola": 40,
}

EMOJI = {
    "pizza": "🍕",
    "burger": "🍔",
    "ayran": "🥛",
    "kola": "🥤",
}

users = {}
orders = {}
campaign_text = None

ANA_MENU = ReplyKeyboardMarkup(
    [
        ["🍔 Menü", "🛒 Sepet"],
        ["📍 Adres", "💳 Ödeme"],
        ["🔁 Tekrar", "🗑️ Sil"],
        ["✅ Onay", "❌ İptal"],
    ],
    resize_keyboard=True
)

URUN_MENU = ReplyKeyboardMarkup(
    [
        ["Pizza", "Burger"],
        ["Ayran", "Kola"],
        ["🛒 Sepet", "⬅️ Geri"],
    ],
    resize_keyboard=True
)

ODEME_MENU = ReplyKeyboardMarkup(
    [["Nakit", "Kart"], ["⬅️ Geri"]],
    resize_keyboard=True
)

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "cart": [],
            "address": None,
            "payment": None,
            "name": None,
            "phone": None,
            "waiting_name": False,
            "waiting_phone": False,
            "waiting_address": False,
        }
    return users[uid]

def is_open():
    h = datetime.now().hour
    return OPEN <= h < CLOSE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name

    status = "🟢 Açığız" if is_open() else "🔴 Kapalıyız"

    msg = f"🍔 Hoş geldin {name} 👋\n\n{status} ({OPEN}:00 - {CLOSE}:00)\n\n"

    if campaign_text:
        msg += f"🔥 Kampanya:\n{campaign_text}\n\n"

    msg += "Sipariş vermek için menüyü kullan 👇"

    await update.message.reply_text(msg, reply_markup=ANA_MENU)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.lower()
    raw = update.message.text

    user = get_user(uid)

    if user["waiting_name"]:
        user["name"] = raw
        user["waiting_name"] = False
        user["waiting_phone"] = True
        await update.message.reply_text("📞 Numaran?")
        return

    if user["waiting_phone"]:
        user["phone"] = raw
        user["waiting_phone"] = False
        user["waiting_address"] = True
        await update.message.reply_text("📍 Adres?")
        return

    if user["waiting_address"]:
        user["address"] = raw
        user["waiting_address"] = False
        await update.message.reply_text("Adres kaydedildi ✅", reply_markup=ANA_MENU)
        return

    if "menü" in text:
        await update.message.reply_text("Ne almak istersin? 😋", reply_markup=URUN_MENU)
        return

    if text in MENU_ITEMS:
        user["cart"].append(text)

        responses = [
            f"{EMOJI[text]} {text} sepete eklendi 😋",
            f"{EMOJI[text]} Harika seçim! 🔥",
            f"{EMOJI[text]} Bunu da ekledim 👌"
        ]

        total = sum(MENU_ITEMS[i] for i in user["cart"])

        await update.message.reply_text(
            random.choice(responses) + f"\n💰 Toplam: {total} TL",
            reply_markup=URUN_MENU
        )
        return

    if "sepet" in text:
        total = sum(MENU_ITEMS[i] for i in user["cart"])
        await update.message.reply_text(f"{user['cart']}\n💰 {total} TL")
        return

    if "adres" in text:
        user["waiting_address"] = True
        await update.message.reply_text("Adres yaz:", reply_markup=ReplyKeyboardRemove())
        return

    if "ödeme" in text:
        await update.message.reply_text("Ödeme seç:", reply_markup=ODEME_MENU)
        return

    if text in ["nakit", "kart"]:
        user["payment"] = text
        await update.message.reply_text("Seçildi ✅", reply_markup=ANA_MENU)
        return

    if "onay" in text:
        if not user["name"]:
            user["waiting_name"] = True
            await update.message.reply_text("İsmini yaz:")
            return

        if not user["phone"]:
            user["waiting_phone"] = True
            await update.message.reply_text("Telefon:")
            return

        if not user["address"]:
            user["waiting_address"] = True
            await update.message.reply_text("Adres:")
            return

        if not user["payment"]:
            await update.message.reply_text("Ödeme seç:", reply_markup=ODEME_MENU)
            return

        order_id = random.randint(1000, 9999)
        orders[order_id] = uid

        total = sum(MENU_ITEMS[i] for i in user["cart"])

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍳 Hazırlanıyor", callback_data=f"prep_{order_id}"),
                InlineKeyboardButton("🚗 Yolda", callback_data=f"road_{order_id}")
            ],
            [
                InlineKeyboardButton("✅ Teslim", callback_data=f"done_{order_id}")
            ]
        ])

        await context.bot.send_message(
            ADMIN_ID,
            f"""🚨 SİPARİŞ #{order_id}

👤 {user['name']}
📞 {user['phone']}

🛒 {', '.join(user['cart'])}
💰 {total} TL

📍 {user['address']}""",
            reply_markup=keyboard
        )

        await update.message.reply_text(
            f"🎉 Sipariş alındı {user['name']}!\n🧾 No: {order_id}"
        )

        user["cart"] = []

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    order_id = int(data.split("_")[1])
    uid = orders.get(order_id)

    if not uid:
        return

    if data.startswith("prep"):
        msg = "🍳 Siparişin hazırlanıyor!"
    elif data.startswith("road"):
        msg = "🚗 Siparişin yolda!"
    else:
        msg = "✅ Sipariş teslim edildi!"

    await context.bot.send_message(uid, msg)

# KAMPANYA

async def kampanya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global campaign_text
    if update.effective_user.id != ADMIN_ID:
        return
    campaign_text = " ".join(context.args)
    await update.message.reply_text("Kampanya aktif ✅")

async def kampanya_kapat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global campaign_text
    campaign_text = None
    await update.message.reply_text("Kampanya kapatıldı ❌")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kampanya", kampanya))
    app.add_handler(CommandHandler("kampanya_kapat", kampanya_kapat))
    app.add_handler(MessageHandler(filters.TEXT, handle))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
