import os
from datetime import datetime

import openpyxl
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Railway varsa oradan alır, yoksa PC testi için alttaki değerleri kullanır
TOKEN = os.getenv("TOKEN") or "BURAYA_TOKEN"
ADMIN_ID = int(os.getenv("ADMIN_ID") or "6741548158")

FILE_NAME = "orders.xlsx"
RESTAURANT_NAME = "Getiriyosun Bot"

MENU_ITEMS = {
    "pizza": 150,
    "burger": 120,
    "ayran": 30,
    "kola": 40,
}

UPSELL = {
    "pizza": "ayran",
    "burger": "kola",
}

users = {}

# ---------------- MENÜLER ----------------

ANA_MENU = ReplyKeyboardMarkup(
    [
        ["🍔 Menü", "⚡ Hızlı Menü"],
        ["🛒 Sepet", "📍 Adres"],
        ["💳 Ödeme", "✅ Onay"],
        ["❌ İptal"],
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
        ["⬅️ Geri", "❌ İptal"],
    ],
    resize_keyboard=True
)

ONAY_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Onayla", "❌ İptal"],
        ["⬅️ Geri", "🛒 Sepet"],
    ],
    resize_keyboard=True
)

# ---------------- EXCEL ----------------

def init_excel():
    try:
        openpyxl.load_workbook(FILE_NAME)
    except FileNotFoundError:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Orders"
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

# ---------------- USER ----------------

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "cart": [],
            "address": None,
            "payment": None,
            "waiting_address": False,
        }
    return users[user_id]


def reset_user(user_id, keep_address=True):
    old_address = users[user_id]["address"] if user_id in users and keep_address else None
    users[user_id] = {
        "cart": [],
        "address": old_address,
        "payment": None,
        "waiting_address": False,
    }


def cart_total(user):
    return sum(MENU_ITEMS[item] for item in user["cart"])


def format_cart(user):
    if not user["cart"]:
        return "Sepetin şu an boş 😕"

    lines = []
    total = 0
    for item in user["cart"]:
        price = MENU_ITEMS[item]
        total += price
        emoji = "🍕" if item == "pizza" else "🍔" if item == "burger" else "🥤" if item == "kola" else "🥛"
        lines.append(f"{emoji} {item.capitalize()} - {price} TL")

    address = user["address"] if user["address"] else "Girilmedi"
    payment = user["payment"].capitalize() if user["payment"] else "Seçilmedi"

    return (
        f"🛒 {RESTAURANT_NAME} Sipariş Özeti\n\n"
        + "\n".join(lines)
        + f"\n\n💰 Toplam: {total} TL"
        + f"\n📍 Adres: {address}"
        + f"\n💳 Ödeme: {payment}"
    )

