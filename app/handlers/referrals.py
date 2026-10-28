from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from app.config import get_settings
from app.database import SessionFactory
from app.models import User, ReferralLedger
from app.keyboards.main import main_menu

router = Router()

@router.callback_query(F.data == 'referral')
async def referral(callback: CallbackQuery):
    settings = get_settings()
    async with SessionFactory() as s:
        user = await s.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        count = await s.scalar(select(func.count()).select_from(User).where(User.referred_by == user.id)) if user else 0
        rewards = await s.scalar(select(func.coalesce(func.sum(ReferralLedger.reward_amount), 0)).where(ReferralLedger.referrer_id == user.id)) if user else 0
    username = settings.bot_username.lstrip('@')
    link = f'https://t.me/{username}?start=ref_{user.referral_code}' if username and user else 'نام کاربری ربات در تنظیمات تعیین نشده است.'
    await callback.message.edit_text(f'🎟 <b>دعوت از دوستان</b>\nلینک اختصاصی شما:\n<code>{link}</code>\n\nدعوت‌های ثبت‌شده: {count}\nپاداش تبلیغاتی داخلی: {rewards} استارز CShop\n\nاین امتیاز داخلی است و دارایی یا موجودی کیف پول رسمی Telegram Stars نیست. پاداش پس از اولین سفارش پرداخت‌شده و تکمیل‌شده کاربر دعوت‌شده ثبت می‌شود.', reply_markup=main_menu(callback.from_user.id in settings.admin_ids))
    await callback.answer()
