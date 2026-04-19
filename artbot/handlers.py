from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from typing import Any

import requests
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, Message

from artbot.domain import ArtworkRepository, LookupStatus
from artbot.messages import (
    AIRTABLE_ERROR_TEXT,
    AUTHOR_NOT_FOUND_TEXT,
    AUTHOR_QUERY_TOO_SHORT_TEXT,
    DUPLICATE_TEXT,
    HELP_TEXT,
    IMAGE_ERROR_SUFFIX,
    NOT_A_NUMBER_TEXT,
    NOT_FOUND_TEXT,
    PDF_ERROR_TEXT,
    START_TEXT,
    format_artwork_caption,
    format_author_found_text,
)
from artbot.pdf_generator import generate_artwork_pdf, generate_artworks_pdf

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
async def text_handler(
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
    artworks_pdf_generator: PdfGenerator = generate_artworks_pdf,
) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer(AUTHOR_QUERY_TOO_SHORT_TEXT)
        return

    if not text.isdecimal():
        await _process_author_query(
            message,
            repository=repository,
            query=text,
            request_timeout_seconds=request_timeout_seconds,
            pdf_font_path=pdf_font_path,
            pdf_bold_font_path=pdf_bold_font_path,
            artworks_pdf_generator=artworks_pdf_generator,
        )
        return

    row_id = int(text)
    if row_id <= 0:
        await message.answer(NOT_A_NUMBER_TEXT)
        return

    await _process_row_id_query(
        message,
        repository=repository,
        row_id=row_id,
        request_timeout_seconds=request_timeout_seconds,
        pdf_font_path=pdf_font_path,
        pdf_bold_font_path=pdf_bold_font_path,
        pdf_generator=pdf_generator,
    )


async def _process_row_id_query(
    message: Any,
    repository: ArtworkRepository,
    row_id: int,
    request_timeout_seconds: float,
    pdf_font_path: str | None,
    pdf_bold_font_path: str | None,
    pdf_generator: PdfGenerator,
) -> None:
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
    await _send_card(message, artwork.image_url, caption, request_timeout_seconds)

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


async def _process_author_query(
    message: Any,
    repository: ArtworkRepository,
    query: str,
    request_timeout_seconds: float,
    pdf_font_path: str | None,
    pdf_bold_font_path: str | None,
    artworks_pdf_generator: PdfGenerator,
) -> None:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        await message.answer(AUTHOR_QUERY_TOO_SHORT_TEXT)
        return

    try:
        artworks = await asyncio.to_thread(repository.find_by_author_query, normalized_query)
    except Exception:
        logger.exception("Airtable author lookup failed for query=%s", normalized_query)
        await message.answer(AIRTABLE_ERROR_TEXT)
        return

    if not artworks:
        await message.answer(AUTHOR_NOT_FOUND_TEXT)
        return

    await message.answer(format_author_found_text(len(artworks)))

    try:
        pdf_bytes = await asyncio.to_thread(
            artworks_pdf_generator,
            artworks,
            request_timeout_seconds,
            pdf_font_path,
            pdf_bold_font_path,
        )
        document = BufferedInputFile(
            pdf_bytes,
            filename=f"artworks_{_safe_filename_part(normalized_query)}.pdf",
        )
        await message.answer_document(document=document, caption=f"PDF по автору: {normalized_query}")
    except Exception:
        logger.exception("Author PDF generation or sending failed for query=%s", normalized_query)
        await message.answer(PDF_ERROR_TEXT)


async def _send_card(
    message: Any,
    image_url: str | None,
    caption: str,
    request_timeout_seconds: float,
) -> None:
    if not image_url:
        await message.answer(caption + "\n\nИзображение не указано.")
        return

    try:
        image_bytes = await asyncio.to_thread(
            _download_image_bytes,
            image_url,
            request_timeout_seconds,
        )
        photo = BufferedInputFile(image_bytes, filename="artwork_image.jpg")
        await message.answer_photo(photo=photo, caption=caption)
    except TelegramAPIError:
        logger.exception("Telegram could not send image")
        await message.answer(caption + IMAGE_ERROR_SUFFIX)
    except Exception:
        logger.exception("Could not download image before sending it to Telegram")
        await message.answer(caption + IMAGE_ERROR_SUFFIX)


def _safe_filename_part(value: str) -> str:
    filename = re.sub(r"[^\w.-]+", "_", value.strip(), flags=re.UNICODE).strip("._")
    return filename[:80] or "author"


def _download_image_bytes(image_url: str, request_timeout_seconds: float) -> bytes:
    response = requests.get(
        image_url,
        timeout=request_timeout_seconds,
        headers={"User-Agent": "artbot/1.0"},
    )
    response.raise_for_status()
    return response.content
