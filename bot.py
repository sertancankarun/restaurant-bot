import os
import random
from datetime import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN") or "BURAYA_TOKEN"
ADMIN_ID = int(os.getenv("ADMIN_ID") or "6741548158")

MENU_ITEMS = {
    "pizza": 150,
    "burger": 120,
    "ayran": 30,
    "kola": 40,
}

users = {}
orders = {}

ANA_MENU = ReplyKeyboardMarkup(
    [
        ["🍔 Menü", "🛒 Sepet"],
        ["📍 Adres", "💳 Ödeme"],
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
    [
        ["Nakit", "Kart"],
        ["⬅️ Geri"],
    ],
    resize_keyboard=True
)

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "cart": [],
            "address": None,
            "payment": None,
            "name": None,
            "phone": None,
            "waiting_address": False,
            "waiting_name": False,
            "waiting_phone": False,
        }
    return users[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍔 Hoş geldin!\nSipariş vermek için menüyü kullan 👇",
        reply_markup=ANA_MENU
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()
    raw = update.message.text

    user = get_user(user_id)

    # isim
    if user["waiting_name"]:
        user["name"] = raw
        user["waiting_name"] = False
        user["waiting_phone"] = True
        await update.message.reply_text("📞 Telefon numaranı yaz:")
        return

    # telefon
    if user["waiting_phone"]:
        user["phone"] = raw
        user["waiting_phone"] = False
        await update.message.reply_text("📍 Adresini gir:")
        user["waiting_address"] = True
        return

    # adres
    if user["waiting_address"]:
        user["address"] = raw
        user["waiting_address"] = False
        await update.message.reply_text("Adres kaydedildi ✅", reply_markup=ANA_MENU)
        return

    if "geri" in text:
        await update.message.reply_text("Ana menü 👇", reply_markup=ANA_MENU)
        return

    if "menü" in text:
        await update.message.reply_text("Ürün seç 👇", reply_markup=URUN_MENU)
        return

    if text in MENU_ITEMS:
        user["cart"].append(text)
        await update.message.reply_text(f"{text} eklendi ✅", reply_markup=URUN_MENU)
        return

    if "sepet" in text:
        if not user["cart"]:
            await update.message.reply_text("Sepet boş")
            return

        total = sum(MENU_ITEMS[i] for i in user["cart"])
        await update.message.reply_text(
            f"{', '.join(user['cart'])}\nToplam: {total} TL"
        )
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
        if not user["cart"]:
            await update.message.reply_text("Sepet boş")
            return

        if not user["name"]:
            user["waiting_name"] = True
            await update.message.reply_text("İsmini yaz:")
            return

        if not user["phone"]:
            user["waiting_phone"] = True
            await update.message.reply_text("Telefonunu yaz:")
            return

        if not user["address"]:
            user["waiting_address"] = True
            await update.message.reply_text("Adres yaz:")
            return

        if not user["payment"]:
            await update.message.reply_text("Ödeme seç:", reply_markup=ODEME_MENU)
            return

        order_id = random.randint(1000, 9999)
        orders[order_id] = user_id

        total = sum(MENU_ITEMS[i] for i in user["cart"])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🧾 {order_id}\n{user['name']} - {user['phone']}\n{', '.join(user['cart'])}\n{total} TL\n{user['address']}"
        )

        await update.message.reply_text(
            f"✅ Sipariş alındı\nNumara: {order_id}"
        )

        users[user_id]["cart"] = []
        return

# ADMIN KOMUTLARI

async def hazirlaniyor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = int(context.args[0])
    user_id = orders.get(order_id)

    if user_id:
        await context.bot.send_message(user_id, "🍳 Siparişin hazırlanıyor!")

async def yolda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = int(context.args[0])
    user_id = orders.get(order_id)

    if user_id:
        await context.bot.send_message(user_id, "🚗 Siparişin yolda!")

async def teslim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = int(context.args[0])
    user_id = orders.get(order_id)

    if user_id:
        await context.bot.send_message(user_id, "✅ Sipariş teslim edildi!")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hazirlaniyor", hazirlaniyor))
    app.add_handler(CommandHandler("yolda", yolda))
    app.add_handler(CommandHandler("teslim", teslim))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    app.run_polling()

if __name__ == "__main__":
    main()
