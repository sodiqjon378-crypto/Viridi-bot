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
    FSInputFile,
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

# Bazalarni yaratish (id sifatida article ishlatiladi)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
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
    product_id TEXT,
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


# --- 46 TA MAHSULOTNI ARTIKULI BILAN BAZAGA JOYlash ---
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

        # Uy tozalash va pol yuvish uchun (homeclean)
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
        cursor.execute("SELECT id FROM products WHERE id = ?", (art,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO products (id, name, category, volume, price, description, media_type) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (art, name, cat, vol, price, desc, "")
            )
    conn.commit()

init_default_products()


logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
router = Router()


# --- FSM STATE-LAR (Barcha bo'limlar uchun) ---
class AddProductState(StatesGroup):
    media = State()
    article = State()
    name = State()
    category = State()
    volume = State()
    price = State()
    description = State()


class EditProductState(StatesGroup):
    article = StateField = State()
    field = State()
    new_value = State()


class DeleteProductState(StatesGroup):
    article = State()


class DealerRegState(StatesGroup):
    full_name = State()
    phone = State()


class FeedbackState(StatesGroup):
    text = State()


def get_user_lang(user_id):
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else "uz"


def main_menu(lang="uz", is_admin=False):
    if lang == "ru":
        kb = [
            [KeyboardButton(text="🛍 Товары"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="☕️ Кафе и рестораны"), KeyboardButton(text="🤝 Стать дилером")],
            [KeyboardButton(text="✍️ Отзывы"), KeyboardButton(text="ℹ️ О нас")],
            [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="🔄 Перезапуск (/start)")],
            [KeyboardButton(text="🌐 Сменить язык")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Админ панель")])
    else:
        kb = [
            [KeyboardButton(text="🛍 Mahsulotlar"), KeyboardButton(text="🛒 Savatcha")],
            [KeyboardButton(text="☕️ Kafe va restoranlar"), KeyboardButton(text="🤝 Diler bo'lish")],
            [KeyboardButton(text="✍️ Fikr va mulohaza"), KeyboardButton(text="ℹ️ Biz haqimizda")],
            [KeyboardButton(text="📞 Bog'lanish"), KeyboardButton(text="🔄 Qayta boshlash (/start)")],
            [KeyboardButton(text="🌐 Tilni o'zgartirish")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# Skrinshotdagi aniq 6 ta tugma va Asosiy menyu bilan admin panel klaviaturasi
def admin_menu(lang="uz"):
    if lang == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="✏️ Редактировать товар")],
                [KeyboardButton(text="❌ Удалить товар"), KeyboardButton(text="📋 Список товаров")],
                [KeyboardButton(text="👥 Заявки дилеров"), KeyboardButton(text="📮 Просмотр отзывов")],
                [KeyboardButton(text="🔙 Главное меню")],
            ],
            resize_keyboard=True,
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="✏️ Mahsulotni tahrirlash")],
                [KeyboardButton(text="❌ Mahsulotni o'chirish"), KeyboardButton(text="📋 Mahsulotlar ro'yxati")],
                [KeyboardButton(text="👥 Dillerlar arizalari"), KeyboardButton(text="📮 Fikr-mulohazalarni ko'rish")],
                [KeyboardButton(text="🔙 Asosiy menyu")],
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


# --- DILER BO'LISH (Foydalanuvchi uchun) ---
@router.message(F.text.in_(["🤝 Diler bo'lish", "🤝 Стать дилером"]))
async def become_dealer(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel)]], resize_keyboard=True)
    await message.answer("Diler bo'lish uchun to'liq F.I.Sh. kiriting:" if lang == "uz" else "Введите ваше Ф.И.О.:", reply_markup=kb)
    await state.set_state(DealerRegState.full_name)


