import json
import os

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
import httpx


load_dotenv()
TG_API_TOKEN = os.getenv("TG_API_TOKEN")
SIMULATION_CORE_HOST = os.getenv("SIMULATION_CORE_HOST", "http://localhost:8001")
HTTP_TIMEOUT = 1200

bot = Bot(token=TG_API_TOKEN)
dp = Dispatcher()


@dp.message(Command(commands=["start", "help"]))
async def send_welcome(message: types.Message):
    await message.reply("TODO: add start/help message!")


@dp.message(Command("create_simulation"))
async def create_simulation(message: types.Message):
    response = httpx.post(
        os.path.join(SIMULATION_CORE_HOST, "create_simulation"),
        timeout=HTTP_TIMEOUT,
        json={"id": str(message.chat.id)},
    )

    if response.status_code == 200:
        if response.text == "null":
            await bot.send_message(
                message.chat.id,
                "You already started negotiations. If you want to stop them - send /end_simulation",
            )
            return
        for text in json.loads(response.text):
            await bot.send_message(message.chat.id, text)
    else:
        await message.answer("Something went wrong...")


@dp.message(Command("end_simulation"))
async def end_simulation(message: types.Message):
    response = httpx.post(
        os.path.join(SIMULATION_CORE_HOST, "end_simulation"),
        timeout=HTTP_TIMEOUT,
        json={"id": str(message.chat.id)},
    )

    if response.status_code == 200:
        await bot.send_message(message.chat.id, "Negotiations are ended")
    else:
        await message.answer("Something went wrong...")


@dp.message()
async def message_to_agent(message: types.Message):
    response = httpx.post(
        os.path.join(SIMULATION_CORE_HOST, "get_text"),
        timeout=HTTP_TIMEOUT,
        json={"id": str(message.chat.id), "message": message.text},
    )

    if response.status_code == 200:
        if response.text == "null":
            await bot.send_message(
                message.chat.id,
                "These negotiations are ended, please, send /end_simulation",
            )
            return
        for text in json.loads(response.text):
            await bot.send_message(message.chat.id, text)
    else:
        await message.answer("Something went wrong...")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
