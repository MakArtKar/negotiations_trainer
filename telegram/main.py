import os

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from dotenv import load_dotenv

load_dotenv()
TG_API_TOKEN = os.getenv("TG_API_TOKEN")
# SIMULATION_CORE_HOST = os.getenv('SIMULATION_CORE_HOST')
HTTP_TIMEOUT = 1200

bot = Bot(token=TG_API_TOKEN)
dp = Dispatcher()


@dp.message(Command(commands=["start", "help"]))
async def send_welcome(message: types.Message):
    await message.reply("TODO: add start/help message!")


@dp.message(Command("create_simulation"))
async def create_simulation(message: types.Message):
    await message.reply("TODO: add simulation creation")


@dp.message(Command("end_simulation"))
async def end_simulation(message: types.Message):
    await message.reply("TODO: add simulation ending")


@dp.message(Command("message_to_agent"))
async def message_to_agent(message: types.Message):
    await message.reply("TODO: add ability to send the message")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
