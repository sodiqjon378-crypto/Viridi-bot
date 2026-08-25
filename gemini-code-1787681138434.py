import asyncio
import logging
import os
import sqlite3
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

conn = sqlite3.connect("viridi_bot_v2.db")
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    volume TEXT,
    price TEXT,
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
conn.commit()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
router = Router()


class AddProduct(StatesGroup):
    name = State()
    category = State()
    media = State()
    volume = State()
    price = State()
    description = State()


class DeleteProduct(StatesGroup):
    prod_id = State()


class DealerReg(StatesGroup):
    phone = State()


def main_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="🛍 Mahsulotlar"), KeyboardButton(text="ℹ️ Biz haqimizda")],
        [
            KeyboardButton(text="🤝 Dillerlar uchun"),
            KeyboardButton(text="📞 Bog'lanish"),
        ],
    ]
    if is_admin:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="❌ Mahsulotni o'chirish")],
            [KeyboardButton(text="📋 Mahsulotlar ro'yxati"), KeyboardButton(text="👥 Dillerlar arizalari")],
            [KeyboardButton(text="🔙 Asosiy menyu")],
        ],
        resize_keyboard=True,
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        "Assalomu alaykum! **VIRIDI Group** rasmiy Telegram botiga xush kelibsiz.\n"
        "Bu yerda uy tozalash va gigiena vositalarini chakana va ulgurji narxlarda xarid qilishingiz mumkin.",
        reply_markup=main_menu(is_admin),
        parse_mode="Markdown",
    )


@router.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer("Asosiy menyu:", reply_markup=main_menu(is_admin))


@router.message(F.text == "ℹ️ Biz haqimizda")
async def about_us(message: Message):
    await message.answer(
        "🌿 **VIRIDI Group** — uy tozalash, kir yuvish, oshxona va vanna-tualet gigiena vositalarining O'zbekistondagi ishonchli yetkazib beruvchisi.\n\n"
        "✨ **Bizning afzalliklarimiz:**\n"
        "• Yuqori sifatli va samarali tozalash mahsulotlari;\n"
        "• Uy bekalari va kafe-restoranlar uchun qulay tanlov;\n"
        "• Hovlilar, kafel, bruschatka va marmarlarni chuqur tozalash hamda oqartirish vositalari;\n"
        "• Chakana va ulgurji (dillerlik asosida) savdo tizimi;\n"
        "• Hamyonbop narxlar.\n\n"
        "📞 **Aloqa uchun telefon:** +998937413339\n"
        "👤 **Telegram menejer:** @um1daxon3339",
        parse_mode="Markdown",
    )


@router.message(F.text == "📞 Bog'lanish")
async def contact_us(message: Message):
    await message.answer(
        "📞 Murojaat uchun:\n\n"
        "👤 Telegram: @um1daxon3339\n"
        "📱 Telefon: +998937413339"
    )


@router.message(F.text == "🤝 Dillerlar uchun")
async def dealer_section(message: Message):
    cursor.execute("SELECT status FROM dealers WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()

    if res and res[0] == "approved":
        await message.answer("Siz allaqachon diller maqomidasiz! Ulgurji narxlar tez orada ochiladi.")
    elif res and res[0] == "pending":
        await message.answer("Sizning arizangiz ko'rib chiqilmoqda. Tez orada admin bog'lanadi.")
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
        )
        await message.answer(
            "Ulgurji narxlarni ko'rish va diller bo'lish uchun pastdagi tugmani bosing va raqamingizni yuboring:",
            reply_markup=kb,
        )


@router.message(F.content_type == "contact")
async def get_contact(message: Message, state: FSMContext):
    contact = message.contact
    cursor.execute(
        "INSERT OR REPLACE INTO dealers (user_id, full_name, phone, status) VALUES (?, ?, ?, ?)",
        (message.from_user.id, message.from_user.full_name, contact.phone_number, "pending"),
    )
    conn.commit()

    await message.answer("Raqamingiz qabul qilindi! Ariza adminga yuborildi.", reply_markup=main_menu())
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"👤 Yangi diller arizasi!\nIsm: {message.from_user.full_name}\nTel: {contact.phone_number}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="Tasdiqlash ✅", callback_data=f"approve_{message.from_user.id}")]]
                ),
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("approve_"))
async def approve_dealer(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    cursor.execute("UPDATE dealers SET status = 'approved' WHERE user_id = ?", (user_id,))
    conn.commit()
    await callback.message.edit_text("Diller tasdiqlandi ✅")
    await bot.send_message(user_id, "Tabriklaymiz! Sizning dillerlik arizangiz tasdiqlandi.")


@router.message(F.text == "🛍 Mahsulotlar")
async def show_categories(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍳 Oshxona degresrlari", callback_data="cat_degreaser")],
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
        await callback.message.edit_text("Bu kategoriyada hozircha mahsulot yo'q.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_cats")]]))
        return

    kb = []
    for p in products:
        kb.append([InlineKeyboardButton(text=f"{p[1]} — {p[2]} so'm", callback_data=f"prod_{p[0]}")])
    
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_cats")])
    await callback.message.edit_text("Mahsulotlar ro'yxati:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "back_cats")
async def back_to_cats(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍳 Oshxona degresrlari", callback_data="cat_degreaser")],
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
    prod_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name, volume, price, description, media_id, media_type FROM products WHERE id = ?", (prod_id,))
    p = cursor.fetchone()

    if p:
        text = f"📦 **{p[0]}**\n💧 **Hajmi:** {p[1]}\n\n💰 Narxi: {p[2]} so'm\n\n📝 Tavsif: {p[3]}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Buyurtma berish", callback_data=f"order_{prod_id}")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_cats")],
            ]
        )
        if p[4] and p[5] == "photo":
            await callback.message.answer_photo(photo=p[4], caption=text, reply_markup=kb, parse_mode="Markdown")
            await callback.message.delete()
        elif p[4] and p[5] == "video":
            await callback.message.answer_video(video=p[4], caption=text, reply_markup=kb, parse_mode="Markdown")
            await callback.message.delete()
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("order_"))
async def make_order(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name FROM products WHERE id = ?", (prod_id,))
    p = cursor.fetchone()
    
    await callback.answer("Buyurtmangiz qabul qilindi! Tez orada menejer aloqaga chiqadi.", show_alert=True)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🚨 Yangi buyurtma!\nFoydalanuvchi: @{callback.from_user.username or 'yoq'} ({callback.from_user.full_name})\nMahsulot: {p[0]}"
            )
        except Exception:
            pass


