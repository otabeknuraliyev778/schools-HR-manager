import os
import asyncio
import logging
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import start, vacancy, application, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def start_health_server():
    """Render va boshqa bulutli xizmatlar uchun health check serveri"""
    port = os.getenv("PORT")
    if port:
        app = web.Application()
        async def handle_ping(request):
            return web.Response(text="OK - Oqdaryo 2-son IMI Bot is running!")
        app.router.add_get("/", handle_ping)
        app.router.add_get("/health", handle_ping)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(port))
        await site.start()
        logger.info(f"Bulutli platforma uchun Health check server ishga tushdi: port {port}")

async def main():
    if not BOT_TOKEN:
        logger.error(
            "XATOLIK: BOT_TOKEN aniqlanmadi! Iltimos, .env faylida BOT_TOKEN=sizning_tokeningiz ni kiriting."
        )
        print("\n" + "="*60)
        print("⚠️ DIQQAT: BOT_TOKEN ko'rsatilmagan!")
        print("Botni ishga tushirish uchun .env faylida bot tokeningizni kiriting.")
        print("Namuna: .env.example fayliga qarang.")
        print("="*60 + "\n")
        return

    # Ma'lumotlar bazasini initsializatsiya qilish
    logger.info("Ma'lumotlar bazasi initsializatsiya qilinmoqda...")
    await init_db()

    # Bulutli hosting (Render) uchun port mavjud bo'lsa serverni yoqish
    await start_health_server()

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ro'yxatdan o'tkazish
    dp.include_router(start.router)
    dp.include_router(vacancy.router)
    dp.include_router(application.router)
    dp.include_router(admin.router)

    logger.info("Maktab HR Menejeri yordamchi boti muvaffaqiyatli ishga tushdi!")
    
    # Eski xabarlarni tozalash (drop pending updates) va polling boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
