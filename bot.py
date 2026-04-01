import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
import random

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

OPEN = 10
CLOSE = 23

CAMPAIGN_ACTIVE = False  # 🔥 kampanya aç kapa

MENU = {
    "🍕 Pizza": 150,
    "🍔 Burger": 120,
    "🥤 Kola": 40,
    "🥛 Ayran": 30
}

users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "cart": [],
            "adres": None,
            "odeme": None,
            "state": None,
            "isim": None,
            "telefon": None
        }
    return users[uid]

def main_menu():
    buttons = [
        ["🍔 Menü", "🛒 Sepet"],
        ["📍 Adres", "💳 Ödeme"],
        ["✅ Onayla", "❌ İptal"]
    ]
    if CAMPAIGN_ACTIVE:
        buttons.insert(0, ["🔥 Kampanya"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def menu_buttons():
    return ReplyKeyboardMarkup(
        [["🍕 Pizza", "🍔 Burger"],
         ["🥤 Kola", "🥛 Ayran"],
         ["🔙 Geri"]],
        resize_keyboard=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().hour
    if now < OPEN or now >= CLOSE:
        await update.message.reply_text("🚫 Şu an kapalıyız")
        return

    await update.message.reply_text(
        "👋 Hoş geldin!\n\n🍽 Sipariş vermek için menüyü kullan 👇",
        reply_markup=main_menu()
    )

def cart_text(user):
    if not user["cart"]:
        return "🛒 Sepet boş"

    total = sum(MENU[i] for i in user["cart"])
    text = "🛒 Sepet:\n\n"
    for i in user["cart"]:
        text += f"• {i} - {MENU[i]} TL\n"

    text += f"\n💰 Toplam: {total} TL\n"
    text += f"📍 Adres: {user['adres'] or 'Yok'}\n"
    text += f"💳 Ödeme: {user['odeme'] or 'Yok'}"

    return text

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    user = get_user(uid)

    # 🔥 ADRES YAZMA FIX
    if user["state"] == "adres":
        user["adres"] = text
        user["state"] = None
        await update.message.reply_text(
            f"📍 Adres kaydedildi ✅\n🏠 {text}",
            reply_markup=main_menu()
        )
        return

    # 🔥 İSİM
    if user["state"] == "isim":
        user["isim"] = text
        user["state"] = "telefon"
        await update.message.reply_text("📞 Telefon numaranı yaz:")
        return

    # 🔥 TELEFON
    if user["state"] == "telefon":
        user["telefon"] = text
        user["state"] = None
        await update.message.reply_text("✅ Bilgiler alındı", reply_markup=main_menu())
        return

    if text == "🍔 Menü":
        await update.message.reply_text("👇 Ürün seç:", reply_markup=menu_buttons())
        return

    if text in MENU:
        user["cart"].append(text)

        cevaplar = [
            f"{text} sepete eklendi 🔥",
            f"Harika seçim! {text} 👌",
            f"{text} eklendi, devam edelim 😎"
        ]

        await update.message.reply_text(random.choice(cevaplar))
        return

    if text == "🛒 Sepet":
        await update.message.reply_text(cart_text(user), reply_markup=main_menu())
        return

    if text == "📍 Adres":
        user["state"] = "adres"
        await update.message.reply_text("📍 Adresini yaz:")
        return

    if text == "💳 Ödeme":
        user["odeme"] = "Nakit"
        await update.message.reply_text("💳 Ödeme: Nakit seçildi ✅")
        return

    if text == "🔙 Geri":
        await update.message.reply_text("🔙 Ana menü", reply_markup=main_menu())
        return

    if text == "❌ İptal":
        users[uid] = {}
        await update.message.reply_text("❌ Sipariş iptal edildi", reply_markup=main_menu())
        return

    if text == "✅ Onayla":
        if not user["cart"]:
            await update.message.reply_text("🛒 Sepet boş")
            return

        if not user["adres"]:
            user["state"] = "adres"
            await update.message.reply_text("📍 Önce adres yaz:")
            return

        if not user["odeme"]:
            await update.message.reply_text("💳 Önce ödeme seç")
            return

        user["state"] = "isim"
        await update.message.reply_text("👤 İsmini yaz:")
        return

    # 🔥 ANLAYAMADIM FIX (SADECE GEREKSİZ MESAJLARDA)
    await update.message.reply_text(
        "👇 Menüden seçim yapabilirsin",
        reply_markup=main_menu()
    )

async def main_admin_notify(app, uid, user):
    order_id = random.randint(1000, 9999)
    text = f"""📦 Sipariş #{order_id}

👤 {user['isim']}
📞 {user['telefon']}

🛒 {', '.join(user['cart'])}
💰 {sum(MENU[i] for i in user['cart'])} TL
📍 {user['adres']}
"""

    await app.bot.send_message(chat_id=ADMIN_ID, text=text)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
