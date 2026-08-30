import asyncio
import logging
import os
import sqlite3
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


# --- BARCHA 46 TA MAHSULOTNI ARTIKULI BILAN BAZAGA YOZISH ---
def init_default_products():
    products_list = [
        # Suyuq sovunlar / Krem-sovunlar (soap)
        ("140105", "VIRIS Olchali tort", "soap", "500 ml", 30000, "paxta urug'i yog'li gipoallergen suyuq krem-sovun 0+"),
        ("110110", "VIRida Ertaknamo Bali", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, kokos yog'i bilan"),
        ("110210", "VIRida Afrika xazinalari", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, argan yog'i bilan"),
        ("110310", "VIRida Islandiya buloqlari", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, paxta urug'i yog'i bilan"),
        ("110410", "VIRida Fudzi afsonalari", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq krem-sovun, 0+, gipoallergen, paxta urug'i yog'i bilan"),
        ("110152", "VIRida Ertaknamo Bali", "soap", "5200 ml", 125000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, kokos yog'i bilan"),
        ("110252", "VIRida Afrika xazinalari", "soap", "5200 ml", 125000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, argan yog'i bilan"),
        ("110352", "VIRida Islandiya buloqlari", "soap", "5200 ml", 125000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, paxta urug'i yog'i bilan"),
        ("110452", "VIRida Fudzi afsonalari", "soap", "5200 ml", 130000, "4 xil gialuronli antibakterial suyuq krem-sovun, 0+, gipoallergen, paxta urug'i yog'i bilan"),

        # Oshxona uchun (degreaser)
        ("210105", "VIRjet Antijir", "degreaser", "500 ml", 40000, "Konsentrlangan oshxona vositasi yog' va kuyiklarga qarshi, hidsiz"),
        ("280505", "Viris Yog'ga yo'q!", "degreaser", "500 ml", 35000, "Oshxona vositasi yog' va kuyiklarga qarshi, hidsiz"),
        ("260110", "VIRma idish yuvish geli", "degreaser", "1000 ml", 50000, "Gialuron kislotali konsentrlangan gel, meva va bolalar idishlari uchun"),
        ("260152", "VIRma idish yuvish geli", "degreaser", "5200 ml", 180000, "Gialuron kislotali konsentrlangan gel, meva va bolalar idishlari uchun"),
        ("260452", "VIRma RETRO COLLECTION", "degreaser", "5200 ml", 130000, "Moychechak ekstraktli konsentrlangan idish yuvish geli"),
        ("260352", "VIRma Tog' o'tlari", "degreaser", "5200 ml", 130000, "Tog' o'tlari ekstraktli konsentrlangan idish yuvish geli"),
        ("260552", "Virma - Pamelo", "degreaser", "5200 ml", 130000, "Pamelo xushbo'y konsentrlangan idish yuvish geli"),

        # Uy tozalash va pol yuvish uchun (homeclean) — VIRlan PRO S6 shu yerga ko'chirildi
        ("210205", "VIRjet Universal", "homeclean", "500 ml", 40000, "Mebellar va qattiq yuzalar uchun universal dog' tozalovchi"),
        ("280605", "Viris Hammasi toza!", "homeclean", "500 ml", 35000, "Mebellar va yuzalar uchun universal dog' tozalovchi"),
        ("240110", "Viround liliya va gortenziya", "homeclean", "1000 ml", 40000, "Pol yuvish uchun konsentrlangan antibakterial vosita"),
        ("240210", "VIRound Life planet", "homeclean", "1000 ml", 40000, "Bergamot va jasminli pol yuvish vositasi"),
        ("240310", "Viround Moonlight", "homeclean", "1000 ml", 40000, "Parfyumlangan konsentrlangan pol yuvish vositasi"),
        ("240510", "Viround Pet Friendly", "homeclean", "1000 ml", 40000, "Uy hayvonlari hidini yo'qotuvchi pol yuvish vositasi"),
        ("240152", "Viround liliya va gortenziya", "homeclean", "5200 ml", 110000, "Pol yuvish uchun konsentrlangan antibakterial vosita (katta hajm)"),
        ("240252", "VIRound Life planet", "homeclean", "5200 ml", 110000, "Bergamot va jasminli pol yuvish vositasi"),
        ("240352", "Viround Moonlight", "homeclean", "5200 ml", 120000, "Parfyumlangan konsentrlangan pol yuvish vositasi"),
        ("240552", "Viround Pet Friendly", "homeclean", "5200 ml", 120000, "Uy hayvonlari hidini yo'qotuvchi pol yuvish vositasi"),
        ("350605", "VIRlan PRO S6 Triqer", "homeclean", "500 ml", 100000, "Skotch, graffiti va saqich dog'larini ketkazuvchi professional vosita"),

        # Vanna va tualet uchun (bathroom)
        ("220105", "VIRsant kislotali vosita", "bathroom", "500 ml", 40000, "Tualet va vanna uchun zang va qatlam tozalovchi"),
        ("280105", "Viris To'xtat na'lot!", "bathroom", "500 ml", 35000, "Zang va qatlam tozalovchi"),
        ("220175", "VIRsant kislotali vosita", "bathroom", "750 ml", 45000, "Antibakterial tualet va vanna tozalovchi"),
        ("220275", "VIRsant Ultra", "bathroom", "750 ml", 42000, "Yuqori samarali kislotali tualet va vanna tozalovchi"),
        ("230175", "VIRet", "bathroom", "750 ml", 32000, "Antibakterial tualet va vanna tozalovchi vosita"),

        # Kir yuvish uchun (laundry)
        ("510112", "VIRIS gel Universal", "laundry", "1200 ml", 55000, "Oq va rangli kir yuvish uchun konsentrlangan gel, 35 yuvish"),
        ("520212", "VIRIS konditsioner Harmony", "laundry", "1200 ml", 50000, "Harmony konsentrlangan mato konditsioneri, 30 yuvish"),
        ("510312", "VIRis Color gel", "laundry", "1200 ml", 55000, "Rangli kirlar uchun konsentrlangan gel, 35 yuvish"),
        ("520312", "VIRis Greenly konditsioner", "laundry", "1200 ml", 50000, "Greenly konsentrlangan mato konditsioneri, 30 yuvish"),
        ("510712", "VIRis White gel", "laundry", "1200 ml", 55000, "Oq kirlar uchun konsentrlangan gel, 35 yuvish"),
        ("520712", "VIRis Wonder konditsioner", "laundry", "1200 ml", 50000, "Wonder konsentrlangan mato konditsioneri, 30 yuvish"),
        ("510812", "VIRis Delicate gel", "laundry", "1200 ml", 55000, "Nozik kirlar uchun konsentrlangan gel, 35 yuvish"),
        ("520812", "VIRis Amaze konditsioner", "laundry", "1200 ml", 50000, "Amaze konsentrlangan mato konditsioneri, 30 yuvish"),
        ("510512", "VIRis Black gel", "laundry", "1200 ml", 55000, "Qora kirlar uchun konsentrlangan gel, 35 yuvish"),
        ("520512", "VIRis Passion konditsioner", "laundry", "1200 ml", 50000, "Qora kirlar uchun mato konditsioneri, 30 yuvish"),
        ("510352", "VIRis Color gel", "laundry", "5200 ml", 140000, "Rangli kirlar uchun konsentrlangan gel, 150 yuvish"),
        ("520352", "VIRis Greenly konditsioner", "laundry", "5200 ml", 135000, "Greenly mato konditsioneri, 130 yuvish"),
        ("510152", "VIRIS gel Universal", "laundry", "5200 ml", 140000, "Oq va rangli kir yuvish geli, 150 yuvish"),
        ("520252", "VIRIS konditsioner Harmony", "laundry", "5200 ml", 135000, "Harmony mato konditsioneri, 130 yuvish")
    ]
    
    for art, name, cat, vol, price, desc in products_list:
        cursor.execute("SELECT id FROM products WHERE name = ? AND volume = ?", (name, vol))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO products (article, name, category, volume, price, description, media_type) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (art, name, cat, vol, price, desc, "")
            )
    conn.commit()

init_default_products()


logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
router = Router()


class AddProductState(StatesGroup):
    media = State()
    info = State()


class DeleteProductState(StatesGroup):
    product_id = State()


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
            [KeyboardButton(text="☕️ Кафе и рестораны"), KeyboardButton(text="✍️ Отзывы")],
            [KeyboardButton(text="ℹ️ О нас"), KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="🔄 Перезапуск (/start)"), KeyboardButton(text="🌐 Сменить язык")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Админ панель")])
    else:
        kb = [
            [KeyboardButton(text="🛍 Mahsulotlar"), KeyboardButton(text="🛒 Savatcha")],
            [KeyboardButton(text="☕️ Kafe va restoranlar"), KeyboardButton(text="✍️ Fikr va mulohaza")],
            [KeyboardButton(text="ℹ️ Biz haqimizda"), KeyboardButton(text="📞 Bog'lanish")],
            [KeyboardButton(text="🔄 Qayta boshlash (/start)"), KeyboardButton(text="🌐 Tilni o'zgartirish")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_menu(lang="uz"):
    if lang == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="❌ Очистить фото")],
                [KeyboardButton(text="📋 Список товаров"), KeyboardButton(text="🔙 Главное меню")],
            ],
            resize_keyboard=True,
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="❌ Rasmini tozalash")],
                [KeyboardButton(text="📋 Mahsulotlar ro'yxati"), KeyboardButton(text="🔙 Asosiy menyu")],
            ],
            resize_keyboard=True,
        )


@router.message(Command("start"))
@router.message(F.text.in_(["🔄 Qayta boshlash (/start)", "🔄 Перезапуск (/start)"]))
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
    text = "Siz o'zbek tilini tanladingiz! **VIRIDI Group** botiga xush kelibsiz:" if lang == "uz" else "Вы выбрали русский язык! Добро пожаловать:"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.answer("Kerakli bo'limni tanlang:" if lang == "uz" else "Выберите раздел:", reply_markup=main_menu(lang, is_admin))


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


# --- KAFE VA RESTORANLAR ---
@router.message(F.text.in_(["☕️ Kafe va restoranlar", "☕️ Кафе и рестораны"]))
async def cafe_restaurants(message: Message):
    lang = get_user_lang(message.from_user.id)
    text = "☕️ **Kafe, restoranlar va umumiy ovqatlanish shoxobchalari uchun:**\n\nViridi Group kafe, restoran va mehmonxonalar uchun ulgurji va chakana narxlarda professional tozalash va yuvish vositalarini taklif etadi.\n\n📞 Hamkorlik uchun telefon: +998937413339\n👤 Menejer: @um1daxon3339" if lang == "uz" else "☕️ **Для кафе и ресторанов:**\n\nПрофессиональные моющие средства оптом.\n\n📞 Контакты: +998937413339"
    await message.answer(text, parse_mode="Markdown")


@router.message(F.text.in_(["ℹ️ Biz haqimizda", "ℹ️ О нас"]))
async def about_us(message: Message):
    lang = get_user_lang(message.from_user.id)
    text = "🌿 **VIRIDI Group** — uy tozalash, kir yuvish, oshxona va vanna-tualet vositalarining ishonchli yetkazib beruvchisi.\n\n📞 Telefon: +998937413339" if lang == "uz" else "🌿 **VIRIDI Group** — надежный поставщик средств."
    await message.answer(text, parse_mode="Markdown")


@router.message(F.text.in_(["📞 Bog'lanish", "📞 Контакты"]))
async def contact_us(message: Message):
    lang = get_user_lang(message.from_user.id)
    text = "📞 Murojaat uchun:\n\n👤 Telegram: @um1daxon3339\n📱 Телефон: +998937413339" if lang == "uz" else "📞 Контакты:\n\n👤 Telegram: @um1daxon3339\n📱 Телефон: +998937413339"
    await message.answer(text)


# --- ADMIN PANEL ---
@router.message(F.text.in_(["⚙️ Admin Panel", "⚙️ Админ панель"]))
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        await message.answer("Admin panel:", reply_markup=admin_menu(lang))


@router.message(F.text.in_(["➕ Mahsulot qo'shish", "➕ Добавить товар"]))
async def add_product_start(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel)]], resize_keyboard=True)
        await message.answer("Iltimos, yangi mahsulot **rasmini** yuboring:" if lang == "uz" else "Пожалуйста, отправьте **фото** товара:", reply_markup=kb)
        await state.set_state(AddProductState.media)


