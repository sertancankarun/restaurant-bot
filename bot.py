import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MENU = {
    "Pizza": 150,
    "Burger": 120,
    "Kola": 40,
    "Ayran": 30
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
    return ReplyKeyboardMarkup([
        ["🍔 Menü", "🛒 Sepet"],
        ["📍 Adres", "💳 Ödeme"],
        ["✅ Onayla", "❌ İptal"]
    ], resize_keyboard=True)

def menu_buttons():
    return ReplyKeyboardMarkup([
        ["Pizza", "Burger"],
        ["Ayran", "Kola"],
        ["🔙 Geri"]
    ], resize_keyboard=True)

def payment_menu():
    return ReplyKeyboardMarkup([
        ["💵 Nakit", "💳 Kapıda Kart"],
        ["🏦 IBAN"],
        ["🔙 Geri"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hoş geldin {name}!\nSipariş vermek için menüyü kullan 👇",
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

    # 🔥 STATE BLOKLARI (EN ÜST)

    if user["state"] == "telefon":
        if not text.isdigit() or len(text) < 10:
            await update.message.reply_text("📞 Geçerli numara yaz (sadece rakam)")
            return

        user["telefon"] = text
        user["state"] = None

        total = sum(MENU[i] for i in user["cart"])

        msg = f"""
📦 Sipariş

👤 {user['isim']}
📞 {user['telefon']}
🛒 {', '.join(user['cart'])}
💰 {total} TL
📍 {user['adres']}
💳 {user['odeme']}
"""

        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

        await update.message.reply_text(
            "🎉 Siparişin alındı! Hazırlanıyor 👨‍🍳",
            reply_markup=main_menu()
        )

        users[uid] = {}
        return

    if user["state"] == "isim":
        user["isim"] = text
        user["state"] = "telefon"
        await update.message.reply_text("📞 Telefon numaranı yaz:")
        return

 # 🔥 ADRES FIX (SADECE BURAYI DEĞİŞTİR)
if user.get("state") == "adres":
    # buton basarsa engelle
    if text in ["🍔 Menü", "🛒 Sepet", "💳 Ödeme", "✅ Onayla", "❌ İptal"]:
        await update.message.reply_text("📍 Lütfen adresini yaz (buton değil)")
        return

    user["adres"] = text
    user["state"] = None

    await update.message.reply_text(
        f"📍 Adres kaydedildi ✅\n🏠 {text}",
        reply_markup=main_menu()
    )
    return

    # 🔥 MENÜ
    if text == "🍔 Menü":
        await update.message.reply_text("👇 Ürün seç:", reply_markup=menu_buttons())
        return

    # 🔥 ÜRÜN
    if text in MENU:
        user["cart"].append(text)
        fiyat = MENU[text]
        total = sum(MENU[i] for i in user["cart"])

        await update.message.reply_text(
            f"🔥 {text} eklendi!\n💰 {fiyat} TL\n🧾 Toplam: {total} TL"
        )
        return

    # 🔥 SEPET
    if text == "🛒 Sepet":
        await update.message.reply_text(cart_text(user), reply_markup=main_menu())
        return

    # 🔥 ADRES
    if text == "📍 Adres":
        user["state"] = "adres"
        await update.message.reply_text("📍 Adresini yaz:")
        return

    # 🔥 ÖDEME MENÜ
    if text == "💳 Ödeme":
        await update.message.reply_text("💳 Ödeme yöntemi seç:", reply_markup=payment_menu())
        return

    # 🔥 ÖDEME SEÇİMİ
    if text in ["💵 Nakit", "💳 Kapıda Kart", "🏦 IBAN"]:
        user["odeme"] = text
        await update.message.reply_text(f"{text} seçildi ✅", reply_markup=main_menu())
        return

    # 🔥 GERİ
    if text == "🔙 Geri":
        await update.message.reply_text("🔙 Ana menü", reply_markup=main_menu())
        return

    # 🔥 İPTAL
    if text == "❌ İptal":
        users[uid] = {}
        await update.message.reply_text("❌ Sipariş iptal edildi", reply_markup=main_menu())
        return

    # 🔥 ONAY
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

    # 🔥 DEFAULT
    await update.message.reply_text("👇 Menüden seçim yap", reply_markup=main_menu())

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
