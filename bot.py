import os
from datetime import datetime

import openpyxl
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# TOKEN / ADMIN
TOKEN = os.getenv("TOKEN") or "BURAYA_TOKEN"
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

    total = sum(MENU_ITEMS[i] for i in cart)
    now = datetime.now()

    ws.append([
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M"),
        ", ".join(cart),
        total,
        address,
        payment
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
        "Hoş geldin 👋\nSipariş vermek için menüyü kullan 👇",
        reply_markup=ANA_MENU
    )

# HANDLE
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_text = update.message.text
    text = raw_text.lower()

    user = get_user(user_id)

    # GERİ
    if "geri" in text:
        await update.message.reply_text(
            "Ana menüye döndün 👇",
            reply_markup=ANA_MENU
        )
        return

    # ADRES GİRİŞİ
    if user["waiting_address"]:
        user["address"] = raw_text
        user["waiting_address"] = False
        await update.message.reply_text(
            "📍 Adres kaydedildi ✅",
            reply_markup=ANA_MENU
        )
        return

    # İPTAL
    if "iptal" in text:
        users[user_id] = {
            "cart": [],
            "address": user["address"],
            "payment": None,
            "waiting_address": False,
        }
        await update.message.reply_text("Sipariş iptal edildi ❌", reply_markup=ANA_MENU)
        return

    # MENÜ
    if "menü" in text:
        await update.message.reply_text(
            "🍔 Ürün seçebilirsin 👇",
            reply_markup=URUN_MENU
        )
        return

    # ÜRÜN EKLE
    if text in ["pizza", "burger", "ayran", "kola"]:
        user["cart"].append(text)

        # upsell
        extra = ""
        if text == "pizza":
            extra = "\nYanına ayran ister misin? 🥤"
        elif text == "burger":
            extra = "\nYanına kola ister misin? 🥤"

        await update.message.reply_text(
            f"🛒 {text.capitalize()} sepete eklendi!{extra}",
            reply_markup=URUN_MENU
        )
        return

    # SEPET
    if "sepet" in text:
        if not user["cart"]:
            await update.message.reply_text("Sepetin boş 😕")
            return

        total = sum(MENU_ITEMS[i] for i in user["cart"])

        await update.message.reply_text(
            f"🛒 Sepetin:\n{', '.join(user['cart'])}\n\n💰 Toplam: {total} TL",
            reply_markup=ANA_MENU
        )
        return

    # ADRES
    if "adres" in text:
        user["waiting_address"] = True
        await update.message.reply_text(
            "📍 Lütfen adresini yaz:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # ÖDEME
    if "ödeme" in text:
        await update.message.reply_text(
            "💳 Ödeme yöntemini seç:",
            reply_markup=ODEME_MENU
        )
        return

    if text in ["nakit", "kart"]:
        user["payment"] = text
        await update.message.reply_text(
            f"💳 {text.capitalize()} seçildi ✅",
            reply_markup=ANA_MENU
        )
        return

    # ONAY EKRANI
    if "onay" in text and "onayla" not in text:
        await update.message.reply_text(
            "Siparişi onaylamak için aşağıya bas 👇",
            reply_markup=ONAY_MENU
        )
        return

    # ONAYLA (ASIL SİPARİŞ)
    if "onayla" in text:
        if not user["cart"]:
            await update.message.reply_text("Sepet boş ❌")
            return

        if not user["address"]:
            user["waiting_address"] = True
            await update.message.reply_text("Adres girmen lazım ❌", reply_markup=ReplyKeyboardRemove())
            return

        if not user["payment"]:
            await update.message.reply_text("Ödeme seç ❌", reply_markup=ODEME_MENU)
            return

        total = sum(MENU_ITEMS[i] for i in user["cart"])

        msg = f"📦 Yeni Sipariş\n\n🛒 {', '.join(user['cart'])}\n💰 {total} TL\n📍 {user['address']}\n💳 {user['payment']}"

        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

        save_order(user["cart"], user["address"], user["payment"])

        users[user_id] = {
            "cart": [],
            "address": user["address"],
            "payment": None,
            "waiting_address": False,
        }

        await update.message.reply_text(
            "Siparişin alındı 🎉",
            reply_markup=ANA_MENU
        )
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
