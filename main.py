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

# Bazalarni yaratish
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
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    lang TEXT
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


# --- RUSCHA MATNLARNI O'ZBEK TILIGA TARJIMA QILISH FUNKSIYasi ---
def translate_to_uzbek(text):
    if not text or pd.isna(text):
        return ""
    
    # Asosiy so'zlarni o'zbekchaga o'girish lug'ati
    translations = {
        "Жидкое мыло": "Suyuq sovun",
        "жидкое мыло": "suyuq sovun",
        "Мыло": "Sovun",
        "мыло": "sovun",
        "Антижир": "Yog'ga qarshi vosita (Antijir)",
        "антижир": "yog'ga qarshi vosita",
        "Универсальный": "Universal tozalovchi",
        "универсальный": "universal",
        "для кухни": "oshxona uchun",
        "для стирки": "kir yuvish uchun",
        "для туалета": "tualet uchun",
        "для ванной": "vanna uchun",
        "для пола": "pol uchun",
        "Описание": "Tavsif yo'q",
        "Источники Исландидии": "Islandiya buloqlari",
        "Сказочное Бали": "Ertaknamo Bali",
        "Сокровища Африки": "Afrika xazinalari"
    }
    
    for ru, uz in translations.items():
        text = text.replace(ru, uz)
    return text


# --- EXCEL FAYLDAN MAHSULOTLARNI O'QISH VA TARJIMA QILIB YUKLASH ---
def load_products_from_excel():
    excel_file = "Прайс.xlsx"
    if not os.path.exists(excel_file):
        return
    
    try:
        df = pd.read_excel(excel_file)
        for _, row in df.iterrows():
            raw_name = str(row.get("Название", ""))
            if pd.isna(raw_name) or not raw_name or raw_name == "nan":
                continue
            
            # Nom va tavsifni o'zbek tiliga tarjima qilamiz
            name = translate_to_uzbek(raw_name)
            raw_desc = str(row.get("Описание", ""))
            description = translate_to_uzbek(raw_desc)
            
            article = str(row.get("Артикул", ""))
            price = float(row.get("цена", 0) if not pd.isna(row.get("цена")) else 0)
            
            volume = "500 ml"
            name_lower = raw_name.lower()
            if "1000 мл" in name_lower or "1 л" in name_lower:
                volume = "1000 ml"
            elif "5200 мл" in name_lower or "5 л" in name_lower:
                volume = "5200 ml"
            elif "750 мл" in name_lower:
                volume = "750 ml"
            elif "1200 мл" in name_lower:
                volume = "1200 ml"

            category = "homeclean"
            if "мыло" in name_lower or "cream-мыло" in name_lower:
                category = "soap"
            elif "антижир" in name_lower or "кухню" in name_lower or "жиру нет" in name_lower:
                category = "degreaser"
            elif "стирки" in name_lower or "гель для стирки" in name_lower or "кондиционер" in name_lower:
                category = "laundry"
            elif "туалета" in name_lower or "ванной" in name_lower or "virsant" in name_lower:
                category = "bathroom"

            cursor.execute("SELECT id FROM products WHERE article = ? OR name = ?", (article, name))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO products (article, name, category, volume, price, description, media_type) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (article, name, category, volume, price, description, "photo")
                )
        conn.commit()
    except Exception as e:
        print(f"Excel xatosi: {e}")

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


class DeleteProductState(StatesGroup):
    product_id = State()


class FeedbackState(StatesGroup):
    text = State()


class CheckoutState(StatesGroup):
    location = State()
    confirm_location = State()
    details = State()
    phone = State()
    payment = State()


def get_user_lang(user_id):
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else "uz"


