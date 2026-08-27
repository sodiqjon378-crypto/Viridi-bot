import asyncio
import logging
import os
import sqlite3
import pandas as pd
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

TOKEN = "8950219106:AAHhM1Tl14D8LLaNUmClwxuZRfQ4136UDvc"
ADMIN_IDS = [49557984, 2145398125]

conn = sqlite3.connect("viridi_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article TEXT,
    name TEXT,
    category TEXT,
    volume TEXT,
    price REAL,
    description TEXT,
    media_id TEXT,
    media_type TEXT
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS dealers (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    phone TEXT,
    status TEXT
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS cart (
    user_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    PRIMARY KEY(user_id, product_id)
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    full_name TEXT,
    text TEXT
)
"""
)
conn.commit()


# --- EXCEL FAYLDAN MAHSULOTLARNI AVTOMATIK YUKLASH ---
def load_products_from_excel():
    excel_file = "Прайс.xlsx"
    if not os.path.exists(excel_file):
        return
    
    try:
        df = pd.read_excel(excel_file)
        for _, row in df.iterrows():
            name = str(row.get("Название", ""))
            if pd.isna(name) or not name or name == "nan":
                continue
            
            article = str(row.get("Артикул", ""))
            description = str(row.get("Описание", ""))
            price = float(row.get("цена", 0) if not pd.isna(row.get("цена")) else 0)
            
            volume = "500 ml"
            name_lower = name.lower()
            if "1000 мл" in name_lower or "1 л" in name_lower:
                volume = "1000 ml"
            elif "5200 мл" in name_lower or "5 л" in name_lower:
                volume = "5200 ml"
            elif "750 мл" in name_lower:
                volume = "750 ml"
            elif "1200 мл" in name_lower:
                volume = "1200 ml"
            elif "500 мл" in name_lower:
                volume = "500 ml"

            category = "homeclean"
            if "мыло" in name_lower or "cream-мыло" in name_lower:
                category = "soap"
            elif "антижир" in name_lower or "кухню" in name_lower or "жиру нет" in name_lower:
                category = "degreaser"
            elif "стирки" in name_lower or "гель для стирки" in name_lower or "кондиционер" in name_lower:
                category = "laundry"
            elif "туалета" in name_lower or "ванной" in name_lower or "virsant" in name_lower:
                category = "bathroom"
            elif "пола" in name_lower or "viround" in name_lower:
                category = "homeclean"
            elif "посуды" in name_lower or "virma" in name_lower:
                category = "soap"

            cursor.execute("SELECT id FROM products WHERE article = ? OR name = ?", (article, name))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(
                    """
                    INSERT INTO products (article, name, category, volume, price, description, media_type) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (article, name, category, volume, price, description, "photo")
                )
        conn.commit()
        print("Excel fayldan mahsulotlar muvaffaqiyatli yuklandi!")
    except Exception as e:
        print(f"Excel faylni o'qishda xatolik: {e}")

load_products_from_excel()


logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
router = Router()


class AddProduct(StatesGroup):
    article = State()
    name = State()
    category = State()
    media = State()
    volume = State()
    price = State()
    description = State()


class EditProduct(StatesGroup):
    select_prod = State()
    select_field = State()
    new_value = State()


class FeedbackState(StatesGroup):
    text = State()


class CheckoutState(StatesGroup):
    location = State()
    confirm_location = State()
    details = State()
    phone = State()
    payment = State()


def main_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="🛍 Mahsulotlar"), KeyboardButton(text="🛒 Savatcha")],
        [KeyboardButton(text="✍️ Fikr va mulohaza"), KeyboardButton(text="ℹ️ Biz haqimizda")],
        [KeyboardButton(text="🤝 Dillerlar uchun"), KeyboardButton(text="📞 Bog'lanish")],
    ]
    if is_admin:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="✏️ Mahsulotni tahrirlash")],
            [KeyboardButton(text="❌ Mahsulotni o'chirish"), KeyboardButton(text="📋 Mahsulotlar ro'yxati")],
            [KeyboardButton(text="👥 Dillerlar arizalari"), KeyboardButton(text="📥 Fikr-mulohazalarni ko'rish")],
            [KeyboardButton(text="🔙 Asosiy menyu")],
        ],
        resize_keyboard=True,
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        "Assalomu alaykum! **VIRIDI Group** rasmiy Telegram botiga xush kelibsiz.\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=main_menu(is_admin),
        parse_mode="Markdown",
    )


