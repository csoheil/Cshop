import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from app.config import get_settings
from app.database import init_db, engine
from app.handlers.start import router as start_router
from app.handlers.products import router as products_router
from app.handlers.orders import router as orders_router
from app.handlers.payments import router as payments_router
from app.handlers.referrals import router as referrals_router
from app.handlers.support import router as support_router
from app.handlers.admin.panel import router as admin_router

async def main() -> None:
    settings = get_settings()
    if not settings.bot_token or 'replace_with_real_token' in settings.bot_token:
        raise RuntimeError('Set a valid BOT_TOKEN in .env before starting CShop.')
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    for router in (start_router, products_router, orders_router, payments_router, referrals_router, support_router, admin_router):
        dp.include_router(router)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except (TelegramAPIError, TelegramNetworkError):
        logging.exception('Telegram polling stopped after API/network error')
        raise
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