def main_menu(lang="uz", is_admin=False):
    if lang == "ru":
        kb = [
            [KeyboardButton(text="🛍 Товары"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="✍️ Отзывы"), KeyboardButton(text="ℹ️ О нас")],
            [KeyboardButton(text="🤝 Для дилеров"), KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="🌐 Сменить язык")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Админ панель")])
    else:
        kb = [
            [KeyboardButton(text="🛍 Mahsulotlar"), KeyboardButton(text="🛒 Savatcha")],
            [KeyboardButton(text="✍️ Fikr va mulohaza"), KeyboardButton(text="ℹ️ Biz haqimizda")],
            [KeyboardButton(text="🤝 Dillerlar uchun"), KeyboardButton(text="📞 Bog'lanish")],
            [KeyboardButton(text="🌐 Tilni o'zgartirish")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_menu(lang="uz"):
    if lang == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="✏️ Редактировать товар")],
                [KeyboardButton(text="❌ Удалить товар"), KeyboardButton(text="📋 Список товаров")],
                [KeyboardButton(text="👥 Заявки дилеров"), KeyboardButton(text="📥 Просмотр отзывов")],
                [KeyboardButton(text="🔙 Главное меню")],
            ],
            resize_keyboard=True,
        )
    else:
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
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
            ]
        ]
    )
    await message.answer("Iltimos, tilni tanlang / Пожалуйста, выберите язык:", reply_markup=kb)


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, full_name, lang) VALUES (?, ?, ?)",
        (user_id, callback.from_user.full_name, lang)
    )
    conn.commit()
    
    is_admin = user_id in ADMIN_IDS
    if lang == "ru":
        text = "Вы успешно выбрали русский язык! Добро пожаловать в официальный бот **VIRIDI Group**:"
    else:
        text = "Siz o'zbek tilini tanladingiz! **VIRIDI Group** rasmiy botiga xush kelibsiz:"
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.answer("Kerakli bo'limni tanlang:" if lang == "uz" else "Выберите нужный раздел:", reply_markup=main_menu(lang, is_admin))


@router.message(F.text.in_(["🌐 Tilni o'zgartirish", "🌐 Сменить язык"]))
async def change_lang_btn(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
            ]
        ]
    )
    await message.answer("Tilni tanlang / Выберите язык:", reply_markup=kb)