@router.message(F.text.in_(["🔙 Asosiy menyu", "🔙 Bekor qilish"]))
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer("Bosh menyuga qaytdingiz:", reply_markup=main_menu(is_admin))


@router.message(F.text == "ℹ️ Biz haqimizda")
async def about_us(message: Message):
    await message.answer(
        "🌿 **VIRIDI Group** — uy tozalash, kir yuvish, oshxona va vanna-tualet gigiena vositalarining O'zbekistondagi ishonchli yetkazib beruvchisi.\n\n"
        "📞 **Aloqa uchun telefon:** +998937413339\n"
        "👤 **Telegram menejer:** @um1daxon3339",
        parse_mode="Markdown",
    )


@router.message(F.text == "📞 Bog'lanish")
async def contact_us(message: Message):
    await message.answer("📞 Murojaat uchun:\n\n👤 Telegram: @um1daxon3339\n📱 Telefon: +998937413339")


# --- Fikr va mulohaza bo'limi ---
@router.message(F.text == "✍️ Fikr va mulohaza")
async def start_feedback_real(message: Message, state: FSMContext):
    await message.answer("Fikr va mulohazangizni yozib qoldiring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True))
    await state.set_state(FeedbackState.text)


@router.message(FeedbackState.text)
async def save_feedback(message: Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        return
    cursor.execute(
        "INSERT INTO feedback (user_id, full_name, text) VALUES (?, ?, ?)",
        (message.from_user.id, message.from_user.full_name, message.text),
    )
    conn.commit()
    await state.clear()
    await message.answer("Fikringiz uchun rahmat! Adminga yuborildi. ✅", reply_markup=main_menu(message.from_user.id in ADMIN_IDS))


@router.message(F.text == "📥 Fikr-mulohazalarni ko'rish")
async def view_feedbacks(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT full_name, user_id, text FROM feedback")
        rows = cursor.fetchall()
        if not rows:
            await message.answer("Hozircha fikrlar yo'q.")
            return
        text = "📥 **Foydalanuvchilardan fikrlar:**\n\n"
        for r in rows:
            text += f"👤 {r[1]} ({r[0]}):\n💬 {r[2]}\n------------------\n"
        await message.answer(text, parse_mode="Markdown")


# --- Dillerlar bo'limi ---
@router.message(F.text == "🤝 Dillerlar uchun")
async def dealer_section(message: Message):
    cursor.execute("SELECT status FROM dealers WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()

    if res and res[0] == "approved":
        await message.answer("Siz allaqachon diller maqomidasiz!")
    elif res and res[0] == "pending":
        await message.answer("Sizning arizangiz ko'rib chiqilmoqda.")
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
                [KeyboardButton(text="🔙 Asosiy menyu")]
            ],
            resize_keyboard=True,
        )
        await message.answer("Diller bo'lish uchun raqamingizni yuboring:", reply_markup=kb)


@router.message(F.content_type == "contact")
async def get_contact(message: Message):
    contact = message.contact
    cursor.execute(
        "INSERT OR REPLACE INTO dealers (user_id, full_name, phone, status) VALUES (?, ?, ?, ?)",
        (message.from_user.id, message.from_user.full_name, contact.phone_number, "pending"),
    )
    conn.commit()
    await message.answer("Raqamingiz qabul qilindi!", reply_markup=main_menu(message.from_user.id in ADMIN_IDS))
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"👤 Yangi diller arizasi!\nIsm: {message.from_user.full_name}\nTel: {contact.phone_number}")
        except Exception:
            pass


# --- Mahsulotlar va miqdor tanlash ---
@router.message(F.text == "🛍 Mahsulotlar")
async def show_categories(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Uy tozalash", callback_data="cat_homeclean")],
            [InlineKeyboardButton(text="🍳 Oshxona uchun", callback_data="cat_degreaser")],
            [InlineKeyboardButton(text="🧺 Kir yuvish vositalari", callback_data="cat_laundry")],
            [InlineKeyboardButton(text="🚽 Vanna va tualet", callback_data="cat_bathroom")],
            [InlineKeyboardButton(text="🧼 Suyuq sovunlar", callback_data="cat_soap")],
            [InlineKeyboardButton(text="🏢 Kafe va restoranlar uchun", callback_data="cat_cafe")],
            [InlineKeyboardButton(text="🧱 Hovli, kafel va marmarlar", callback_data="cat_yard")],
        ]
    )
    await message.answer("Kerakli kategoriyani tanlang:", reply_markup=kb)


