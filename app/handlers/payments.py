from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select
from app.config import get_settings
from app.database import SessionFactory
from app.models import Order, User, PaymentReceipt
from app.services.payments import review_receipt, PaymentTransitionError
from app.services.referrals import grant_referral_reward

router = Router()

def is_admin(uid: int) -> bool: return uid in get_settings().admin_ids

@router.message(F.photo | F.document)
async def receive_receipt(message: Message):
    if not message.caption:
        await message.answer('رسید را با کپشن شامل شماره سفارش، مانند #12، ارسال کنید.'); return
    import re
    match = re.search(r'#(\d+)', message.caption)
    if not match:
        await message.answer('شماره سفارش در کپشن پیدا نشد؛ مانند #12 بنویسید.'); return
    order_id = int(match.group(1)); file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    settings = get_settings()
    async with SessionFactory() as s:
        async with s.begin():
            order = await s.get(Order, order_id)
            user = await s.get(User, order.user_id) if order else None
            if not order or not user or user.telegram_id != message.from_user.id:
                await message.answer('سفارش پیدا نشد یا متعلق به شما نیست.'); return
            if order.payment_status != 'AWAITING_PAYMENT':
                await message.answer('این سفارش دیگر رسید جدید نمی‌پذیرد.'); return
            order.payment_status = 'UNDER_REVIEW'
            receipt = PaymentReceipt(order_id=order.id, file_id=file_id, status='UNDER_REVIEW'); s.add(receipt)
    admin_ids = settings.admin_ids
    if not admin_ids:
        await message.answer('رسید ثبت شد، اما مدیر در تنظیمات تعریف نشده است. پشتیبانی را مطلع کنید.')
    for admin_id in admin_ids:
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ تأیید پرداخت', callback_data=f'review:yes:{order_id}'), InlineKeyboardButton(text='❌ رد رسید', callback_data=f'review:no:{order_id}')]])
            if message.photo: await message.bot.send_photo(admin_id, file_id, caption=f'رسید سفارش #{order_id}\nکاربر: {message.from_user.id}\nمبلغ: {order.final_price:,} تومان', reply_markup=kb)
            else: await message.bot.send_document(admin_id, file_id, caption=f'رسید سفارش #{order_id}\nکاربر: {message.from_user.id}\nمبلغ: {order.final_price:,} تومان', reply_markup=kb)
        except Exception:
            import logging; logging.exception('Failed to notify admin %s', admin_id)
    await message.answer('رسید دریافت شد و برای بررسی ارسال شد. وضعیت سفارش پس از بررسی مدیر اعلام می‌شود.')

@router.callback_query(F.data.startswith('review:'))
async def review(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    _, decision, raw_id = callback.data.split(':'); order_id = int(raw_id); approve = decision == 'yes'
    async with SessionFactory() as s:
        async with s.begin():
            try: order = await review_receipt(s, order_id, callback.from_user.id, approve)
            except PaymentTransitionError as e:
                await callback.answer(str(e), show_alert=True); return
            user = await s.get(User, order.user_id); telegram_id = user.telegram_id if user else None
    if telegram_id:
        await callback.bot.send_message(telegram_id, f'وضعیت پرداخت سفارش #{order_id}: {"✅ تأیید شد" if approve else "❌ رسید رد شد"}. ' + ('برای پیگیری انجام سفارش منتظر پیام بعدی باشید.' if approve else 'در صورت نیاز با پشتیبانی تماس بگیرید.'))
    await callback.message.edit_caption(caption=(callback.message.caption or '') + f'\n\nبررسی‌شده توسط {callback.from_user.id}: {"تأیید" if approve else "رد"}')
    await callback.answer('ثبت شد.')
