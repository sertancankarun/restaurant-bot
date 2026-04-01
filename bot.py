import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MENU = {
    "Pizza": 150,
    "Burger": 120,
    "Ayran": 30,
    "Kola": 40
}

users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "cart": [],
            "adres": None,
            "odeme": None,
            "isim": None,
            "telefon": None,
            "state": None
        }
    return users[uid]

def main_menu():
    return ReplyKeyboardMarkup([
        ["🍔 Menü", "🛒 Sepet"],
        ["📍 Adres", "💳 Ödeme"],
        ["✅ Onayla", "❌ İptal"]
    ], resize_keyboard=True)

def menu_buttons():
    return ReplyKeyboardMarkup([
        ["Pizza", "Burger"],
        ["Ayran", "Kola"],
        ["🛒 Sepet", "🔙 Geri"]
    ], resize_keyboard=True)

def payment_buttons():
    return ReplyKeyboardMarkup([
        ["💵 Nakit", "💳 Kapıda Kart"],
        ["🏦 IBAN"],
        ["🔙 Geri"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name

    users.pop(uid, None)

    await update.message.reply_text(
f"""👋 Hoş geldin {name}!

🍔 Sipariş vermek için:

1️⃣ Menüden ürün seç  
2️⃣ Adres gir  
3️⃣ Ödeme seç  
4️⃣ Onayla  

👇 Başlamak için Menü'ye bas""",
        reply_markup=main_menu()
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    user = get_user(uid)

    # 🔥 STATE ÖNCELİĞİ

    if user["state"] == "adres":
        if len(text) < 4:
            await update.message.reply_text("📍 Daha detaylı adres yaz")
            return

        user["adres"] = text
        user["state"] = None

        await update.message.reply_text(f"📍 Adres kaydedildi ✅\n{text}", reply_markup=main_menu())
        return

    if user["state"] == "isim":
        user["isim"] = text
        user["state"] = "telefon"

        await update.message.reply_text("📞 Telefon numaranı yaz:")
        return

    if user["state"] == "telefon":
        if not text.isdigit() or len(text) < 10:
            await update.message.reply_text("📞 Geçerli numara yaz")
            return

        user["telefon"] = text
        user["state"] = None

        total = sum(MENU[i] for i in user["cart"])

        msg = f"""
📦 Yeni Sipariş

👤 {user['isim']}
📞 {user['telefon']}
🛒 {', '.join(user['cart'])}
💰 {total} TL
📍 {user['adres']}
💳 {user['odeme']}
"""

        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

        await update.message.reply_text("🎉 Sipariş alındı! Hazırlanıyor 👨‍🍳", reply_markup=main_menu())

        users.pop(uid, None)
        return

    # 🔥 BUTONLAR

    if text == "🍔 Menü":
        await update.message.reply_text("👇 Ürün seç:", reply_markup=menu_buttons())
        return

    if text == "🔙 Geri":
        await update.message.reply_text("↩️ Ana menü", reply_markup=main_menu())
        return

    if text in MENU:
        user["cart"].append(text)
        total = sum(MENU[i] for i in user["cart"])

        await update.message.reply_text(f"🔥 {text} eklendi\n💰 Toplam: {total} TL")
        return

    if text == "🛒 Sepet":
        if not user["cart"]:
            await update.message.reply_text("🛒 Sepet boş")
            return

        total = sum(MENU[i] for i in user["cart"])

        await update.message.reply_text(
f"""🛒 Sepet:

{', '.join(user["cart"])}

💰 {total} TL
📍 {user["adres"] or "Yok"}
💳 {user["odeme"] or "Yok"}"""
        )
        return

    if text == "📍 Adres":
        user["state"] = "adres"
        await update.message.reply_text("📍 Adresini yaz:")
        return

    if text == "💳 Ödeme":
        await update.message.reply_text("💳 Ödeme seç:", reply_markup=payment_buttons())
        return

    if text in ["💵 Nakit", "💳 Kapıda Kart", "🏦 IBAN"]:
        user["odeme"] = text
        await update.message.reply_text(f"✅ {text} seçildi", reply_markup=main_menu())
        return

    if text == "✅ Onayla":

        if not user["cart"]:
            await update.message.reply_text("🛒 Önce ürün seç")
            return

        if not user["adres"]:
            user["state"] = "adres"
            await update.message.reply_text("📍 Adresini yaz:")
            return

        if not user["odeme"]:
            await update.message.reply_text("💳 Ödeme seç")
            return

        user["state"] = "isim"
        await update.message.reply_text("👤 İsmini yaz:")
        return

    if text == "❌ İptal":
        users.pop(uid, None)
        await update.message.reply_text("❌ Sipariş iptal edildi", reply_markup=main_menu())
        return

    await update.message.reply_text("⚠️ Menüden seçim yap", reply_markup=main_menu())

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