@router.callback_query(F.data.startswith("cat_"))
async def show_products_by_cat(callback: CallbackQuery):
    cat = callback.data.split("_")[1]
    cursor.execute("SELECT id, name, price FROM products WHERE category = ?", (cat,))
    products = cursor.fetchall()

    if not products:
        await callback.message.edit_text("Bu kategoriyada mahsulot yo'q.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_cats")]]))
        return

    kb = []
    for p in products:
        kb.append([InlineKeyboardButton(text=f"{p[1]} — {p[2]} so'm", callback_data=f"prod_{p[0]}_1")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_cats")])
    await callback.message.edit_text("Mahsulotlar ro'yxati:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "back_cats")
async def back_to_cats(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Uy tozalash", callback_data="cat_homeclean")],
            [InlineKeyboardButton(text="🍳 Oshxona uchun", callback_data="cat_degreaser")],
            [InlineKeyboardButton(text="🧺 Kir yuvish vositalari", callback_data="cat_laundry")],
            [InlineKeyboardButton(text="🚽 Vanna va tualet", callback_data="cat_bathroom")],
            [InlineKeyboardButton(text="🧼 Suyuq sovunlar", callback_data="cat_soap")],
            [InlineKeyboardButton(text="🏢 Kafe va restoranlar uchun", callback_data="cat_cafe")],
            [InlineKeyboardButton(text="🧱 Hovli, kafel va marmarlar", callback_data="cat_yard")],
        ]
    )
    await callback.message.edit_text("Kerakli kategoriyani tanlang:", reply_markup=kb)


@router.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery):
    parts = callback.data.split("_")
    prod_id = int(parts[1])
    qty = int(parts[2])

    cursor.execute("SELECT name, volume, price, description, media_id, media_type FROM products WHERE id = ?", (prod_id,))
    p = cursor.fetchone()

    if p:
        total_price = p[2] * qty
        text = f"📦 **{p[0]}**\n💧 **Hajmi:** {p[1]}\n\n💰 Narxi: {p[2]} so'm\n🔢 Miqdori: {qty} ta\n💵 Jami: {total_price} so'm\n\n📝 Tavsif: {p[3]}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="➖", callback_data=f"prod_{prod_id}_{max(1, qty-1)}"),
                    InlineKeyboardButton(text=f"{qty} ta", callback_data="noop"),
                    InlineKeyboardButton(text="➕", callback_data=f"prod_{prod_id}_{qty+1}"),
                ],
                [InlineKeyboardButton(text="🛒 Savatchaga qo'shish", callback_data=f"addcart_{prod_id}_{qty}")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_cats")],
            ]
        )
        if p[4] and p[5] == "photo":
            await callback.message.answer_photo(photo=p[4], caption=text, reply_markup=kb, parse_mode="Markdown")
            await callback.message.delete()
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "noop")
async def noop_cb(callback: CallbackQuery):
    await callback.answer()


# --- Savatcha bo'limi ---
@router.callback_query(F.data.startswith("addcart_"))
async def add_to_cart(callback: CallbackQuery):
    parts = callback.data.split("_")
    prod_id = int(parts[1])
    qty = int(parts[2])
    user_id = callback.from_user.id

    cursor.execute(
        "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = ?",
        (user_id, prod_id, qty, qty),
    )
    conn.commit()
    await callback.answer("Mahsulot savatchaga qo'shildi! 🛒", show_alert=True)


@router.message(F.text == "🛒 Savatcha")
async def show_cart(message: Message):
    user_id = message.from_user.id
    cursor.execute(
        """
        SELECT p.name, c.quantity, p.price, c.product_id 
        FROM cart c JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
    """,
        (user_id,),
    )
    items = cursor.fetchall()

    if not items:
        await message.answer("Savatchangiz bo'sh. 🛒")
        return

    text = "🛒 **Sizning savatchangiz:**\n\n"
    grand_total = 0
    for name, qty, price, pid in items:
        summa = qty * price
        grand_total += summa
        text += f"• {name} — {qty} ta x {price} = {summa} so'm\n"

    text += f"\n💵 **Umumiy summa:** {grand_total} so'm"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Buyurtmani rasmiylashtirish", callback_data="start_checkout")],
            [InlineKeyboardButton(text="🗑 Savatchani tozalash", callback_data="clear_cart")],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    await callback.message.edit_text("Savatcha tozalandi.")


