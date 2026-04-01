import os
import random
from datetime import datetime

import openpyxl
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Railway varsa oradan alır, PC testi için fallback vardır
TOKEN = os.getenv("TOKEN") or "BURAYA_TOKEN"
ADMIN_ID = int(os.getenv("ADMIN_ID") or "6741548158")

FILE_NAME = "orders.xlsx"
RESTAURANT_NAME = "Getiriyosun Bot"

# Çalışma saatleri
OPEN_HOUR = 10
CLOSE_HOUR = 23

MENU_ITEMS = {
    "pizza": 150,
    "burger": 120,
    "ayran": 30,
    "kola": 40,
}

COMBOS = {
    "⚡ Menü 1": ["pizza", "ayran"],
    "⚡ Menü 2": ["burger", "kola"],
}

UPSELL = {
    "pizza": "ayran",
    "burger": "kola",
}

EMOJI = {
    "pizza": "🍕",
    "burger": "🍔",
    "ayran": "🥛",
    "kola": "🥤",
}

users = {}

# ---------------- MENÜLER ----------------

ANA_MENU = ReplyKeyboardMarkup(
    [
        ["🍔 Menü", "⚡ Menü 1"],
        ["⚡ Menü 2", "🛒 Sepet"],
        ["📍 Adres", "💳 Ödeme"],
        ["🔁 Tekrar Sipariş", "🗑️ Son Ürünü Sil"],
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
        ["⬅️ Geri", "❌ İptal"],
    ],
    resize_keyboard=True
)

ONAY_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Onayla", "❌ İptal"],
        ["🛒 Sepet", "⬅️ Geri"],
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
        ws.append([
            "Sipariş No",
            "Tarih",
            "Saat",
            "Ürünler",
            "Toplam",
            "Adres",
            "Ödeme"
        ])
        wb.save(FILE_NAME)


def save_order(order_id, cart, address, payment):
    wb = openpyxl.load_workbook(FILE_NAME)
    ws = wb.active

    total = sum(MENU_ITEMS[item] for item in cart)
    now = datetime.now()

    ws.append([
        order_id,
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
            "last_order": [],
        }
    return users[user_id]


def reset_user(user_id, keep_address=True, keep_last_order=True):
    old_address = users[user_id]["address"] if user_id in users and keep_address else None
    old_last_order = users[user_id]["last_order"] if user_id in users and keep_last_order else []

    users[user_id] = {
        "cart": [],
        "address": old_address,
        "payment": None,
        "waiting_address": False,
        "last_order": old_last_order,
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
        lines.append(f"{EMOJI[item]} {item.capitalize()} - {price} TL")

    address = user["address"] if user["address"] else "Girilmedi"
    payment = user["payment"].capitalize() if user["payment"] else "Seçilmedi"

    return (
        f"🛒 {RESTAURANT_NAME} Sipariş Özeti\n\n"
        + "\n".join(lines)
        + f"\n\n💰 Toplam: {total} TL"
        + f"\n📍 Adres: {address}"
        + f"\n💳 Ödeme: {payment}"
    )


def is_open_now():
    hour = datetime.now().hour
    return OPEN_HOUR <= hour < CLOSE_HOUR


def make_order_id():
    return random.randint(1000, 9999)

# ---------------- BOT ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "Dostum"
    user = get_user(user_id)

    status_text = (
        f"🟢 Şu an açığız ({OPEN_HOUR}:00 - {CLOSE_HOUR}:00)"
        if is_open_now()
        else f"🔴 Şu an kapalıyız ({OPEN_HOUR}:00 - {CLOSE_HOUR}:00)"
    )

    if user["address"]:
        msg = (
            f"🍔 {RESTAURANT_NAME}\n\n"
            f"Tekrar hoş geldin {name} 😄\n"
            f"{status_text}\n\n"
            "Sipariş vermek için aşağıdaki menüyü kullanabilirsin."
        )
    else:
        msg = (
            f"🍔 {RESTAURANT_NAME}\n\n"
            f"Hoş geldin {name} 👋\n"
            f"{status_text}\n\n"
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
        reset_user(user_id, keep_address=True, keep_last_order=True)
        await update.message.reply_text(
            "Sipariş iptal edildi ❌\nİstersen yeni sipariş oluşturabilirsin.",
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

    # Combo 1
    if "menü 1" in text:
        user["cart"].extend(COMBOS["⚡ Menü 1"])
        await update.message.reply_text(
            "⚡ Menü 1 sepete eklendi!\n\n🍕 Pizza + 🥛 Ayran",
            reply_markup=ANA_MENU
        )
        return

    # Combo 2
    if "menü 2" in text:
        user["cart"].extend(COMBOS["⚡ Menü 2"])
        await update.message.reply_text(
            "⚡ Menü 2 sepete eklendi!\n\n🍔 Burger + 🥤 Kola",
            reply_markup=ANA_MENU
        )
        return

    # Tekrar sipariş
    if "tekrar sipariş" in text:
        if not user["last_order"]:
            await update.message.reply_text(
                "Henüz tekrar edilecek bir siparişin yok 😕",
                reply_markup=ANA_MENU
            )
            return

        user["cart"].extend(user["last_order"])
        await update.message.reply_text(
            "🔁 Son siparişin tekrar sepete eklendi!",
            reply_markup=ANA_MENU
        )
        return

    # Son ürünü sil
    if "son ürünü sil" in text:
        if not user["cart"]:
            await update.message.reply_text(
                "Silinecek ürün yok. Sepetin boş 😕",
                reply_markup=ANA_MENU
            )
            return

        last_item = user["cart"].pop()
        await update.message.reply_text(
            f"🗑️ Son ürün kaldırıldı: {last_item.capitalize()}",
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
            f"🛒 {EMOJI[text]} {text.capitalize()} sepete eklendi!{extra}",
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
        if not is_open_now():
            await update.message.reply_text(
                f"🔴 Şu an kapalıyız.\nÇalışma saatleri: {OPEN_HOUR}:00 - {CLOSE_HOUR}:00",
                reply_markup=ANA_MENU
            )
            return

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
                "❌ Ödeme yöntemi seçmedin.\n\nLütfen aşağıdan seç 👇",
                reply_markup=ODEME_MENU
            )
            return

        total = cart_total(user)
        items_text = ", ".join(item.capitalize() for item in user["cart"])
        order_id = make_order_id()

        admin_msg = (
            f"🚨 YENİ SİPARİŞ - {RESTAURANT_NAME}\n\n"
            f"🧾 Sipariş No: #{order_id}\n"
            f"🛒 Ürünler: {items_text}\n"
            f"💰 Toplam: {total} TL\n"
            f"📍 Adres: {user['address']}\n"
            f"💳 Ödeme: {user['payment'].capitalize()}\n"
            f"🕒 Saat: {datetime.now().strftime('%H:%M')}"
        )

        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        save_order(order_id, user["cart"], user["address"], user["payment"])

        # Son siparişi kaydet
        user["last_order"] = list(user["cart"])

        await update.message.reply_text(
            f"🎉 Siparişin alındı!\n\n"
            f"🧾 Sipariş numaran: #{order_id}\n"
            f"⏱ Ortalama teslim süresi: 20-30 dk\n"
            f"📞 Gerekirse seninle iletişime geçebiliriz.\n\n"
            "Teşekkür ederiz ❤️",
            reply_markup=ANA_MENU
        )

        reset_user(user_id, keep_address=True, keep_last_order=True)
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
