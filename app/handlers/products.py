from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from app.database import SessionFactory
from app.models import Product
from app.keyboards.main import back_menu, main_menu

router = Router()
class BuyFlow(StatesGroup):
    quantity = State()

@router.callback_query(F.data == 'products')
async def categories(callback: CallbackQuery):
    async with SessionFactory() as s:
        products = (await s.scalars(select(Product).where(Product.is_active.is_(True), Product.is_deleted.is_(False)).order_by(Product.category, Product.name))).all()
    if not products:
        await callback.message.edit_text('فعلاً محصول فعالی موجود نیست.', reply_markup=back_menu())
    else:
        categories = sorted({p.category for p in products})
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'📂 {c}', callback_data=f'cat:{c}') ] for c in categories] + [[InlineKeyboardButton(text='⬅️ منوی اصلی', callback_data='home')]])
        await callback.message.edit_text('🛍 دسته‌بندی محصولات را انتخاب کنید:', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith('cat:'))
async def list_products(callback: CallbackQuery):
    category = callback.data[4:]
    async with SessionFactory() as s:
        products = (await s.scalars(select(Product).where(Product.category == category, Product.is_active.is_(True), Product.is_deleted.is_(False)))).all()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'{p.name} — {p.price_toman:,} تومان', callback_data=f'product:{p.id}')] for p in products] + [[InlineKeyboardButton(text='⬅️ منوی اصلی', callback_data='home')]])
    await callback.message.edit_text('یک محصول را انتخاب کنید:', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith('product:'))
async def product_detail(callback: CallbackQuery, state: FSMContext):
    try: product_id = int(callback.data.split(':', 1)[1])
    except ValueError:
        await callback.answer('محصول نامعتبر است.', show_alert=True); return
    async with SessionFactory() as s: product = await s.get(Product, product_id)
    if not product or not product.is_active or product.is_deleted:
        await callback.answer('این محصول در دسترس نیست.', show_alert=True); return
    if product.pricing_type == 'per_unit':
        await state.update_data(product_id=product.id)
        await state.set_state(BuyFlow.quantity)
        await callback.message.answer(f'<b>{product.name}</b>\n{product.description}\nقیمت هر واحد: {product.price_toman:,} تومان\n\nتعداد را به‌صورت عدد صحیح وارد کنید.' + (' حداقل سفارش استارز ۵۰ عدد است.' if product.category.lower() in {'stars','telegram stars','استارز تلگرام','استارز'} else ''))
    else:
        await callback.message.answer(f'<b>{product.name}</b>\n{product.description}\nقیمت: {product.price_toman:,} تومان', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🧾 ثبت سفارش', callback_data=f'buy:{product.id}:1')],[InlineKeyboardButton(text='⬅️ منوی اصلی', callback_data='home')]]))
    await callback.answer()

@router.message(BuyFlow.quantity)
async def quantity_entered(message: Message, state: FSMContext):
    raw = (message.text or '').strip()
    if not raw.isascii() or not raw.isdigit():
        await message.answer('لطفاً تعداد را فقط با عدد صحیح وارد کنید.'); return
    qty = int(raw)
    data = await state.get_data()
    async with SessionFactory() as s: product = await s.get(Product, data.get('product_id'))
    if not product or not product.is_active or product.is_deleted:
        await state.clear(); await message.answer('این محصول دیگر در دسترس نیست.', reply_markup=back_menu()); return
    minimum = 50 if product.category.lower() in {'stars','telegram stars','استارز تلگرام','استارز'} else 1
    if qty < minimum or qty > 1_000_000:
        await message.answer(f'تعداد باید بین {minimum:,} و 1,000,000 باشد.'); return
    await state.clear()
    await message.answer(f'تعداد انتخابی: {qty:,}\nمبلغ برآوردی: {product.price_toman * qty:,} تومان\nمبلغ نهایی هنگام ثبت سفارش در سرور محاسبه می‌شود.', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🧾 ادامه خرید', callback_data=f'buy:{product.id}:{qty}')],[InlineKeyboardButton(text='⬅️ منوی اصلی', callback_data='home')]]))
