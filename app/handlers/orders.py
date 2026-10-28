from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from app.config import get_settings
from app.database import SessionFactory
from app.models import Product, User, Order
from app.services.pricing import validate_quantity, calculate_total, apply_discount, PricingError
from app.keyboards.main import main_menu

router = Router()

@router.callback_query(F.data.startswith('buy:'))
async def create_order(callback: CallbackQuery):
    try: _, p, q = callback.data.split(':'); product_id, quantity = int(p), int(q)
    except (ValueError, TypeError):
        await callback.answer('درخواست نامعتبر است.', show_alert=True); return
    async with SessionFactory() as session:
        async with session.begin():
            product = await session.get(Product, product_id)
            if not product or not product.is_active or product.is_deleted:
                await callback.answer('این محصول دیگر موجود نیست.', show_alert=True); return
            try:
                validate_quantity(product, quantity, get_settings().min_stars_quantity)
                total = calculate_total(product, quantity)
                total, discount_id = await apply_discount(session, None, product, total)
            except PricingError as e:
                await callback.answer(str(e), show_alert=True); return
            user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
            if not user:
                await callback.answer('ابتدا /start را بزنید.', show_alert=True); return
            order = Order(user_id=user.id, product_id=product.id, product_name=product.name, quantity=quantity,
                          original_price=calculate_total(product, quantity), discount_id=discount_id,
                          discount_amount=calculate_total(product, quantity)-total, final_price=total)
            session.add(order); await session.flush(); order_id = order.id
    settings = get_settings()
    card = ''.join(ch for ch in settings.payment_card_number if ch.isdigit())
    await callback.message.answer(f'🧾 <b>سفارش #{order_id}</b>\nمحصول: {product.name}\nتعداد: {quantity:,}\nمبلغ: <b>{total:,} تومان</b>\n\nکارت مقصد: <code>{card}</code>\nدارنده کارت: {settings.payment_cardholder or "طبق اطلاعات پشتیبانی"}\n\nپس از واریز، تصویر یا فایل رسید را با کپشن <code>#{order_id}</code> ارسال کنید. سفارش تا تأیید مدیر در انتظار پرداخت/بررسی است. هیچ تحویلی قبل از تأیید پرداخت و انجام واقعی اعلام نمی‌شود.')
    await callback.answer('سفارش ثبت شد.')

@router.callback_query(F.data == 'my_orders')
async def my_orders(callback: CallbackQuery):
    async with SessionFactory() as s:
        user = await s.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        orders = (await s.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(10))).all() if user else []
    text = '📦 <b>سفارش‌های شما</b>\n\n' + ('\n'.join(f'#{o.id} {o.product_name} — {o.final_price:,} تومان\nپرداخت: {o.payment_status} | انجام: {o.fulfillment_status}' for o in orders) if orders else 'هنوز سفارشی ندارید.')
    await callback.message.edit_text(text, reply_markup=main_menu(callback.from_user.id in get_settings().admin_ids)); await callback.answer()
