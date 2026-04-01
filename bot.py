import os
from datetime import datetime

import openpyxl
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# TOKEN ve ADMIN
TOKEN = os.getenv("TOKEN") or "8375997086:AAFQsoQchoyIuHjtoff3Wr5hUeUy4_nVqUY"
ADMIN_ID = int(os.getenv("ADMIN_ID") or "6741548158")

FILE_NAME = "orders.xlsx"

MENU_ITEMS = {
    "pizza": 150,
    "burger": 120,
    "ayran": 30,
    "kola": 40,
}

users = {}

# MENÜLER
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
        ["⬅️ Geri", "🛒 Sepet"],
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

ONAY_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Onayla", "❌ İptal"],
        ["⬅️ Geri"],
    ],
    resize_keyboard=True
)

# EXCEL
def init_excel():
    try:
        openpyxl.load_workbook(FILE_NAME)
    except:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Tarih", "Saat", "Ürünler", "Toplam", "Adres", "Ödeme"])
        wb.save(FILE_NAME)

def save_order(cart, address, payment):
    wb = openpyxl.load_workbook(FILE_NAME)
    ws = wb.active

    total = sum(MENU_ITEMS[item] for item in cart)
    now = datetime.now()

    ws.append([
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M"),
        ", ".join(cart),
        total,
        address,
        payment,
    ])

    wb.save(FILE_NAME)

# USER
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "cart": [],
            "address": None,
            "payment": None,
            "waiting_address": False,
        }
    return users[user_id]

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hoş geldin 👋",
        reply_markup=ANA_MENU
    )

# MESAJ
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    user = get_user(user_id)

    # adres yazma
    if user["waiting_address"]:
        user["address"] = update.message.text
        user["waiting_address"] = False
        await update.message.reply_text("Adres kaydedildi ✅", reply_markup=ANA_MENU)
        return

    # iptal
    if "iptal" in text:
        users[user_id] = {
            "cart": [],
            "address": user["address"],
            "payment": None,
            "waiting_address": False,
        }
        await update.message.reply_text("İptal edildi ❌", reply_markup=ANA_MENU)
        return

    # menü
    if "menü" in text:
        await update.message.reply_text("Ürün seç:", reply_markup=URUN_MENU)
        return

    # ürün ekleme
    if text in ["pizza", "burger", "ayran", "kola"]:
        user["cart"].append(text)
        await update.message.reply_text(f"{text} eklendi ✅", reply_markup=URUN_MENU)
        return

    # sepet
    if "sepet" in text:
        if not user["cart"]:
            await update.message.reply_text("Sepet boş")
            return

        total = sum(MENU_ITEMS[i] for i in user["cart"])
        await update.message.reply_text(
            f"Sepet: {', '.join(user['cart'])}\nToplam: {total} TL",
            reply_markup=ANA_MENU
        )
        return

    # adres
    if "adres" in text:
        user["waiting_address"] = True
        await update.message.reply_text("Adres yaz:", reply_markup=ReplyKeyboardRemove())
        return

    # ödeme
    if "ödeme" in text:
        await update.message.reply_text("Ödeme seç:", reply_markup=ODEME_MENU)
        return

    if text in ["nakit", "kart"]:
        user["payment"] = text
        await update.message.reply_text(f"{text} seçildi ✅", reply_markup=ANA_MENU)
        return

    # onay ekranı
    if text == "onay":
        await update.message.reply_text("Onaylamak için tıkla", reply_markup=ONAY_MENU)
        return

    # onayla
    if "onayla" in text:
        if not user["cart"]:
            await update.message.reply_text("Sepet boş ❌")
            return

        if not user["address"]:
            user["waiting_address"] = True
            await update.message.reply_text("Adres gir ❌", reply_markup=ReplyKeyboardRemove())
            return

        if not user["payment"]:
            await update.message.reply_text("Ödeme seç ❌", reply_markup=ODEME_MENU)
            return

        total = sum(MENU_ITEMS[i] for i in user["cart"])

        msg = f"Sipariş:\n{', '.join(user['cart'])}\n{total} TL\nAdres: {user['address']}\nÖdeme: {user['payment']}"

        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

        save_order(user["cart"], user["address"], user["payment"])

        users[user_id] = {
            "cart": [],
            "address": user["address"],
            "payment": None,
            "waiting_address": False,
        }

        await update.message.reply_text("Sipariş alındı ✅", reply_markup=ANA_MENU)
        return

# MAIN
def main():
    init_excel()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
