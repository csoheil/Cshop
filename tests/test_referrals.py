import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User, Product, Order, ReferralLedger
from app.services.referrals import ensure_user, grant_referral_reward

@pytest.mark.asyncio
async def test_referral_integrity_and_one_time_reward():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with factory() as s:
        async with s.begin():
            referrer = await ensure_user(s, 1, 'ref', 'Referrer')
            code = referrer.referral_code
            self_user = await ensure_user(s, 1, 'ref', 'Referrer', code)
            assert self_user.id == referrer.id
            referee = await ensure_user(s, 2, 'new', 'New User', code)
            assert referee.referred_by == referrer.id
            p = Product(name='x', category='x', price_toman=100, pricing_type='fixed'); s.add(p); await s.flush()
            order = Order(user_id=referee.id, product_id=p.id, product_name='x', quantity=1, original_price=100, discount_amount=0, final_price=100, payment_status='PAID', fulfillment_status='COMPLETED'); s.add(order); await s.flush()
            assert await grant_referral_reward(s, order, 5) is True
            assert await grant_referral_reward(s, order, 5) is False
            assert referrer.star_balance == 5
            assert await s.scalar(__import__('sqlalchemy').select(ReferralLedger.id)) is not None
    await engine.dispose()
