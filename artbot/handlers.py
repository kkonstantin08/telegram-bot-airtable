from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, Message

from artbot.domain import ArtworkRepository, LookupStatus
from artbot.messages import (
    AIRTABLE_ERROR_TEXT,
    DUPLICATE_TEXT,
    HELP_TEXT,
    IMAGE_ERROR_SUFFIX,
    NOT_A_NUMBER_TEXT,
    NOT_FOUND_TEXT,
    PDF_ERROR_TEXT,
    START_TEXT,
    format_artwork_caption,
)
from artbot.pdf_generator import generate_artwork_pdf

logger = logging.getLogger(__name__)

PdfGenerator = Callable[..., bytes]

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await send_start_message(message)


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await send_help_message(message)


@router.message(F.text)
async def row_id_handler(
    message: Message,
    repository: ArtworkRepository,
    request_timeout_seconds: float,
    pdf_font_path: str | None = None,
    pdf_bold_font_path: str | None = None,
) -> None:
    await process_user_text(
        message,
        repository=repository,
        request_timeout_seconds=request_timeout_seconds,
        pdf_font_path=pdf_font_path,
        pdf_bold_font_path=pdf_bold_font_path,
    )


async def send_start_message(message: Any) -> None:
    await message.answer(START_TEXT)


async def send_help_message(message: Any) -> None:
    await message.answer(HELP_TEXT)


async def process_user_text(
    message: Any,
    repository: ArtworkRepository,
    request_timeout_seconds: float = 4.0,
    pdf_font_path: str | None = None,
    pdf_bold_font_path: str | None = None,
    pdf_generator: PdfGenerator = generate_artwork_pdf,
) -> None:
    text = (message.text or "").strip()
    if not text.isdecimal():
        await message.answer(NOT_A_NUMBER_TEXT)
        return

    row_id = int(text)
    if row_id <= 0:
        await message.answer(NOT_A_NUMBER_TEXT)
        return

    try:
        result = await asyncio.to_thread(repository.find_by_row_id, row_id)
    except Exception:
        logger.exception("Airtable lookup failed for row_id=%s", row_id)
        await message.answer(AIRTABLE_ERROR_TEXT)
        return

    if result.status == LookupStatus.NOT_FOUND:
        await message.answer(NOT_FOUND_TEXT)
        return

    if result.status == LookupStatus.DUPLICATE:
        logger.error("Duplicate row ID in Airtable: row_id=%s", row_id)
        await message.answer(DUPLICATE_TEXT)
        return

    if not result.artwork:
        logger.error("Repository returned FOUND without artwork: row_id=%s", row_id)
        await message.answer(AIRTABLE_ERROR_TEXT)
        return

    artwork = result.artwork
    caption = format_artwork_caption(artwork)
    await _send_card(message, artwork.image_url, caption)

    try:
        pdf_bytes = await asyncio.to_thread(
            pdf_generator,
            artwork,
            request_timeout_seconds,
            pdf_font_path,
            pdf_bold_font_path,
        )
        document = BufferedInputFile(pdf_bytes, filename=f"artwork_{artwork.row_id}.pdf")
        await message.answer_document(document=document, caption=f"PDF-карточка #{artwork.row_id}")
    except Exception:
        logger.exception("PDF generation or sending failed for row_id=%s", row_id)
        await message.answer(PDF_ERROR_TEXT)


async def _send_card(message: Any, image_url: str | None, caption: str) -> None:
    if not image_url:
        await message.answer(caption + "\n\nИзображение не указано.")
        return

    try:
        await message.answer_photo(photo=image_url, caption=caption)
    except TelegramAPIError:
        logger.exception("Telegram could not send image URL")
        await message.answer(caption + IMAGE_ERROR_SUFFIX)
