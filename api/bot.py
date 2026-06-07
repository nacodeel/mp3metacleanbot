import os
import tempfile
import requests

from fastapi import FastAPI, Request

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from mutagen.id3 import ID3

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()



# =========================
# Remove MP3 metadata
# =========================

def remove_mp3_metadata(file_path):
    try:
        audio = ID3(file_path)
        audio.delete()
        audio.save()
    except Exception:
        pass


# =========================
# /start
# =========================

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Отправь MP3 файл.\n\n"
        "Бот удалит все метаданные "
        "и отправит очищенный файл обратно."
    )


# =========================
# MP3 handler
# =========================

@dp.message(lambda message: message.document)
async def handle_mp3(message: types.Message):
    document = message.document

    if not document.file_name.lower().endswith(".mp3"):
        await message.answer(
            "Поддерживаются только MP3 файлы."
        )
        return

    file = await bot.get_file(document.file_id)

    file_url = (
        f"https://api.telegram.org/file/bot"
        f"{BOT_TOKEN}/{file.file_path}"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(
            tmpdir,
            document.file_name
        )

        response = requests.get(file_url)

        with open(input_path, "wb") as f:
            f.write(response.content)

        remove_mp3_metadata(input_path)

        cleaned_file = FSInputFile(input_path)

        await message.answer_document(
            document=cleaned_file,
            caption="Метаданные удалены."
        )


# =========================
# Webhook
# =========================

@app.post("/api/bot")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = types.Update.model_validate(data)

    await dp.feed_update(bot, update)

    return {"ok": True}