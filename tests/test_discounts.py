from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, Product, Discount
from app.services.pricing import apply_discount, PricingError

@pytest.mark.asyncio
async def test_percentage_fixed_and_expired_discounts():
    engine=create_async_engine('sqlite+aiosqlite:///:memory:'); factory=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with factory() as s:
        async with s.begin():
            p=Product(name='P',category='x',price_toman=1000,pricing_type='fixed'); s.add(p); await s.flush()
            s.add_all([Discount(code='HALF',percentage=15,min_spend=500),Discount(code='FIX',fixed_amount=150),Discount(code='OLD',percentage=10,expires_at=datetime.now(timezone.utc)-timedelta(days=1))]); await s.flush()
            assert (await apply_discount(s,'half',p,999))[0] == 850
            assert (await apply_discount(s,'FIX',p,100))[0] == 0
            with pytest.raises(PricingError): await apply_discount(s,'OLD',p,1000)
    await engine.dispose()
