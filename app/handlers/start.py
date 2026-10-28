from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from app.config import get_settings
from app.database import SessionFactory
from app.keyboards.main import main_menu
from app.models import Product
from app.services.referrals import ensure_user

router = Router()

@router.message(CommandStart())
async def start(message: Message):
    args = (message.text or '').split(maxsplit=1)
    ref = args[1][4:] if len(args) > 1 and args[1].startswith('ref_') else None
    async with SessionFactory() as session:
        async with session.begin():
            user = await ensure_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name, ref)
    await message.answer(f'سلام {message.from_user.first_name}! 🌷\nبه فروشگاه CShop خوش آمدید.\n\nتمام قیمت‌ها به تومان است. خدمات وابسته به تأمین‌کننده پس از تأیید واقعی انجام سفارش تکمیل می‌شوند.', reply_markup=main_menu(message.from_user.id in get_settings().admin_ids))

@router.callback_query(F.data.in_({'home','about'}))
async def home_or_about(callback: CallbackQuery):
    if callback.data == 'about':
        await callback.message.edit_text('CShop؛ فروشگاه خدمات تلگرام. وضعیت پرداخت و انجام سفارش جداگانه پیگیری می‌شود.\n\nبرای خدمات وابسته به تأمین‌کنندگان ثالث، زمان و امکان تحویل تابع ارائه‌دهنده است.', reply_markup=main_menu(callback.from_user.id in get_settings().admin_ids))
    else:
        await callback.message.edit_text('به منوی اصلی CShop خوش آمدید 🌷', reply_markup=main_menu(callback.from_user.id in get_settings().admin_ids))
    await callback.answer()

@router.callback_query(F.data == 'prices')
async def prices(callback: CallbackQuery):
    async with SessionFactory() as session:
        products = (await session.scalars(select(Product).where(Product.is_active.is_(True), Product.is_deleted.is_(False)).order_by(Product.category, Product.id))).all()
    text = '💰 <b>فهرست قیمت‌ها</b>\n\n' + ('\n'.join(f'• {p.name}: {p.price_toman:,} تومان' + (' به‌ازای هر واحد' if p.pricing_type == 'per_unit' else '') for p in products) if products else 'فعلاً محصول فعالی ثبت نشده است.')
    await callback.message.edit_text(text, reply_markup=main_menu(callback.from_user.id in get_settings().admin_ids))
    await callback.answer()
