from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text='🛍 محصولات', callback_data='products'), InlineKeyboardButton(text='💰 قیمت‌ها', callback_data='prices')],
        [InlineKeyboardButton(text='🎁 دریافت تخفیف', callback_data='discounts'), InlineKeyboardButton(text='📦 سفارش‌های من', callback_data='my_orders')],
        [InlineKeyboardButton(text='🎟 دعوت از دوستان', callback_data='referral'), InlineKeyboardButton(text='🎧 پشتیبانی', callback_data='support')],
        [InlineKeyboardButton(text='ℹ️ درباره CShop', callback_data='about')],
    ]
    if is_admin: rows.append([InlineKeyboardButton(text='⚙️ پنل مدیریت', callback_data='admin')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ بازگشت به منوی اصلی', callback_data='home')]])
