from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import get_settings
from app.keyboards.main import main_menu

router = Router()

@router.callback_query(F.data == 'support')
async def support(callback: CallbackQuery):
    username = get_settings().support_username.lstrip('@')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='💬 ارتباط با پشتیبانی', url=f'https://t.me/{username}')],[InlineKeyboardButton(text='⬅️ منوی اصلی', callback_data='home')]])
    await callback.message.edit_text(f'🎧 پشتیبانی CShop\nآیدی پشتیبانی: @{username}\nبرای پیگیری سفارش، شماره سفارش را ارسال کنید.', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == 'discounts')
async def discounts(callback: CallbackQuery):
    await callback.message.edit_text('🎁 کد تخفیف را هنگام تماس با پشتیبانی دریافت کنید. در نسخه MVP تخفیف‌ها از دیتابیس اعتبارسنجی می‌شوند؛ اعمال کد در فرایند سفارش از سمت مشتری در حال تکمیل است.', reply_markup=main_menu(callback.from_user.id in get_settings().admin_ids))
    await callback.answer()