@router.message(AddProductState.media, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(media_id=photo_id)
    lang = get_user_lang(message.from_user.id)
    await message.answer("Mahsulot ID raqamini yuboring:" if lang == "uz" else "Введите ID товара:")
    await state.set_state(AddProductState.info)


@router.message(AddProductState.info)
async def add_product_finish(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam (ID) kiriting:")
        return

    prod_id = int(message.text)
    data = await state.get_data()
    media_id = data.get("media_id")

    cursor.execute("SELECT name FROM products WHERE id = ?", (prod_id,))
    prod = cursor.fetchone()
    if not prod:
        await message.answer("Bunday ID raqamli mahsulot topilmadi!")
        return

    cursor.execute("UPDATE products SET media_id = ? WHERE id = ?", (media_id, prod_id))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ '{prod[0]}' uchun rasm muvaffaqiyatli qo'shildi!", reply_markup=admin_menu(lang))


# --- MAHSULOT RASMINI TOZALASH ---
@router.message(F.text.in_(["❌ Rasmini tozalash", "❌ Очистить фото"]))
async def start_delete_product(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, article, name, volume, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Mahsulotlar yo'q.")
            return
        text = "Rasmini o'chirmoqchi (tozalamoqchi) bo'lgan mahsulot **ID raqamini** yozing:\n\n"
        for p in products:
            art_str = f"[{p[1]}] " if p[1] else ""
            text += f"ID: {p[0]} | {art_str}{p[2]} ({p[3]}) — {int(p[4])} so'm\n"
        await message.answer(text, reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True), parse_mode="Markdown")
        await state.set_state(DeleteProductState.product_id)


@router.message(DeleteProductState.product_id)
async def process_delete_product(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu(get_user_lang(message.from_user.id)))
        return

    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam (ID) kiriting:")
        return

    prod_id = int(message.text)
    cursor.execute("SELECT id, name FROM products WHERE id = ?", (prod_id,))
    prod = cursor.fetchone()
    if not prod:
        await message.answer("Bunday ID raqamli mahsulot topilmadi:")
        return

    cursor.execute("UPDATE products SET media_id = '' WHERE id = ?", (prod_id,))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ '{prod[1]}' ning rasmi tozalandi (mahsulot bazada saqlanib qoldi)!", reply_markup=admin_menu(get_user_lang(message.from_user.id)))


# --- MAHSULOTLAR KATEGORIYALARI ---
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

    back_text = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
    if not products:
        await callback.message.edit_text("Bu kategoriyada mahsulot yo'q." if lang == "uz" else "В этой категории нет товаров.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="back_cats")]]))
        return

    kb = [[InlineKeyboardButton(text=f"{p[1]} — {int(p[2])} so'm", callback_data=f"prod_{p[0]}_1")] for p in products]
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
    await callback.message.edit_text("Kategoriyani tanlang:", reply_markup=kb)


# --- MAHSULOT TAFSILOTI ---
@router.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery):
    parts = callback.data.split("_")
    prod_id, qty = int(parts[1]), int(parts[2])

    cursor.execute("SELECT name, volume, price, description, media_id FROM products WHERE id = ?", (prod_id,))
    p = cursor.fetchone()

    if p:
        price_int = int(p[2])
        total_price = price_int * qty
        text = f"📦 **{p[0]}**\n💧 **Hajmi:** {p[1]}\n\n💰 Narxi: {price_int} so'm\n🔢 Miqdori: {qty} ta\n💵 Jami: {total_price} so'm\n\n📝 Tavsif: {p[3]}"
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
        if p[4] and p[4].strip():
            try:
                await callback.message.answer_photo(photo=p[4], caption=text, reply_markup=kb, parse_mode="Markdown")
                await callback.message.delete()
                return
            except Exception:
                pass
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "noop")
async def noop_cb(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("addcart_"))
async def add_to_cart(callback: CallbackQuery):
    parts = callback.data.split("_")
    cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = ?", (callback.from_user.id, int(parts[1]), int(parts[2]), int(parts[2])))
    conn.commit()
    await callback.answer("Savatchaga qo'shildi! 🛒", show_alert=True)


@router.message(F.text.in_(["🛒 Savatcha", "🛒 Корзина"]))
async def show_cart(message: Message):
    cursor.execute("SELECT p.name, c.quantity, p.price, c.product_id FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = ?", (message.from_user.id,))
    items = cursor.fetchall()
    if not items:
        await message.answer("Savatchangiz bo'sh. 🛒")
        return

    text = "🛒 **Sizning savatchangiz:**\n\n"
    grand_total = 0
    for name, qty, price, pid in items:
        summa = int(qty * price)
        grand_total += summa
        text += f"• {name} — {qty} x {int(price)} = {summa} so'm\n"
    text += f"\n💵 **Jami:** {grand_total} so'm"
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="start_checkout")],
            [InlineKeyboardButton(text="🗑 Tozalash", callback_data="clear_cart")],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    await callback.message.edit_text("Savatcha tozalandi.")


# --- MAHSULOTLAR RO'YXATI (FAQAT ADMIN UCHUN ARTIKUL BILAN) ---
@router.message(F.text.in_(["📋 Mahsulotlar ro'yxati", "📋 Список товаров"]))
async def show_products_list(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, article, name, volume, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Bazada mahsulotlar yo'q.")
            return
        
        text = "📋 **Barcha mahsulotlar ro'yxati (Artikullari bilan):**\n\n"
        for p in products:
            art_str = f"Artikul: {p[1]} | " if p[1] else ""
            text += f"ID: {p[0]} | {art_str}{p[2]} ({p[3]}) — {int(p[4])} so'm\n"
            
            if len(text) > 3500:
                await message.answer(text, parse_mode="Markdown")
                text = ""
        
        if text:
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
    print("Bot ishga tushdi va mahsulotlar joylashtirildi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
