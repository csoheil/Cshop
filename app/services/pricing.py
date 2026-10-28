from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Discount, Product

class PricingError(ValueError):
    pass

def validate_quantity(product: Product, quantity: int, min_stars: int = 50) -> int:
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise PricingError('تعداد باید عدد صحیح باشد.')
    if quantity < 1:
        raise PricingError('تعداد باید حداقل ۱ باشد.')
    if product.category.lower() in {'stars', 'telegram stars', 'استارز تلگرام', 'استارز'} and quantity < min_stars:
        raise PricingError(f'حداقل سفارش استارز {min_stars} عدد است.')
    return quantity

def calculate_total(product: Product, quantity: int) -> int:
    if product.price_toman < 0:
        raise PricingError('قیمت محصول معتبر نیست.')
    if product.pricing_type == 'per_unit':
        return product.price_toman * quantity
    return product.price_toman

async def apply_discount(session: AsyncSession, code: str | None, product: Product, subtotal: int) -> tuple[int, int | None]:
    if not code:
        return subtotal, None
    discount = await session.scalar(select(Discount).where(Discount.code == code.strip().upper(), Discount.is_active.is_(True)))
    now = datetime.now(timezone.utc)
    if not discount or (discount.expires_at and discount.expires_at <= now):
        raise PricingError('کد تخفیف معتبر یا فعال نیست.')
    if discount.product_id is not None and discount.product_id != product.id:
        raise PricingError('این کد برای محصول انتخابی نیست.')
    if subtotal < discount.min_spend:
        raise PricingError('مبلغ سفارش به حداقل استفاده از تخفیف نرسیده است.')
    if discount.percentage is not None:
        if not 0 <= discount.percentage <= 100:
            raise PricingError('درصد تخفیف نامعتبر است.')
        amount = subtotal * discount.percentage // 100
    else:
        amount = max(0, discount.fixed_amount or 0)
    amount = min(subtotal, amount)
    return subtotal - amount, discount.id