@router.message(DealerRegState.full_name)
async def dealer_fullname(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    await state.update_data(full_name=message.text)
    lang = get_user_lang(message.from_user.id)
    await message.answer("Telefon raqamingizni yuboring (masalan: +998901234567):" if lang == "uz" else "Введите номер телефона:")
    await state.set_state(DealerRegState.phone)


@router.message(DealerRegState.phone)
async def dealer_phone(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    data = await state.get_data()
    user_id = message.from_user.id
    full_name = data.get("full_name")
    phone = message.text

    cursor.execute("INSERT OR REPLACE INTO dealers (user_id, full_name, phone, status) VALUES (?, ?, ?, ?)", (user_id, full_name, phone, "pending"))
    conn.commit()
    await state.clear()
    
    lang = get_user_lang(user_id)
    await message.answer("✅ Arizangiz qabul qilindi! Tez orada menejerlarimiz siz bilan bog'lanishadi." if lang == "uz" else "✅ Заявка принята!", reply_markup=main_menu(lang, user_id in ADMIN_IDS))
    
    # Adinlarga xabar berish
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"🚨 **Yangi diler arizasi!**\n\n👤 F.I.Sh: {full_name}\n📞 Tel: {phone}\n🆔 ID: {user_id}", parse_mode="Markdown")
        except Exception:
            pass


# --- FIKR VA MULOHAZA ---
@router.message(F.text.in_(["✍️ Fikr va mulohaza", "✍️ Отзывы"]))
async def feedback_start(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel)]], resize_keyboard=True)
    await message.answer("Taklif, shikoyat yoki fikringizni yozib yuboring:" if lang == "uz" else "Напишите свой отзыв:", reply_markup=kb)
    await state.set_state(FeedbackState.text)


@router.message(FeedbackState.text)
async def feedback_finish(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    
    user_id = message.from_user.id
    text = message.text
    cursor.execute("INSERT INTO feedback (user_id, full_name, text) VALUES (?, ?, ?)", (user_id, message.from_user.full_name, text))
    conn.commit()
    await state.clear()
    
    lang = get_user_lang(user_id)
    await message.answer("Rahmat! Fikringiz adminga yuborildi. 📝" if lang == "uz" else "Спасибо!", reply_markup=main_menu(lang, user_id in ADMIN_IDS))
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📝 **Yangi fikr/mulohaza:**\n\nKimdan: {message.from_user.full_name}\nMatn: {text}", parse_mode="Markdown")
        except Exception:
            pass


# --- ADMIN PANEL ---
@router.message(F.text.in_(["⚙️ Admin Panel", "⚙️ Админ панель"]))
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        await message.answer("Admin panel:", reply_markup=admin_menu(lang))


# 1. Mahsulot qo'shish
@router.message(F.text.in_(["➕ Mahsulot qo'shish", "➕ Добавить товар"]))
async def add_product_start(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel)]], resize_keyboard=True)
        await message.answer("Yangi mahsulot **rasmini** yuboring (yoki rasm bo'lmasa skip deb yozing):" if lang == "uz" else "Отправьте фото товара:", reply_markup=kb)
        await state.set_state(AddProductState.media)


