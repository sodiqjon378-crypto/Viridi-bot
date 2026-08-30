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


# --- MAHSULOTLARNI KODNING O'ZIDAN KATEGORIYALarga BO'LIB BAZAGA YOZISH ---
def init_default_products():
    products_list = [
        # (Artikul, Nomi, Kategoriya, Hajmi, Narxi, Tavsif)
        ("140105", "VIRIS Olchali tort", "soap", "500 ml", 30000, "paxta urug'i yog'li gipoallergen suyuq krem-sovun 0+"),
        ("110110", "VIRida Ertaknamo Bali", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, kokos yog'i bilan"),
        ("110210", "VIRida Afrika xazinalari", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, argan yog'i bilan"),
        ("110310", "VIRida Islandiya buloqlari", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq sovun, 0+, gipoallergen, paxta urug'i yog'i bilan"),
        ("110410", "VIRida Fudzi afsonalari", "soap", "1000 ml", 45000, "4 xil gialuronli antibakterial suyuq krem-sovun, 0+, gipoallergen, paxta urug'i yog'i bilan")
    ]
    
    for art, name, cat, vol, price, desc in products_list:
        cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
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
                [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="❌ Удалить товар")],
                [KeyboardButton(text="📋 Список товаров"), KeyboardButton(text="🔙 Главное меню")],
            ],
            resize_keyboard=True,
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="❌ Mahsulotni o'chirish")],
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
    text = "📞 Murojaat uchun:\n\n👤 Telegram: @um1daxon3339\n📱 Telefon: +998937413339" if lang == "uz" else "📞 Контакты:\n\n👤 Telegram: @um1daxon3339\n📱 Телефон: +998937413339"
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
    await message.answer("Mahsulot ID raqamini yoki nomini yuboring:" if lang == "uz" else "Введите ID товара:")
    await state.set_state(AddProductState.info)


@router.message(AddProductState.info)
async def add_product_finish(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    if message.text in ["🔙 Bekor qilish", "🔙 Отмена"]:
        await back_to_main(message, state)
        return
    await state.clear()
    await message.answer("✅ Rasm qabul qilindi!", reply_markup=admin_menu(lang))


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

    kb = [[InlineKeyboardButton(text=f"{p[1]} — {p[2]} so'm", callback_data=f"prod_{p[0]}_1")] for p in products]
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
        summa = qty * price
        grand_total += summa
        text += f"• {name} — {qty} x {price} = {summa} so'm\n"
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


# --- MAHSULOTNI O'CHIRISH ---
@router.message(F.text.in_(["❌ Mahsulotni o'chirish", "❌ Удалить товар"]))
async def start_delete_product(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("O'chirish uchun mahsulotlar yo'q.")
            return
        text = "O'chirmoqchi bo'lgan mahsulot **ID raqamini** yozing:\n\n"
        for p in products:
            text += f"ID: {p[0]} | {p[1]} — {p[2]} so'm\n"
        await message.answer(text, reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True), parse_mode="Markdown")
        await state.set_state(DeleteProductState.product_id)


@router.message(DeleteProductState.product_id)
async def process_delete_product(message: Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
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

    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ '{prod[1]}' o'chirildi!", reply_markup=admin_menu(get_user_lang(message.from_user.id)))


@router.message(F.text.in_(["📋 Mahsulotlar ro'yxati", "📋 Список товаров"]))
async def show_products_list(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Bazada mahsulotlar yo'q.")
            return
        text = "📋 **Barcha mahsulotlar:**\n\n"
        for p in products:
            text += f"ID: {p[0]} | {p[1]} — {p[2]} so'm\n"
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
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
