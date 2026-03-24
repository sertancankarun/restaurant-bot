import os
import csv
import random
from datetime import datetime
from collections import Counter

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
IBAN = os.getenv("IBAN", "")
ALICI = os.getenv("ALICI", "RESTORAN ADI")
ORDERS_FILE = "orders.csv"

MENU = {
    "pizza": 150,
    "burger": 120,
    "wrap": 100,
    "ayran": 30,
    "kola": 40,
}

EMOJIS = {
    "pizza": "🍕",
    "burger": "🍔",
    "wrap": "🌯",
    "ayran": "🥛",
    "kola": "🥤",
}

UPSELL = {
    "pizza": "ayran",
    "burger": "kola",
    "wrap": "ayran",
}

kullanicilar = {}

def init_user(uid):
    if uid not in kullanicilar:
        kullanicilar[uid] = {
            "cart": [],
            "address": "",
            "note": "",
            "payment": "",
            "last_order": [],
            "waiting_address": False,
            "waiting_note": False,
        }

def reset_flags(uid):
    kullanicilar[uid]["waiting_address"] = False
    kullanicilar[uid]["waiting_note"] = False

def ensure_orders_file():
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["order_id","timestamp","items","total","address","note","payment"])

def cart_total(uid):
    return sum(MENU[i] for i in kullanicilar[uid]["cart"])

def cart_text(uid):
    cart = kullanicilar[uid]["cart"]
    if not cart:
        return "Sepetin boş."
    text = ""
    for i in cart:
        text += f"{EMOJIS[i]} {i} - {MENU[i]} TL\n"
    return text + f"\n💰 Toplam: {cart_total(uid)} TL"

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 Menü", callback_data="menu")],
        [InlineKeyboardButton("⚡ Hızlı Menü", callback_data="quick")],
        [InlineKeyboardButton("🛒 Sepet", callback_data="cart")],
        [InlineKeyboardButton("📍 Adres", callback_data="address")],
        [InlineKeyboardButton("💳 Ödeme", callback_data="payment")],
        [InlineKeyboardButton("✅ Onayla", callback_data="confirm")],
        [InlineKeyboardButton("❌ İptal", callback_data="cancel")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    init_user(uid)
    await update.message.reply_text("Hoş geldin 😄", reply_markup=main_menu())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    init_user(uid)
    user = kullanicilar[uid]

    if q.data == "menu":
        buttons = []
        for i in MENU:
            buttons.append([InlineKeyboardButton(f"{i} - {MENU[i]} TL", callback_data=f"add_{i}")])
        await q.message.reply_text("Menü:", reply_markup=InlineKeyboardMarkup(buttons))

    elif q.data.startswith("add_"):
        urun = q.data.split("_")[1]
        user["cart"].append(urun)

        if urun in UPSELL:
            oneri = UPSELL[urun]
            await q.message.reply_text(
                f"{urun} eklendi. Yanına {oneri} ister misin?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Evet", callback_data=f"add_{oneri}")],
                    [InlineKeyboardButton("Hayır", callback_data="cart")]
                ])
            )
        else:
            await q.message.reply_text("Eklendi", reply_markup=main_menu())

    elif q.data == "cart":
        await q.message.reply_text(cart_text(uid), reply_markup=main_menu())

    elif q.data == "quick":
        user["cart"] += ["pizza","ayran"]
        await q.message.reply_text("Hızlı sipariş eklendi", reply_markup=main_menu())

    elif q.data == "address":
        user["waiting_address"] = True
        await q.message.reply_text("Adres yaz")

    elif q.data == "payment":
        await q.message.reply_text("Ödeme seç", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Nakit", callback_data="cash")],
            [InlineKeyboardButton("Kart", callback_data="card")],
            [InlineKeyboardButton("IBAN", callback_data="iban")]
        ]))

    elif q.data == "cash":
        user["payment"] = "Nakit"

    elif q.data == "card":
        user["payment"] = "Kart"

    elif q.data == "iban":
        user["payment"] = "IBAN"
        await q.message.reply_text(f"IBAN: {IBAN}")

    elif q.data == "confirm":
        if not user["cart"]:
            await q.message.reply_text("Sepet boş")
            return

        order_id = random.randint(100000,999999)
        ensure_orders_file()

        with open(ORDERS_FILE,"a",newline="",encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                order_id,
                datetime.now(),
                ",".join(user["cart"]),
                cart_total(uid),
                user["address"],
                user["note"],
                user["payment"]
            ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Yeni sipariş: {user['cart']}"
        )

        user["cart"] = []
        await q.message.reply_text("Sipariş alındı")

    elif q.data == "cancel":
        user["cart"] = []
        await q.message.reply_text("İptal edildi")

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    init_user(uid)
    user = kullanicilar[uid]

    if user["waiting_address"]:
        user["address"] = update.message.text
        user["waiting_address"] = False
        await update.message.reply_text("Adres kaydedildi")
    else:
        await update.message.reply_text("Menüden ilerle", reply_markup=main_menu())

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT, text))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()