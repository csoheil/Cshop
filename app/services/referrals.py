import secrets
import string
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Order, ReferralLedger, User

ALPHABET = string.ascii_uppercase + string.digits

def new_referral_code() -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(10))

async def ensure_user(session: AsyncSession, telegram_id: int, username: str | None, full_name: str, ref_code: str | None = None) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        if username is not None: user.username = username
        if full_name: user.full_name = full_name
        return user
    referrer = None
    if ref_code:
        candidate = await session.scalar(select(User).where(User.referral_code == ref_code))
        if candidate and candidate.telegram_id != telegram_id:
            referrer = candidate.id
    user = User(telegram_id=telegram_id, username=username, full_name=full_name,
                referral_code=new_referral_code(), referred_by=referrer, star_balance=0)
    session.add(user)
    await session.flush()
    return user

async def grant_referral_reward(session: AsyncSession, order: Order, reward_amount: int = 5) -> bool:
    """Grant once, only for a paid order that has completed fulfillment."""
    if order.payment_status != 'PAID' or order.fulfillment_status != 'COMPLETED':
        return False
    referee = await session.get(User, order.user_id)
    if not referee or not referee.referred_by or referee.referred_by == referee.id:
        return False
    already = await session.scalar(select(ReferralLedger.id).where(ReferralLedger.referee_id == referee.id).limit(1))
    if already:
        return False
    duplicate_order = await session.scalar(select(ReferralLedger.id).where(ReferralLedger.order_id == order.id))
    if duplicate_order:
        return False
    referrer = await session.get(User, referee.referred_by)
    if not referrer:
        return False
    referrer.star_balance += reward_amount
    session.add(ReferralLedger(referrer_id=referrer.id, referee_id=referee.id, order_id=order.id, reward_amount=reward_amount))
    return True
