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
# Metadata utils
# =========================

def get_mp3_metadata(file_path):
    try:
        audio = ID3(file_path)

        metadata = {}

        for key in audio.keys():
            try:
                metadata[key] = str(audio.get(key))
            except Exception:
                metadata[key] = "unknown"

        return metadata

    except Exception:
        return {}


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
        "Бот:\n"
        "- покажет найденные метаданные\n"
        "- удалит их\n"
        "- проверит результат\n"
        "- отправит очищенный MP3 обратно"
    )


# =========================
# MP3 handler
# =========================
@dp.message(lambda message: message.audio)
async def handle_mp3(message: types.Message):

    audio = message.audio

    file_name = audio.file_name or "audio.mp3"

    if not file_name.lower().endswith(".mp3"):
        await message.answer(
            "Поддерживаются только MP3 файлы."
        )
        return

    status_message = await message.answer(
        "Скачиваю аудио..."
    )

    file = await bot.get_file(audio.file_id)

    file_url = (
        f"https://api.telegram.org/file/bot"
        f"{BOT_TOKEN}/{file.file_path}"
    )

    with tempfile.TemporaryDirectory() as tmpdir:

        input_path = os.path.join(
            tmpdir,
            file_name
        )

        response = requests.get(file_url)

        with open(input_path, "wb") as f:
            f.write(response.content)

        # =========================
        # Read metadata
        # =========================

        await status_message.edit_text(
            "Анализирую метаданные..."
        )

        metadata_before = get_mp3_metadata(input_path)

        if metadata_before:

            metadata_text = "\n".join([
                f"{k}: {v}"
                for k, v in metadata_before.items()
            ])

            if len(metadata_text) > 3500:
                metadata_text = metadata_text[:3500] + "\n..."

            await message.answer(
                "Найдены метаданные:\n\n"
                f"{metadata_text}"
            )

        else:
            await message.answer(
                "Метаданные не обнаружены."
            )

        # =========================
        # Remove metadata
        # =========================

        await status_message.edit_text(
            "Удаляю метаданные..."
        )

        remove_mp3_metadata(input_path)

        # =========================
        # Verify cleanup
        # =========================

        await status_message.edit_text(
            "Проверяю очистку..."
        )

        metadata_after = get_mp3_metadata(input_path)

        if metadata_after:

            verification_text = "\n".join([
                f"{k}: {v}"
                for k, v in metadata_after.items()
            ])

            if len(verification_text) > 3500:
                verification_text = (
                    verification_text[:3500] + "\n..."
                )

            await message.answer(
                "После очистки остались метаданные:\n\n"
                f"{verification_text}"
            )

        else:
            await message.answer(
                "Все метаданные успешно удалены."
            )

        # =========================
        # Send cleaned audio
        # =========================

        await status_message.edit_text(
            "Отправляю очищенный MP3..."
        )

        cleaned_audio = FSInputFile(input_path)

        await message.answer_audio(
            audio=cleaned_audio
        )

        await status_message.delete()


# =========================
# Webhook
# =========================

@app.post("/api/bot")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = types.Update.model_validate(data)

    await dp.feed_update(bot, update)

    return {"ok": True}