@router.message(F.text.in_(["🔙 Asosiy menyu", "🔙 Главное меню", "🔙 Bekor qilish", "🔙 Отмена"]))
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    lang = get_user_lang(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer("Asosiy menyu:" if lang == "uz" else "Главное меню:", reply_markup=main_menu(lang, is_admin))


@router.message(F.text.in_(["ℹ️ Biz haqimizda", "ℹ️ О нас"]))
async def about_us(message: Message):
    lang = get_user_lang(message.from_user.id)
    if lang == "ru":
        text = "🌿 **VIRIDI Group** — надежный поставщик средств для уборки дома, стирки, кухни и ванной в Узбекистане.\n\n📞 **Телефон:** +998937413339\n👤 **Менеджер:** @um1daxon3339"
    else:
        text = "🌿 **VIRIDI Group** — uy tozalash, kir yuvish, oshxona va vanna-tualet vositalarining O'zbekistondagi ishonchli yetkazib beruvchisi.\n\n📞 **Telefon:** +998937413339\n👤 **Menejer:** @um1daxon3339"
    await message.answer(text, parse_mode="Markdown")


@router.message(F.text.in_(["📞 Bog'lanish", "📞 Контакты"]))
async def contact_us(message: Message):
    lang = get_user_lang(message.from_user.id)
    if lang == "ru":
        text = "📞 Контакты:\n\n👤 Telegram: @um1daxon3339\n📱 Телефон: +998937413339"
    else:
        text = "📞 Murojaat uchun:\n\n👤 Telegram: @um1daxon3339\n📱 Telefon: +998937413339"
    await message.answer(text)


@router.message(F.text.in_(["✍️ Fikr va mulohaza", "✍️ Отзывы"]))
async def start_feedback_real(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    cancel_text = "🔙 Отмена" if lang == "ru" else "🔙 Bekor qilish"
    await message.answer("Fikringizni yozib qoldiring:" if lang == "uz" else "Напишите ваш отзыв:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel_text)]], resize_keyboard=True))
    await state.set_state(FeedbackState.text)


@router.message(FeedbackState.text)
async def save_feedback(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    cursor.execute("INSERT INTO feedback (user_id, full_name, text) VALUES (?, ?, ?)", (message.from_user.id, message.from_user.full_name, message.text))
    conn.commit()
    await state.clear()
    await message.answer("Rahmat! Adminga yuborildi. ✅" if lang == "uz" else "Спасибо! Отправлено админу. ✅", reply_markup=main_menu(lang, message.from_user.id in ADMIN_IDS))


@router.message(F.text.in_(["🛍 Mahsulotlar", "🛍 Товары"]))
async def show_categories(message: Message):
    lang = get_user_lang(message.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Uy tozalash" if lang == "uz" else "🏠 Уборка дома", callback_data="cat_homeclean")],
            [InlineKeyboardButton(text="🍳 Oshxona uchun" if lang == "uz" else "🍳 Для кухни", callback_data="cat_degreaser")],
            [InlineKeyboardButton(text="🧺 Kir yuvish" if lang == "uz" else "🧺 Для стирки", callback_data="cat_laundry")],
            [InlineKeyboardButton(text="🚽 Vanna va tualet" if lang == "uz" else "🚽 Ванная и туалет", callback_data="cat_bathroom")],
            [InlineKeyboardButton(text="🧼 Suyuq sovunlar" if lang == "uz" else "🧼 Жидкое мыло", callback_data="cat_soap")],
        ]
    )
    await message.answer("Kategoriyani tanlang:" if lang == "uz" else "Выберите категорию:", reply_markup=kb)


@router.callback_query(F.data.startswith("cat_"))
async def show_products_by_cat(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    cat = callback.data.split("_")[1]
    cursor.execute("SELECT id, name, price FROM products WHERE category = ?", (cat,))
    products = cursor.fetchall()

    if not products:
        back_text = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
        await callback.message.edit_text("Bu kategoriyada mahsulot yo'q." if lang == "uz" else "В этой категории нет товаров.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="back_cats")]]))
        return

    kb = []
    for p in products:
        kb.append([InlineKeyboardButton(text=f"{p[1]} — {p[2]} so'm", callback_data=f"prod_{p[0]}_1")])
    back_text = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
    kb.append([InlineKeyboardButton(text=back_text, callback_data="back_cats")])
    await callback.message.edit_text("Mahsulotlar:" if lang == "uz" else "Товары:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "back_cats")
async def back_to_cats(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Uy tozalash" if lang == "uz" else "🏠 Уборка дома", callback_data="cat_homeclean")],
            [InlineKeyboardButton(text="🍳 Oshxona uchun" if lang == "uz" else "🍳 Для кухни", callback_data="cat_degreaser")],
            [InlineKeyboardButton(text="🧺 Kir yuvish" if lang == "uz" else "🧺 Для стирки", callback_data="cat_laundry")],
            [InlineKeyboardButton(text="🚽 Vanna va tualet" if lang == "uz" else "🚽 Ванная и туалет", callback_data="cat_bathroom")],
            [InlineKeyboardButton(text="🧼 Suyuq sovunlar" if lang == "uz" else "🧼 Жидкое мыло", callback_data="cat_soap")],
        ]
    )
    await callback.message.edit_text("Kategoriyani tanlang:" if lang == "uz" else "Выберите категорию:", reply_markup=kb)


@router.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    parts = callback.data.split("_")
    prod_id, qty = int(parts[1]), int(parts[2])

    cursor.execute("SELECT name, volume, price, description, media_id, media_type FROM products WHERE id = ?", (prod_id,))
    p = cursor.fetchone()

    if p:
        total_price = p[2] * qty
        if lang == "ru":
            text = f"📦 **{p[0]}**\n💧 **Объем:** {p[1]}\n\n💰 Цена: {p[2]} сум\n🔢 Кол-во: {qty} шт.\n💵 Итого: {total_price} сум\n\n📝 Описание: {p[3]}"
            add_cart = "🛒 В корзину"
            back = "🔙 Назад"
        else:
            text = f"📦 **{p[0]}**\n💧 **Hajmi:** {p[1]}\n\n💰 Narxi: {p[2]} so'm\n🔢 Miqdori: {qty} ta\n💵 Jami: {total_price} so'm\n\n📝 Tavsif: {p[3]}"
            add_cart = "🛒 Savatchaga qo'shish"
            back = "🔙 Orqaga"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="➖", callback_data=f"prod_{prod_id}_{max(1, qty-1)}"),
                    InlineKeyboardButton(text=f"{qty} ta" if lang == "uz" else f"{qty} шт.", callback_data="noop"),
                    InlineKeyboardButton(text="➕", callback_data=f"prod_{prod_id}_{qty+1}"),
                ],
                [InlineKeyboardButton(text=add_cart, callback_data=f"addcart_{prod_id}_{qty}")],
                [InlineKeyboardButton(text=back, callback_data="back_cats")],
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


@router.callback_query(F.data.startswith("addcart_"))
async def add_to_cart(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    parts = callback.data.split("_")
    cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = ?", (callback.from_user.id, int(parts[1]), int(parts[2]), int(parts[2])))
    conn.commit()
    await callback.answer("Savatchaga qo'shildi! 🛒" if lang == "uz" else "Добавлено в корзину! 🛒", show_alert=True)


@router.message(F.text.in_(["🛒 Savatcha", "🛒 Корзина"]))
async def show_cart(message: Message):
    lang = get_user_lang(message.from_user.id)
    cursor.execute("SELECT p.name, c.quantity, p.price, c.product_id FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = ?", (message.from_user.id,))
    items = cursor.fetchall()

    if not items:
        await message.answer("Savatchangiz bo'sh. 🛒" if lang == "uz" else "Ваша корзина пуста. 🛒")
        return

    text = "🛒 **Sizning savatchangiz:**\n\n" if lang == "uz" else "🛒 **Ваша корзина:**\n\n"
    grand_total = 0
    for name, qty, price, pid in items:
        summa = qty * price
        grand_total += summa
        text += f"• {name} — {qty} x {price} = {summa} so'm\n"

    text += f"\n💵 **Jami:** {grand_total} so'm"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Buyurtma berish" if lang == "uz" else "✅ Оформить заказ", callback_data="start_checkout")],
            [InlineKeyboardButton(text="🗑 Tozalash" if lang == "uz" else "🗑 Очистить", callback_data="clear_cart")],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    await callback.message.edit_text("Savatcha tozalandi." if lang == "uz" else "Корзина очищена.")


# --- CHECKOUT ---
@router.callback_query(F.data == "start_checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    lang = get_user_lang(callback.from_user.id)
    cursor.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (callback.from_user.id,))
    if cursor.fetchone()[0] == 0:
        await callback.answer("Savatcha bo'sh!", show_alert=True)
        return

    loc_btn = "📍 Geolokatsiyani yuborish" if lang == "uz" else "📍 Отправить геолокацию"
    cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=loc_btn, request_location=True)], [KeyboardButton(text=cancel)]], resize_keyboard=True)
    await callback.message.delete()
    await callback.message.answer("🚚 Geolokatsiyangizni yuboring:" if lang == "uz" else "🚚 Отправьте вашу геолокацию:", reply_markup=kb)
    await state.set_state(CheckoutState.location)