@router.message(AddProductState.media, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(media_id=photo_id)
    await message.answer("Mahsulot **Artikulini** (ID raqamini) kiriting:")
    await state.set_state(AddProductState.article)


@router.message(AddProductState.media)
async def add_product_no_photo(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    await state.update_data(media_id="")
    await message.answer("Mahsulot **Artikulini** (ID raqamini) kiriting:")
    await state.set_state(AddProductState.article)


@router.message(AddProductState.article)
async def add_product_article(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    await state.update_data(article=message.text.strip())
    await message.answer("Mahsulot **nomini** kiriting:")
    await state.set_state(AddProductState.name)


@router.message(AddProductState.name)
async def add_product_name(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    await state.update_data(name=message.text.strip())
    await message.answer("Kategoriyasini yozing (masalan: soap, degreaser, homeclean, bathroom, laundry):")
    await state.set_state(AddProductState.category)


@router.message(AddProductState.category)
async def add_product_category(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    await state.update_data(category=message.text.strip())
    await message.answer("Hajmini yozing (masalan: 500 ml, 1000 ml, 5200 ml):")
    await state.set_state(AddProductState.volume)


@router.message(AddProductState.volume)
async def add_product_volume(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    await state.update_data(volume=message.text.strip())
    await message.answer("Narxini kiriting (faqat raqam bilan, masalan: 45000):")
    await state.set_state(AddProductState.price)


@router.message(AddProductState.price)
async def add_product_price(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    try:
        price = float(message.text.strip())
        await state.update_data(price=price)
        await message.answer("Mahsulot haqida qisqacha tavsif yozing:")
        await state.set_state(AddProductState.description)
    except ValueError:
        await message.answer("Narx faqat raqamlardan iborat bo'lsin! Qaytadan kiriting:")


@router.message(AddProductState.description)
async def add_product_save(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    
    data = await state.get_data()
    artikul = data.get("article")
    name = data.get("name")
    category = data.get("category")
    volume = data.get("volume")
    price = data.get("price")
    desc = message.text.strip()
    media_id = data.get("media_id")

    cursor.execute(
        """
        INSERT OR REPLACE INTO products (id, name, category, volume, price, description, media_id, media_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (artikul, name, category, volume, price, desc, media_id, "")
    )
    conn.commit()
    await state.clear()
    
    lang = get_user_lang(message.from_user.id)
    await message.answer(f"✅ '{name}' muvaffaqiyatli qo'shildi! Artikul: {artikul}", reply_markup=admin_menu(lang))


# 2. Mahsulotni tahrirlash
@router.message(F.text.in_(["✏️ Mahsulotni tahrirlash", "✏️ Редактировать товар"]))
async def edit_product_start(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel)]], resize_keyboard=True)
        await message.answer("Tahrirlamoqchi bo'lgan mahsulot **Artikulini** kiriting:", reply_markup=kb)
        await state.set_state(EditProductState.article)


@router.message(EditProductState.article)
async def edit_product_get_artikul(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    
    artikul = message.text.strip()
    cursor.execute("SELECT id, name, price FROM products WHERE id = ?", (artikul,))
    prod = cursor.fetchone()
    if not prod:
        await message.answer("Bunday artikulli mahsulot topilmadi! Qaytadan to'g'ri artikul kiriting:")
        return

    await state.update_data(article=artikul)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Narxini o'zgartirish", callback_data="edit_price")],
            [InlineKeyboardButton(text="📝 Nomini o'zgartirish", callback_data="edit_name")],
            [InlineKeyboardButton(text="💧 Hajmini o'zgartirish", callback_data="edit_volume")],
        ]
    )
    await message.answer(f"Mahsulot topildi: **{prod[1]}** ({int(prod[2])} so'm)\nNimani o'zgartirmoqchisiz?", reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("edit_"))
async def edit_product_choice(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    await state.update_data(field=action)
    await callback.message.answer("Yangi qiymatni kiriting:")
    await state.set_state(EditProductState.new_value)
    await callback.answer()


@router.message(EditProductState.new_value)
async def edit_product_save(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    
    data = await state.get_data()
    artikul = data.get("article")
    field = data.get("field")
    new_val = message.text.strip()

    if field == "price":
        try:
            new_val = float(new_val)
            cursor.execute("UPDATE products SET price = ? WHERE id = ?", (new_val, artikul))
        except ValueError:
            await message.answer("Narx faqat raqam bo'lishi kerak!")
            return
    elif field == "name":
        cursor.execute("UPDATE products SET name = ? WHERE id = ?", (new_val, artikul))
    elif field == "volume":
        cursor.execute("UPDATE products SET volume = ? WHERE id = ?", (new_val, artikul))

    conn.commit()
    await state.clear()
    lang = get_user_lang(message.from_user.id)
    await message.answer("✅ Mahsulot muvaffaqiyatli tahrirlandi!", reply_markup=admin_menu(lang))


# 3. Mahsulotni o'chirish
@router.message(F.text.in_(["❌ Mahsulotni o'chirish", "❌ Удалить товар"]))
async def delete_product_start(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        lang = get_user_lang(message.from_user.id)
        cancel = "🔙 Bekor qilish" if lang == "uz" else "🔙 Отмена"
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cancel)]], resize_keyboard=True)
        await message.answer("O'chirmoqchi bo'lgan mahsulot **Artikulini** kiriting:", reply_markup=kb)
        await state.set_state(DeleteProductState.article)


@router.message(DeleteProductState.article)
async def delete_product_finish(message: Message, state: FSMContext):
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    
    artikul = message.text.strip()
    cursor.execute("SELECT name FROM products WHERE id = ?", (artikul,))
    prod = cursor.fetchone()
    if not prod:
        await message.answer("Bunday artikulli mahsulot topilmadi! Tekshirib qaytadan kiriting:")
        return

    cursor.execute("DELETE FROM products WHERE id = ?", (artikul,))
    conn.commit()
    await state.clear()
    lang = get_user_lang(message.from_user.id)
    await message.answer(f"✅ '{prod[0]}' bazadan butunlay o'chirildi!", reply_markup=admin_menu(lang))


# 4. Mahsulotlar ro'yxati (2 qismli: matnli artikul/nom yoki Excel fayl)
@router.message(F.text.in_(["📋 Mahsulotlar ro'yxati", "📋 Список товаров"]))
async def show_products_list_menu(message: Message):
    if message.from_user.id in ADMIN_IDS:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Faqat artikul va nomlari", callback_data="list_text")],
                [InlineKeyboardButton(text="📊 Excel faylni olish (.xlsx)", callback_data="list_excel")]
            ]
        )
        await message.answer("Mahsulotlar ro'yxatini qaysi shaklda ko'rmoqchisiz?", reply_markup=kb)


@router.callback_query(F.data == "list_text")
async def send_products_text(callback: CallbackQuery):
    if callback.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, name FROM products")
        products = cursor.fetchall()
        if not products:
            await callback.message.answer("Bazada mahsulotlar yo'q.")
            await callback.answer()
            return
        
        text = "📋 **Artikul va Mahsulot nomlari:**\n\n"
        for p in products:
            text += f"• `{p[0]}` — {p[1]}\n"
            if len(text) > 3500:
                await callback.message.answer(text, parse_mode="Markdown")
                text = ""
        if text:
            await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()


@router.callback_query(F.data == "list_excel")
async def send_products_excel(callback: CallbackQuery):
    if callback.from_user.id in ADMIN_IDS:
        import pandas as pd
        cursor.execute("SELECT id, name, category, volume, price, description FROM products")
        rows = cursor.fetchall()
        
        df = pd.DataFrame(rows, columns=["Артикул", "Название", "Категория", "Объем", "Цена", "Описание"])
        file_path = "Prais_Viridi.xlsx"
        df.to_excel(file_path, index=False)
        
        doc = FSInputFile(file_path)
        await callback.message.answer_document(doc, caption="📊 Joriy mahsulotlar Excel fayli")
        await callback.answer()


# 5. Dillerlar arizalari
@router.message(F.text.in_(["👥 Dillerlar arizalari", "👥 Заявки дилеров"]))
async def show_dealers_requests(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT user_id, full_name, phone, status FROM dealers WHERE status = 'pending'")
        dealers = cursor.fetchall()
        if not dealers:
            await message.answer("Hozircha yangi dilerlik arizalari yo'q.")
            return

        for d in dealers:
            text = f"👤 **Diler arizasi:**\n\nF.I.Sh: {d[1]}\n📞 Tel: {d[2]}\n🆔 ID: {d[0]}"
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"dealer_accept_{d[0]}"),
                        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"dealer_reject_{d[0]}")
                    ]
                ]
            )
            await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("dealer_"))
async def process_dealer_action(callback: CallbackQuery):
    if callback.from_user.id in ADMIN_IDS:
        parts = callback.data.split("_")
        action, dealer_id = parts[1], int(parts[2])

        if action == "accept":
            cursor.execute("UPDATE dealers SET status = 'accepted' WHERE user_id = ?", (dealer_id,))
            conn.commit()
            await callback.message.edit_text("✅ Diler tasdiqlandi!")
            try:
                await bot.send_message(dealer_id, "🎉 Tabriklaymiz! Sizning dilerlik arizangiz tasdiqlandi.")
            except Exception:
                pass
        else:
            cursor.execute("UPDATE dealers SET status = 'rejected' WHERE user_id = ?", (dealer_id,))
            conn.commit()
            await callback.message.edit_text("❌ Diler arizasi rad etildi.")
            try:
                await bot.send_message(dealer_id, "❌ Afsuski, dilerlik arizangiz rad etildi.")
            except Exception:
                pass
        await callback.answer()


# 6. Fikr-mulohazalarni ko'rish
@router.message(F.text.in_(["📮 Fikr-mulohazalarni ko'rish", "📮 Просмотр отзывов"]))
async def show_feedbacks(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT full_name, text FROM feedback ORDER BY id DESC LIMIT 10")
        feedbacks = cursor.fetchall()
        if not feedbacks:
            await message.answer("Hozircha fikr-mulohazalar yo'q.")
            return

        text = "📮 **So'nggi fikr va mulohazalar:**\n\n"
        for f in feedbacks:
            text += f"👤 {f[0]}:\n💬 {f[1]}\n-------------------\n"
        await message.answer(text, parse_mode="Markdown")


# --- MAHSULOTLAR KATEGORIYALARI (Foydalanuvchi uchun) ---
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


# --- MAHSULOT TAFSILOTI VA SAVATCHA ---
@router.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery):
    parts = callback.data.split("_")
    prod_id, qty = parts[1], int(parts[2])

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
    cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = ?", (callback.from_user.id, parts[1], int(parts[2]), int(parts[2])))
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
    print("Bot ishga tushdi va barcha 6 ta admin bo'limi to'liq tiklandi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