# --- BUYURTMA RASMIYLASHTIRISH JARAYONI (CHECKOUT) ---
@router.callback_query(F.data == "start_checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cursor.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] == 0:
        await callback.answer("Savatchangiz bo'sh!", show_alert=True)
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Geolokatsiyani yuborish", request_location=True)],
            [KeyboardButton(text="🔙 Bekor qilish")]
        ],
        resize_keyboard=True
    )
    await callback.message.delete()
    await callback.message.answer("🚚 Buyurtmani yetkazib berish uchun iltimos, **Geolokatsiyangizni** yuboring (Pastdagi tugmani bosing):", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(CheckoutState.location)


@router.message(CheckoutState.location)
async def process_location(message: Message, state: FSMContext):
    if not message.location:
        await message.answer("Iltimos, pastdagi '📍 Geolokatsiyani yuborish' tugmasi orqali joylashuvingizni yuboring.")
        return

    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Ha"), KeyboardButton(text="❌ Yo'q")],
            [KeyboardButton(text="🔙 Bekor qilish")]
        ],
        resize_keyboard=True
    )
    await message.answer("Siz yuborgan manzilga yetkazib berishimiz kerakmi?", reply_markup=kb)
    await state.set_state(CheckoutState.confirm_location)


@router.message(CheckoutState.confirm_location)
async def process_confirm_loc(message: Message, state: FSMContext):
    if message.text == "❌ Yo'q":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📍 Geolokatsiyani yuborish", request_location=True)],
                [KeyboardButton(text="🔙 Bekor qilish")]
            ],
            resize_keyboard=True
        )
        await message.answer("Unda iltimos, to'g'ri geolokatsiyani qaytadan yuboring:", reply_markup=kb)
        await state.set_state(CheckoutState.location)
        return
    elif message.text == "✅ Ha":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True)
        await message.answer("Manzilni topish oson bo'lishi uchun qo'shimcha ma'lumotlarni yozib qoldiring:\n\n*(Masalan: Mahalla nomi, ko'cha, uy raqami, dom, kvartira yoki mo'ljal)*", reply_markup=kb, parse_mode="Markdown")
        await state.set_state(CheckoutState.details)
    else:
        await message.answer("Iltimos, pastdagi tugmalardan foydalaning.")


@router.message(CheckoutState.details)
async def process_details(message: Message, state: FSMContext):
    await state.update_data(details=message.text)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="🔙 Bekor qilish")]
        ],
        resize_keyboard=True
    )
    await message.answer("Bog'lanish uchun aniq telefon raqamingizni yuboring yoki yozib qoldiring:", reply_markup=kb)
    await state.set_state(CheckoutState.phone)


@router.message(CheckoutState.phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💵 Naqd pul"), KeyboardButton(text="💳 Kartaga o'tkazma")],
            [KeyboardButton(text="🔙 Bekor qilish")]
        ],
        resize_keyboard=True
    )
    await message.answer("To'lov turini tanlang:", reply_markup=kb)
    await state.set_state(CheckoutState.payment)