@router.message(CheckoutState.location)
async def process_location(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    if not message.location:
        await message.answer("Iltimos, tugma orqali lokatsiya yuboring." if lang == "uz" else "Пожалуйста, отправьте локацию через кнопку.")
        return
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Ha" if lang == "uz" else "✅ Да"), KeyboardButton(text="❌ Yo'q" if lang == "uz" else "❌ Нет")], [KeyboardButton(text="🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена")]], resize_keyboard=True)
    await message.answer("Manzilni tasdiqlaysizmi?" if lang == "uz" else "Подтверждаете адрес?", reply_markup=kb)
    await state.set_state(CheckoutState.confirm_location)


@router.message(CheckoutState.confirm_location)
async def process_confirm_loc(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    if message.text in ["❌ Yo'q", "❌ Нет"]:
        loc_btn = "📍 Geolokatsiyani yuborish" if lang == "uz" else "📍 Отправить геолокацию"
        cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=loc_btn, request_location=True)], [KeyboardButton(text=cancel)]], resize_keyboard=True)
        await message.answer("Qaytadan yuboring:" if lang == "uz" else "Отправьте заново:", reply_markup=kb)
        await state.set_state(CheckoutState.location)
        return
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена")]], resize_keyboard=True)
    await message.answer("Mo'ljal yoki uy raqamini yozing:" if lang == "uz" else "Напишите ориентир или номер дома:", reply_markup=kb)
    await state.set_state(CheckoutState.details)


@router.message(CheckoutState.details)
async def process_details(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    await state.update_data(details=message.text)
    phone_btn = "📱 Telefon raqamni yuborish" if lang == "uz" else "📱 Отправить номер телефона"
    cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=phone_btn, request_contact=True)], [KeyboardButton(text=cancel)]], resize_keyboard=True)
    await message.answer("Telefon raqamingizni yuboring:" if lang == "uz" else "Отправьте ваш номер телефона:", reply_markup=kb)
    await state.set_state(CheckoutState.phone)


@router.message(CheckoutState.phone)
async def process_phone(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="💵 Naqd pul" if lang == "uz" else "💵 Наличные"), KeyboardButton(text="💳 Karta" if lang == "uz" else "💳 Перевод")], [KeyboardButton(text="🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена")]], resize_keyboard=True)
    await message.answer("To'lov turini tanlang:" if lang == "uz" else "Выберите тип оплаты:", reply_markup=kb)
    await state.set_state(CheckoutState.payment)