# ---------------- BOT ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "Dostum"
    user = get_user(user_id)

    if user["address"]:
        msg = (
            f"🍔 {RESTAURANT_NAME}\n\n"
            f"Tekrar hoş geldin {name} 😄\n"
            "Sipariş vermek için aşağıdaki menüyü kullanabilirsin."
        )
    else:
        msg = (
            f"🍔 {RESTAURANT_NAME}\n\n"
            f"Hoş geldin {name} 👋\n"
            "Sipariş vermek için aşağıdaki menüyü kullanabilirsin."
        )

    await update.message.reply_text(msg, reply_markup=ANA_MENU)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_text = update.message.text.strip()
    text = raw_text.lower()

    user = get_user(user_id)

    # Adres bekleniyorsa
    if user["waiting_address"]:
        user["address"] = raw_text
        user["waiting_address"] = False
        await update.message.reply_text(
            "📍 Adresin başarıyla kaydedildi ✅",
            reply_markup=ANA_MENU
        )
        return

    # Geri
    if "geri" in text:
        await update.message.reply_text(
            "Ana menüye döndün 👇",
            reply_markup=ANA_MENU
        )
        return

    # İptal
    if "iptal" in text:
        reset_user(user_id, keep_address=True)
        await update.message.reply_text(
            "Sipariş iptal edildi ❌\nYeni sipariş için menüyü kullanabilirsin.",
            reply_markup=ANA_MENU
        )
        return

    # Menü
    if "menü" in text or "menu" in text:
        await update.message.reply_text(
            "🍔 Ürün seçebilirsin 👇",
            reply_markup=URUN_MENU
        )
        return

    # Hızlı Menü
    if "hızlı menü" in text or "hizli menü" in text or "hizli menu" in text:
        user["cart"].append("pizza")
        user["cart"].append("ayran")

        await update.message.reply_text(
            "⚡ Hızlı Menü sepete eklendi!\n\n🍕 Pizza + 🥛 Ayran",
            reply_markup=ANA_MENU
        )
        return

    # Ürün ekleme
    if text in ["pizza", "burger", "ayran", "kola"]:
        user["cart"].append(text)

        extra = ""
        if text in UPSELL:
            extra = f"\nYanına {UPSELL[text].capitalize()} ister misin? 😉"

        await update.message.reply_text(
            f"🛒 {text.capitalize()} sepete eklendi!{extra}",
            reply_markup=URUN_MENU
        )
        return

    # Sepet
    if "sepet" in text:
        await update.message.reply_text(
            format_cart(user),
            reply_markup=ANA_MENU
        )
        return

    # Adres
    if "adres" in text:
        user["waiting_address"] = True
        await update.message.reply_text(
            "📍 Lütfen teslimat adresini yaz:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # Ödeme
    if "ödeme" in text or "odeme" in text:
        await update.message.reply_text(
            "💳 Ödeme yöntemini seç:",
            reply_markup=ODEME_MENU
        )
        return

    if text in ["nakit", "kart"]:
        user["payment"] = text
        await update.message.reply_text(
            f"💳 Ödeme yöntemi seçildi: {text.capitalize()} ✅",
            reply_markup=ANA_MENU
        )
        return

    # Onay ekranı
    if "onay" in text and "onayla" not in text:
        await update.message.reply_text(
            format_cart(user) + "\n\nSiparişi tamamlamak için aşağıdaki butonu kullan 👇",
            reply_markup=ONAY_MENU
        )
        return

    # Asıl onay
    if "onayla" in text:
        if not user["cart"]:
            await update.message.reply_text(
                "Sepetin boş ❌\nÖnce ürün seçmelisin.",
                reply_markup=ANA_MENU
            )
            return

        if not user["address"]:
            user["waiting_address"] = True
            await update.message.reply_text(
                "Adres yazmadan siparişi tamamlayamazsın ❌\nLütfen şimdi adresini yaz.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        if not user["payment"]:
            await update.message.reply_text(
                "Ödeme seçmeden siparişi tamamlayamazsın ❌\nLütfen ödeme seç.",
                reply_markup=ODEME_MENU
            )
            return

        total = cart_total(user)
        items_text = ", ".join(item.capitalize() for item in user["cart"])

        admin_msg = (
            f"🚨 YENİ SİPARİŞ - {RESTAURANT_NAME}\n\n"
            f"🛒 Ürünler: {items_text}\n"
            f"💰 Toplam: {total} TL\n"
            f"📍 Adres: {user['address']}\n"
            f"💳 Ödeme: {user['payment'].capitalize()}\n"
            f"🕒 Saat: {datetime.now().strftime('%H:%M')}"
        )

        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        save_order(user["cart"], user["address"], user["payment"])

        await update.message.reply_text(
            "🎉 Siparişin alındı!\n\n"
            "⏱ Ortalama teslim süresi: 20-30 dk\n"
            "📞 Gerekirse seninle iletişime geçebiliriz.\n\n"
            "Teşekkür ederiz ❤️",
            reply_markup=ANA_MENU
        )

        reset_user(user_id, keep_address=True)
        return

    # Fallback
    await update.message.reply_text(
        "Seni tam anlayamadım 😕\n\n"
        "Aşağıdaki menüden devam edebilirsin 👇",
        reply_markup=ANA_MENU
    )


def main():
    init_excel()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot çalışıyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