@router.message(CheckoutState.payment)
async def process_payment(message: Message, state: FSMContext):
    if message.text not in ["💵 Naqd pul", "💳 Kartaga o'tkazma"]:
        await message.answer("Iltimos, pastdagi to'lov turlaridan birini tanlang:")
        return

    payment_method = message.text
    data = await state.get_data()
    user_id = message.from_user.id

    cursor.execute(
        """
        SELECT p.article, p.name, c.quantity, p.price 
        FROM cart c JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
    """,
        (user_id,),
    )
    items = cursor.fetchall()

    if not items:
        await message.answer("Savatcha bo'sh!", reply_markup=main_menu(user_id in ADMIN_IDS))
        await state.clear()
        return

    lat = data.get('lat')
    lon = data.get('lon')
    maps_link = f"https://maps.google.com/?q={lat},{lon}"
    
    admin_text = f"🚨 **YANGI BUYURTMA!**\n\n"
    admin_text += f"👤 **Mijoz:** {message.from_user.full_name} (@{message.from_user.username or 'yoq'})\n"
    admin_text += f"📱 **Tel:** `{data['phone']}`\n"
    admin_text += f"📍 **Lokatsiya:** [Xaritada ochish]({maps_link})\n"
    admin_text += f"🏠 **Manzil:** {data['details']}\n"
    admin_text += f"💳 **To'lov turi:** {payment_method}\n\n"
    admin_text += f"📦 **Buyurtma qilingan mahsulotlar:**\n"

    grand_total = 0
    for article, name, qty, price in items:
        summa = qty * price
        grand_total += summa
        art_str = f"[{article}] " if article else ""
        admin_text += f"• {art_str}{name} — {qty} ta | {summa} so'm\n"

    admin_text += f"\n💵 **Jami narx:** {grand_total} so'm"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            pass

    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()

    user_msg = "✅ **Buyurtmangiz muvaffaqiyatli qabul qilindi va adminga yuborildi!**\nTez orada yetkazib berish bo'yicha siz bilan bog'lanishadi.\n\n"
    if payment_method == "💳 Kartaga o'tkazma":
        user_msg += "💳 **Karta raqam (O'tkazma uchun):**\n`4916990355551166`\nShu raqamga to'lov qilishingiz mumkin."
    else:
        user_msg += "To'lovni mahsulot qo'lingizga yetib borganda naqd pulda amalga oshirishingiz mumkin."

    await message.answer(user_msg, reply_markup=main_menu(message.from_user.id in ADMIN_IDS), parse_mode="Markdown")
    await state.clear()


# --- Admin Panel ---
@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Admin panel:", reply_markup=admin_menu())


@router.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Mahsulotning **Artikul** raqamini kiriting (masalan: ART-001):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True))
        await state.set_state(AddProduct.article)


@router.message(AddProduct.article)
async def process_article(message: Message, state: FSMContext):
    await state.update_data(article=message.text)
    await message.answer("Endi mahsulot nomini kiriting:")
    await state.set_state(AddProduct.name)


@router.message(AddProduct.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Uy tozalash", callback_data="setcat_homeclean")],
            [InlineKeyboardButton(text="Oshxona uchun", callback_data="setcat_degreaser")],
            [InlineKeyboardButton(text="Kir yuvish", callback_data="setcat_laundry")],
            [InlineKeyboardButton(text="Vanna/Tualet", callback_data="setcat_bathroom")],
            [InlineKeyboardButton(text="Suyuq sovun", callback_data="setcat_soap")],
            [InlineKeyboardButton(text="Kafe va restoranlar", callback_data="setcat_cafe")],
            [InlineKeyboardButton(text="Hovli va marmar", callback_data="setcat_yard")],
        ]
    )
    await message.answer("Kategoriyani tanlang:", reply_markup=kb)
    await state.set_state(AddProduct.category)


