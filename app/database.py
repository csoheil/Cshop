from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings
from app.models import Base

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Bootstrap a database-backed catalog once. Placeholder products are inactive until an
    # administrator configures real rates and activates them; no fabricated price is sold.
    from sqlalchemy import select
    from app.models import Product
    async with SessionFactory() as session:
        async with session.begin():
            exists = await session.scalar(select(Product.id).limit(1))
            if not exists:
                session.add_all([
                    Product(name='ری‌اکشن فیک تلگرام', category='ری‌اکشن', description='خدمت وابسته به ارائه‌دهنده؛ قبل از فعال‌سازی نرخ و تأمین‌کننده را بررسی کنید.', price_toman=0, pricing_type='per_unit', is_active=False),
                    Product(name='ویو تلگرام', category='ویو', description='خدمت وابسته به ارائه‌دهنده؛ تحویل پس از تأیید واقعی.', price_toman=0, pricing_type='per_unit', is_active=False),
                    Product(name='استارز تلگرام', category='استارز تلگرام', description='حداقل تعداد پیش‌فرض ۵۰؛ امکان تحویل به ارائه‌دهنده مجاز وابسته است.', price_toman=0, pricing_type='per_unit', is_active=False),
                    Product(name='تلگرام پرمیوم', category='پرمیوم', description='خرید/تحویل وابسته به قابلیت رسمی یا تأمین‌کننده مجاز.', price_toman=0, pricing_type='fixed', is_active=False),
                ])

async def get_session() -> AsyncSession:
    async with SessionFactory() as session:
        yield session
