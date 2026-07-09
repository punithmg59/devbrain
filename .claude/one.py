import asyncio
import os

from telegram import Bot
from telegram.error import TelegramError


async def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "6367786385")

    if not token:
        print("TELEGRAM_BOT_TOKEN is not set.")
        return

    bot = Bot(token=token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text="Trading Bot Online 🚀",
        )
        print("Message sent successfully.")
    except TelegramError as exc:
        print(f"Telegram send failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())