@router.callback_query(F.data.startswith("setcat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.split("_")[1]
    await state.update_data(category=cat)
    await callback.message.answer("Endi mahsulot uchun rasm yoki video yuboring:")
    await state.set_state(AddProduct.media)


@router.message(AddProduct.media, F.photo)
async def process_photo_media(message: Message, state: FSMContext):
    await state.update_data(media_id=message.photo[-1].file_id, media_type="photo")
    await message.answer("Mahsulot hajmini kiriting (masalan: 1L, 5L):")
    await state.set_state(AddProduct.volume)


@router.message(AddProduct.media, F.video)
async def process_video_media(message: Message, state: FSMContext):
    await state.update_data(media_id=message.video.file_id, media_type="video")
    await message.answer("Mahsulot hajmini kiriting (masalan: 1L, 5L):")
    await state.set_state(AddProduct.volume)


@router.message(AddProduct.volume)
async def process_volume(message: Message, state: FSMContext):
    await state.update_data(volume=message.text)
    await message.answer("Mahsulot narxini raqamlarda kiriting (masalan: 45000):")
    await state.set_state(AddProduct.price)


@router.message(AddProduct.price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 45000):")
        return
    await state.update_data(price=float(message.text))
    await message.answer("Tavsif yozing:")
    await state.set_state(AddProduct.description)


@router.message(AddProduct.description)
async def process_description(message: Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute(
        "INSERT INTO products (article, name, category, volume, price, description, media_id, media_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (data["article"], data["name"], data["category"], data["volume"], data["price"], message.text, data["media_id"], data["media_type"]),
    )
    conn.commit()
    await state.clear()
    await message.answer("Mahsulot muvaffaqiyatli qo'shildi! ✅", reply_markup=admin_menu())


# --- Mahsulotni tahrirlash ---
@router.message(F.text == "✏️ Mahsulotni tahrirlash")
async def start_edit_product(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, article, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Tahrirlash uchun mahsulotlar yo'q.")
            return
        
        kb = []
        for p in products:
            art = f"[{p[1]}] " if p[1] else ""
            kb.append([InlineKeyboardButton(text=f"{art}{p[2]} — {p[3]} so'm", callback_data=f"editprod_{p[0]}")])
        
        await message.answer("Qaysi mahsulotni tahrirlamoqchisiz? Tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith("editprod_"))
async def select_product_field(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    await state.update_data(edit_prod_id=prod_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏷 Artikulini o'zgartirish", callback_data="editfield_article")],
            [InlineKeyboardButton(text="📦 Nomini o'zgartirish", callback_data="editfield_name")],
            [InlineKeyboardButton(text="💧 Hajmini o'zgartirish", callback_data="editfield_volume")],
            [InlineKeyboardButton(text="💰 Narxini o'zgartirish", callback_data="editfield_price")],
            [InlineKeyboardButton(text="📝 Tavsifini o'zgartirish", callback_data="editfield_description")],
            [InlineKeyboardButton(text="🖼 Rasmini/Videosini o'zgartirish", callback_data="editfield_media")],
        ]
    )
    await callback.message.edit_text("Mahsulotning qaysi qismini o'zgartirmoqchisiz?", reply_markup=kb)


@router.callback_query(F.data.startswith("editfield_"))
async def select_field_to_edit(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    await state.update_data(edit_field=field)

    field_names = {
        "article": "Yangi artikul raqamini kiriting:",
        "name": "Yangi mahsulot nomini kiriting:",
        "volume": "Yangi hajmini kiriting (masalan: 1L, 5L):",
        "price": "Yangi narxini raqamlarda kiriting (masalan: 50000):",
        "description": "Yangi tavsifini kiriting:",
        "media": "Yangi rasm yoki video yuboring:"
    }
    
    await callback.message.answer(field_names.get(field, "Yangi qiymatni kiriting:"), reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True))
    await state.set_state(EditProduct.new_value)


@router.message(EditProduct.new_value)
async def save_edited_field(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    field = data["edit_field"]

    if field == "media":
        if message.photo:
            media_id = message.photo[-1].file_id
            cursor.execute("UPDATE products SET media_id = ?, media_type = 'photo' WHERE id = ?", (media_id, prod_id))
        elif message.video:
            media_id = message.video.file_id
            cursor.execute("UPDATE products SET media_id = ?, media_type = 'video' WHERE id = ?", (media_id, prod_id))
        else:
            await message.answer("Iltimos, rasm yoki video yuboring:")
            return
    else:
        new_val = message.text
        if field == "price":
            if not new_val.isdigit():
                await message.answer("Iltimos, faqat raqam kiriting:")
                return
            new_val = float(new_val)
        
        cursor.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (new_val, prod_id))

    conn.commit()
    await state.clear()
    await message.answer("Mahsulot muvaffaqiyatli yangilandi! ✅", reply_markup=admin_menu())


@router.message(F.text == "❌ Mahsulotni o'chirish")
async def start_delete_product(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, article, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("O'chirish uchun mahsulotlar yo'q.")
            return
        text = "O'chirmoqchi bo'lgan mahsulot ID raqamini yozing:\n\n"
        for p in products:
            art = f"[{p[1]}] " if p[1] else ""
            text += f"ID: {p[0]} | {art}{p[2]} — {p[3]} so'm\n"
        await message.answer(text)


@router.message(F.text == "📋 Mahsulotlar ro'yxati")
async def show_products_list(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, article, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Hozircha bazada mahsulotlar yo'q.")
            return
        
        text = "📋 **Bazadagi barcha mahsulotlar:**\n\n"
        for p in products:
            art = f"[{p[1]}] " if p[1] else ""
            text += f"ID: {p[0]} | {art}{p[2]} — {p[3]} so'm\n"
        
        await message.answer(text, parse_mode="Markdown")


PORT = int(os.environ.get("PORT", 10000))

async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()


async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await web_server()
    print("Bot tayyor va ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