@router.message(CheckoutState.payment)
async def process_payment(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    payment_method = message.text
    data = await state.get_data()
    user_id = message.from_user.id

    cursor.execute("SELECT p.article, p.name, c.quantity, p.price FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = ?", (user_id,))
    items = cursor.fetchall()
    if not items:
        await message.answer("Savatcha bo'sh!", reply_markup=main_menu(lang, user_id in ADMIN_IDS))
        await state.clear()
        return

    maps_link = f"https://maps.google.com/?q={data['lat']},{data['lon']}"
    admin_text = f"🚨 **YANGI BUYURTMA!**\n\n👤 Mijoz: {message.from_user.full_name}\n📱 Tel: `{data['phone']}`\n📍 [Xaritada ko'rish]({maps_link})\n🏠 Manzil: {data['details']}\n💳 To'lov: {payment_method}\n\n📦 Mahsulotlar:\n"
    grand_total = 0
    for article, name, qty, price in items:
        summa = qty * price
        grand_total += summa
        admin_text += f"• {name} — {qty} ta | {summa} so'm\n"
    admin_text += f"\n💵 Jami: {grand_total} so'm"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            pass

    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()

    user_msg = "✅ Buyurtmangiz qabul qilindi!" if lang == "uz" else "✅ Ваш заказ принят!"
    await message.answer(user_msg, reply_markup=main_menu(lang, user_id in ADMIN_IDS))
    await state.clear()


@router.message(F.text.in_(["⚙️ Admin Panel", "⚙️ Админ панель"]))
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        await message.answer("Admin panel:", reply_markup=admin_menu(lang))


# --- MAHSULOTNI O'CHIRISH VA ADMINGA XABAR BERISH ---
@router.message(F.text.in_(["❌ Mahsulotni o'chirish", "❌ Удалить товар"]))
async def start_delete_product(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        cursor.execute("SELECT id, article, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("O'chirish uchun mahsulotlar yo'q." if lang == "uz" else "Нет товаров для удаления.")
            return
        
        text = "O'chirmoqchi bo'lgan mahsulot **ID raqamini** yozing:\n\n" if lang == "uz" else "Введите **ID номер** товара, который хотите удалить:\n\n"
        for p in products:
            art = f"[{p[1]}] " if p[1] else ""
            text += f"ID: {p[0]} | {art}{p[2]} — {p[3]} so'm\n"
        
        cancel_text = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
        await message.answer(text, reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel_text)]], resize_keyboard=True), parse_mode="Markdown")
        await state.set_state(DeleteProductState.product_id)


@router.message(DeleteProductState.product_id)
async def process_delete_product(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu(lang))
        return

    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam (ID) kiriting:" if lang == "uz" else "Пожалуйста, введите только цифру (ID):")
        return

    prod_id = int(message.text)
    cursor.execute("SELECT id, name, article FROM products WHERE id = ?", (prod_id,))
    prod = cursor.fetchone()

    if not prod:
        await message.answer("Bunday ID raqamli mahsulot topilmadi. Qaytadan kiriting:" if lang == "uz" else "Товар с таким ID не найден. Введите заново:")
        return

    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    await state.clear()
    
    success_text = f"✅ '{prod[1]}' nomli mahsulot muvaffaqiyatli o'chirildi!" if lang == "uz" else f"✅ Товар '{prod[1]}' успешно удален!"
    await message.answer(success_text, reply_markup=admin_menu(lang))

    admin_notification = (
        f"🗑 **MAHSULOT O'CHIRILDI!**\n\n"
        f"👤 **O'chirgan admin:** {message.from_user.full_name}\n"
        f"📦 **Mahsulot ID:** {prod[0]}\n"
        f"🏷 **Artikul:** {prod[2] if prod[2] else 'Yo\'q'}\n"
        f"📝 **Nomi:** {prod[1]}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_notification, parse_mode="Markdown")
        except Exception:
            pass


@router.message(F.text.in_(["📋 Mahsulotlar ro'yxati", "📋 Список товаров"]))
async def show_products_list(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, article, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Bazada mahsulotlar yo'q.")
            return
        text = "📋 **Mahsulotlar:**\n\n"
        for p in products:
            text += f"ID: {p[0]} | {p[2]} — {p[3]} so'm\n"
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
    print("Bot ishga tushdi va tarjima funksiyasi ishlamoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
