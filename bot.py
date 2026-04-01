import os
import random
from datetime import datetime

import openpyxl
from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

FILE_NAME = "orders.xlsx"

OPEN = 10
CLOSE = 23

MENU = {
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

ANA_MENU = ReplyKeyboardMarkup([
    ["🍔 Menü", "🛒 Sepet"],
    ["📍 Adres", "💳 Ödeme"],
    ["🔁 Tekrar Sipariş", "🗑️ Son Ürünü Sil"],
    ["✅ Onay", "❌ İptal"]
], resize_keyboard=True)

URUN_MENU = ReplyKeyboardMarkup([
    ["Pizza", "Burger"],
    ["Ayran", "Kola"],
    ["🛒 Sepet", "⬅️ Geri"]
], resize_keyboard=True)

SEPET_MENU = ReplyKeyboardMarkup([
    ["✅ Onay", "🗑️ Son Ürünü Sil"],
    ["🍔 Menü", "⬅️ Geri"],
    ["❌ İptal"]
], resize_keyboard=True)

ODEME_MENU = ReplyKeyboardMarkup([
    ["Nakit", "Kart"],
    ["⬅️ Geri"]
], resize_keyboard=True)


def init_excel():
    try:
        openpyxl.load_workbook(FILE_NAME)
    except:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ID", "Ürünler", "Toplam", "Adres", "Ödeme"])
        wb.save(FILE_NAME)


def save_order(cart, address, payment):
    wb = openpyxl.load_workbook(FILE_NAME)
    ws = wb.active
    total = sum(MENU[i] for i in cart)
    ws.append([random.randint(1000,9999), ", ".join(cart), total, address, payment])
    wb.save(FILE_NAME)


def get_user(uid):
    if uid not in users:
        users[uid] = {
            "cart": [],
            "address": None,
            "payment": None,
            "name": None,
            "phone": None,
            "state": "main",
            "waiting_name": False,
            "waiting_phone": False,
            "waiting_address": False,
            "last_order": []
        }
    return users[uid]


def total(user):
    return sum(MENU[i] for i in user["cart"])


def is_open():
    return OPEN <= datetime.now().hour < CLOSE


def format_cart(user):
    if not user["cart"]:
        return "Sepet boş 😕"

    txt = ""
    for i in user["cart"]:
        txt += f"{EMOJI[i]} {i} - {MENU[i]} TL\n"

    return f"🛒 Sepet:\n\n{txt}\n💰 Toplam: {total(user)} TL"


async def start(update, context):
    user = get_user(update.effective_user.id)

    msg = "🟢 Açığız" if is_open() else "🔴 Kapalıyız"

    await update.message.reply_text(
        f"Hoş geldin {update.effective_user.first_name} 👋\n{msg}",
        reply_markup=ANA_MENU
    )


async def handle(update, context):
    uid = update.effective_user.id
    user = get_user(uid)
    text = update.message.text.lower()
    raw = update.message.text

    # İSİM
    if user["waiting_name"]:
        user["name"] = raw
        user["waiting_name"] = False
        user["waiting_phone"] = True
        await update.message.reply_text("📞 Telefonunu yaz:")
        return

    # TELEFON
    if user["waiting_phone"]:
        if not raw.isdigit() or len(raw) != 11:
            await update.message.reply_text("❌ Geçerli telefon gir (11 hane)")
            return

        user["phone"] = raw
        user["waiting_phone"] = False
        user["waiting_address"] = True
        await update.message.reply_text("📍 Adres yaz:")
        return

    # ADRES
    if user["waiting_address"]:
        user["address"] = raw
        user["waiting_address"] = False
        await update.message.reply_text("📍 Kaydedildi ✅", reply_markup=ANA_MENU)
        return

    # GERİ
    if "geri" in text:
        await update.message.reply_text("Ana menü 👇", reply_markup=ANA_MENU)
        return

    if "iptal" in text:
        user["cart"] = []
        await update.message.reply_text("İptal edildi ❌", reply_markup=ANA_MENU)
        return

    if "menü" in text:
        await update.message.reply_text("Ürün seç 👇", reply_markup=URUN_MENU)
        return

    if text in MENU:
        user["cart"].append(text)
        await update.message.reply_text(
            f"{EMOJI[text]} {text} eklendi 🔥\n💰 {total(user)} TL",
            reply_markup=URUN_MENU
        )
        return

    if "sepet" in text:
        await update.message.reply_text(format_cart(user), reply_markup=SEPET_MENU)
        return

    if "adres" in text:
        user["waiting_address"] = True
        await update.message.reply_text("Adres yaz:", reply_markup=ReplyKeyboardRemove())
        return

    if "ödeme" in text:
        await update.message.reply_text("Seç 👇", reply_markup=ODEME_MENU)
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
            await update.message.reply_text("Telefon yaz:")
            return

        if not user["address"]:
            user["waiting_address"] = True
            await update.message.reply_text("Adres yaz:")
            return

        if not user["payment"]:
            await update.message.reply_text("Ödeme seç!")
            return

        save_order(user["cart"], user["address"], user["payment"])

        await update.message.reply_text(
            "🎉 Sipariş alındı!\n20-30 dk içinde sende",
            reply_markup=ANA_MENU
        )

        user["last_order"] = list(user["cart"])
        user["cart"] = []
        return

    await update.message.reply_text("Anlayamadım 😕", reply_markup=ANA_MENU)


async def main():
    init_excel()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))
    app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
