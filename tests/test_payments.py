import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User, Product, Order, PaymentReceipt
from app.services.payments import review_receipt, PaymentTransitionError

@pytest.mark.asyncio
async def test_payment_state_machine_and_duplicate_review_guard():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with factory() as s:
        async with s.begin():
            u=User(telegram_id=1, referral_code='ABC', full_name='U'); p=Product(name='P',category='P',price_toman=100,pricing_type='fixed'); s.add_all([u,p]); await s.flush()
            o=Order(user_id=u.id,product_id=p.id,product_name='P',quantity=1,original_price=100,discount_amount=0,final_price=100,payment_status='UNDER_REVIEW'); s.add(o); await s.flush()
            s.add(PaymentReceipt(order_id=o.id,file_id='file',status='UNDER_REVIEW')); await s.flush(); oid=o.id
        async with s.begin():
            o=await review_receipt(s, oid, 99, True); assert o.payment_status == 'PAID'
        with pytest.raises(PaymentTransitionError):
            async with s.begin(): await review_receipt(s, oid, 99, False)
    await engine.dispose()