@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Admin panelga xush kelibsiz:", reply_markup=admin_menu())


@router.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Mahsulot nomini kiriting:")
        await state.set_state(AddProduct.name)


@router.message(AddProduct.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Oshxona", callback_data="setcat_degreaser")],
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
    await callback.message.answer("Endi mahsulot uchun **rasm yoki video** yuboring:")
    await state.set_state(AddProduct.media)


@router.message(AddProduct.media, F.photo)
async def process_photo_media(message: Message, state: FSMContext):
    media_id = message.photo[-1].file_id
    await state.update_data(media_id=media_id, media_type="photo")
    await message.answer("Mahsulot hajmini kiriting (masalan: **1L**, **5L** yoki **500ml**):", parse_mode="Markdown")
    await state.set_state(AddProduct.volume)


@router.message(AddProduct.media, F.video)
async def process_video_media(message: Message, state: FSMContext):
    media_id = message.video.file_id
    await state.update_data(media_id=media_id, media_type="video")
    await message.answer("Mahsulot hajmini kiriting (masalan: **1L**, **5L** yoki **500ml**):", parse_mode="Markdown")
    await state.set_state(AddProduct.volume)


@router.message(AddProduct.media)
async def process_media_invalid(message: Message):
    await message.answer("Iltimos, matn yozmang, faqat **rasm yoki video** yuboring:")


@router.message(AddProduct.volume)
async def process_volume(message: Message, state: FSMContext):
    await state.update_data(volume=message.text)
    await message.answer("Mahsulot narxini kiriting (masalan: 45000):")
    await state.set_state(AddProduct.price)


@router.message(AddProduct.price)
async def process_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Mahsulot haqida qisqacha tavsif yozing:")
    await state.set_state(AddProduct.description)


@router.message(AddProduct.description)
async def process_description(message: Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute(
        "INSERT INTO products (name, category, volume, price, description, media_id, media_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["name"], data["category"], data["volume"], data["price"], message.text, data["media_id"], data["media_type"]),
    )
    conn.commit()
    await state.clear()
    await message.answer("Mahsulot hajm va rasm/video bilan muvaffaqiyatli qo'shildi! ✅", reply_markup=admin_menu())


@router.message(F.text == "❌ Mahsulotni o'chirish")
async def start_delete_product(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("O'chirish uchun mahsulotlar yo'q.")
            return
        
        text = "❌ Qaysi mahsulotni o'chirmoqchisiz?\nIltimos, o'sha mahsulotning **ID raqamini** yozib yuboring (masalan: 1):\n\n"
        for p in products:
            text += f"ID: {p[0]} | {p[1]} — {p[2]} so'm\n"
        
        await message.answer(text, parse_mode="Markdown")
        await state.set_state(DeleteProduct.prod_id)


@router.message(DeleteProduct.prod_id)
async def process_delete_product(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        prod_id = message.text.strip()
        if not prod_id.isdigit():
            await message.answer("Iltimos, faqat raqam (ID) kiriting:")
            return
        
        cursor.execute("DELETE FROM products WHERE id = ?", (int(prod_id),))
        conn.commit()
        await state.clear()
        await message.answer(f"ID raqami {prod_id} bo'lgan mahsulot o'chirib yuborildi! 🗑", reply_markup=admin_menu())


@router.message(F.text == "📋 Mahsulotlar ro'yxati")
async def list_products_admin(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cursor.execute("SELECT id, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Hozircha mahsulotlar yo'q.")
            return
        
        text = "📋 **Mavjud mahsulotlar:**\n\n"
        for p in products:
            text += f"ID: {p[0]} | {p[1]} — {p[2]} so'm\n"
        await message.answer(text, parse_mode="Markdown")


async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())