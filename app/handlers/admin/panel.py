from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from app.config import get_settings
from app.database import SessionFactory
from app.models import Product, Order, User, AdminAuditLog
from app.services.referrals import grant_referral_reward
from app.keyboards.main import main_menu

router = Router()
def allowed(uid: int) -> bool: return uid in get_settings().admin_ids

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 آمار', callback_data='admin:stats'), InlineKeyboardButton(text='🛍 محصولات', callback_data='admin:products')],
        [InlineKeyboardButton(text='🧾 رسیدهای در انتظار', callback_data='admin:receipts'), InlineKeyboardButton(text='📦 انجام سفارش‌ها', callback_data='admin:orders')],
        [InlineKeyboardButton(text='⬅️ منوی اصلی', callback_data='home')]])

@router.message(Command('admin'))
async def admin_command(message: Message):
    if not allowed(message.from_user.id):
        await message.answer('دسترسی غیرمجاز.'); return
    await message.answer('⚙️ پنل مدیریت CShop', reply_markup=admin_kb())

@router.callback_query(F.data == 'admin')
async def admin_menu(callback: CallbackQuery):
    if not allowed(callback.from_user.id): await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    await callback.message.edit_text('⚙️ پنل مدیریت CShop', reply_markup=admin_kb()); await callback.answer()

@router.callback_query(F.data == 'admin:stats')
async def stats(callback: CallbackQuery):
    if not allowed(callback.from_user.id): await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    async with SessionFactory() as s:
        users = await s.scalar(select(func.count()).select_from(User)) or 0
        revenue = await s.scalar(select(func.coalesce(func.sum(Order.final_price), 0)).where(Order.payment_status == 'PAID')) or 0
        active = await s.scalar(select(func.count()).select_from(Order).where(Order.fulfillment_status.in_(['PENDING','IN_PROGRESS']))) or 0
        completed = await s.scalar(select(func.count()).select_from(Order).where(Order.fulfillment_status == 'COMPLETED')) or 0
    await callback.message.edit_text(f'📊 آمار\nکاربران: {users}\nدرآمد سفارش‌های پرداخت‌شده: {revenue:,} تومان\nسفارش‌های فعال: {active}\nسفارش‌های تکمیل‌شده: {completed}', reply_markup=admin_kb()); await callback.answer()

@router.callback_query(F.data == 'admin:products')
async def product_admin(callback: CallbackQuery):
    if not allowed(callback.from_user.id): await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    async with SessionFactory() as s:
        products = (await s.scalars(select(Product).order_by(Product.id.desc()).limit(30))).all()
    rows = [[InlineKeyboardButton(text=f'{"🟢" if p.is_active and not p.is_deleted else "⚫"} #{p.id} {p.name}', callback_data=f'admin:toggle:{p.id}')] for p in products]
    rows += [[InlineKeyboardButton(text='➕ افزودن محصول', callback_data='admin:help_add')],[InlineKeyboardButton(text='⬅️ پنل', callback_data='admin')]]
    await callback.message.edit_text('محصولات (برای فعال/غیرفعال کردن روی محصول بزنید):', reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)); await callback.answer()

@router.callback_query(F.data.startswith('admin:toggle:'))
async def toggle_product(callback: CallbackQuery):
    if not allowed(callback.from_user.id): await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    pid = int(callback.data.rsplit(':', 1)[1])
    async with SessionFactory() as s:
        async with s.begin():
            product = await s.get(Product, pid)
            if not product: await callback.answer('محصول پیدا نشد.', show_alert=True); return
            product.is_active = not product.is_active
            s.add(AdminAuditLog(admin_id=callback.from_user.id, action='product_toggled', target_type='product', target_id=str(pid)))
    await callback.answer('وضعیت محصول تغییر کرد.')
    await product_admin(callback)

@router.callback_query(F.data == 'admin:help_add')
async def add_help(callback: CallbackQuery):
    if not allowed(callback.from_user.id): await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    await callback.message.answer('برای افزودن محصول از نسخه مدیریت CLI یا seed script استفاده کنید؛ فرم چندمرحله‌ای ایجاد/ویرایش محصول در این MVP پیاده‌سازی نشده است. هرگز اطلاعات قیمت یا سفارش را از callback کاربر قابل اعتماد فرض نکنید.')
    await callback.answer()

@router.callback_query(F.data == 'admin:receipts')
async def receipts(callback: CallbackQuery):
    if not allowed(callback.from_user.id): await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    async with SessionFactory() as s:
        orders = (await s.scalars(select(Order).where(Order.payment_status == 'UNDER_REVIEW').order_by(Order.id))).all()
    text = '🧾 سفارش‌های منتظر بررسی رسید:\n' + ('\n'.join(f'#{o.id} — {o.product_name} — {o.final_price:,} تومان' for o in orders) if orders else 'موردی نیست.')
    await callback.message.edit_text(text, reply_markup=admin_kb()); await callback.answer()


