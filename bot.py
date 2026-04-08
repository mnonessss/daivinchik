import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
import aiohttp

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
API_URL = os.getenv("API_URL")
if not TOKEN or not API_URL:
    raise RuntimeError("TOKEN and API_URL must be set in environment or .env file")

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message):
    telegram_id = message.from_user.id
    welcome_text = "Добро пожаловать в Дайвинчик"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{API_URL}/users/register",
                json={"telegram_id": telegram_id},
            ) as resp:
                if resp.status >= 400:
                    await message.answer(
                        "Регистрация временно недоступна, попробуйте еще раз."
                    )
                    return
                payload = await resp.json(content_type=None)
        if payload.get("already_registered") is True:
            await message.answer("Вы уже зарегистрированы")
            return
        await message.answer(welcome_text)
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
        await message.answer(
            "Сервис регистрации не отвечает (таймаут). Попробуй еще раз через минуту."
        )
    except aiohttp.ClientError:
        await message.answer(
            "Не удалось связаться с API. Проверьте, что backend запущен."
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