@router.message(F.text.startswith('/product'))
async def product_admin_command(message: Message):
    if not allowed(message.from_user.id):
        await message.answer('دسترسی غیرمجاز.'); return
    # /product add|name|category|price|fixed/per_unit|description
    # /product price|id|price ; /product delete|id ; /product edit|id|name|category|price|fixed/per_unit|description
    parts = (message.text or '').split('|')
    try:
        action = parts[0].split(maxsplit=1)[1].strip().lower()
        async with SessionFactory() as s:
            async with s.begin():
                if action == 'add' and len(parts) >= 6:
                    name, category, price, pricing_type = parts[1].strip(), parts[2].strip(), int(parts[3]), parts[4].strip()
                    description = '|'.join(parts[5:]).strip()
                    if price < 0 or pricing_type not in {'fixed','per_unit'} or not name or not category: raise ValueError
                    obj = Product(name=name, category=category, price_toman=price, pricing_type=pricing_type, description=description, is_active=True)
                    s.add(obj); await s.flush(); target = str(obj.id); audit_action = 'product_created'
                    response = f'محصول #{obj.id} ایجاد شد.'
                elif action == 'price' and len(parts) == 3:
                    obj = await s.get(Product, int(parts[1])); price = int(parts[2])
                    if not obj or price < 0: raise ValueError
                    obj.price_toman = price; target = str(obj.id); audit_action = 'product_price_updated'; response = 'قیمت به‌روزرسانی شد.'
                elif action == 'delete' and len(parts) == 2:
                    obj = await s.get(Product, int(parts[1]))
                    if not obj: raise ValueError
                    obj.is_deleted = True; obj.is_active = False; target = str(obj.id); audit_action = 'product_soft_deleted'; response = 'محصول به‌صورت نرم حذف شد.'
                elif action == 'edit' and len(parts) >= 7:
                    obj = await s.get(Product, int(parts[1])); price = int(parts[4]); pricing_type = parts[5].strip()
                    if not obj or price < 0 or pricing_type not in {'fixed','per_unit'}: raise ValueError
                    obj.name, obj.category, obj.price_toman, obj.pricing_type = parts[2].strip(), parts[3].strip(), price, pricing_type
                    obj.description = '|'.join(parts[6:]).strip(); target = str(obj.id); audit_action = 'product_updated'; response = 'محصول ویرایش شد.'
                else:
                    raise ValueError
                s.add(AdminAuditLog(admin_id=message.from_user.id, action=audit_action, target_type='product', target_id=target))
        await message.answer(response)
    except (ValueError, IndexError):
        await message.answer('قالب‌ها:\n/product add|نام|دسته|قیمت_تومان|fixed یا per_unit|توضیحات\n/product price|شناسه|قیمت_تومان\n/product edit|شناسه|نام|دسته|قیمت_تومان|fixed یا per_unit|توضیحات\n/product delete|شناسه')

@router.callback_query(F.data.startswith('admin:fulfill:'))
async def fulfillment_update(callback: CallbackQuery):
    if not allowed(callback.from_user.id):
        await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    try: _, _, raw_id, status = callback.data.split(':'); oid = int(raw_id)
    except ValueError:
        await callback.answer('درخواست نامعتبر.', show_alert=True); return
    if status not in {'IN_PROGRESS','COMPLETED','CANCELLED'}:
        await callback.answer('وضعیت نامعتبر.', show_alert=True); return
    async with SessionFactory() as s:
        async with s.begin():
            order = await s.get(Order, oid, with_for_update=True)
            if not order or order.payment_status != 'PAID':
                await callback.answer('ابتدا پرداخت باید تأیید شده باشد.', show_alert=True); return
            if order.fulfillment_status in {'COMPLETED','CANCELLED'}:
                await callback.answer('این سفارش نهایی شده است.', show_alert=True); return
            order.fulfillment_status = status
            s.add(AdminAuditLog(admin_id=callback.from_user.id, action='fulfillment_'+status.lower(), target_type='order', target_id=str(oid)))
            if status == 'COMPLETED':
                await grant_referral_reward(s, order, get_settings().referral_reward_stars)
            user = await s.get(User, order.user_id); customer_id = user.telegram_id if user else None
    if customer_id:
        await callback.bot.send_message(customer_id, f'وضعیت انجام سفارش #{oid} به {status} تغییر کرد.')
    await callback.answer('وضعیت انجام سفارش ثبت شد.')

@router.callback_query(F.data == 'admin:orders')
async def admin_orders(callback: CallbackQuery):
    if not allowed(callback.from_user.id): await callback.answer('دسترسی غیرمجاز.', show_alert=True); return
    async with SessionFactory() as s:
        orders = (await s.scalars(select(Order).where(Order.payment_status == 'PAID', Order.fulfillment_status.in_(['PENDING','IN_PROGRESS'])).order_by(Order.id))).all()
    rows = []
    for o in orders:
        rows.append([InlineKeyboardButton(text=f'#{o.id} {o.product_name}: شروع', callback_data=f'admin:fulfill:{o.id}:IN_PROGRESS'), InlineKeyboardButton(text='تکمیل', callback_data=f'admin:fulfill:{o.id}:COMPLETED')])
    rows.append([InlineKeyboardButton(text='⬅️ پنل', callback_data='admin')])
    await callback.message.edit_text('📦 سفارش‌های پرداخت‌شده و فعال:', reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)); await callback.answer()
