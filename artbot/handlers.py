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

from artbot.domain import Artwork, ArtworkRepository, LookupStatus
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
    REQUEST_BUSY_TEXT,
    ROW_QUERY_ACCEPTED_TEXT,
    START_TEXT,
    format_artwork_caption,
    format_author_found_text,
)
from artbot.pdf_generator import generate_artwork_pdf, generate_artworks_pdf

logger = logging.getLogger(__name__)

PdfGenerator = Callable[..., bytes]

router = Router()

AIRTABLE_PERMISSION_ERROR_TEXT = (
    "Airtable отклонил доступ к таблице. "
    "Проверьте права токена (PAT) на эту base/table и scope data.records:read."
)


class InMemoryRequestGuard:
    def __init__(self) -> None:
        self._active_chat_ids: set[int] = set()

    def try_acquire(self, chat_id: int) -> bool:
        if chat_id in self._active_chat_ids:
            return False
        self._active_chat_ids.add(chat_id)
        return True

    def release(self, chat_id: int) -> None:
        self._active_chat_ids.discard(chat_id)


request_guard = InMemoryRequestGuard()


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
    author_pdf_chunk_size: int = 50,
    pdf_font_path: str | None = None,
    pdf_bold_font_path: str | None = None,
) -> None:
    await process_user_text(
        message,
        repository=repository,
        request_timeout_seconds=request_timeout_seconds,
        author_pdf_chunk_size=author_pdf_chunk_size,
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
    author_pdf_chunk_size: int = 50,
    pdf_font_path: str | None = None,
    pdf_bold_font_path: str | None = None,
    pdf_generator: PdfGenerator = generate_artwork_pdf,
    artworks_pdf_generator: PdfGenerator = generate_artworks_pdf,
    guard: InMemoryRequestGuard | None = None,
) -> None:
    active_guard = guard or request_guard
    chat_id = _extract_chat_id(message)
    if chat_id is not None:
        if not active_guard.try_acquire(chat_id):
            await message.answer(REQUEST_BUSY_TEXT)
            return

        try:
            await _process_user_text_unlocked(
                message,
                repository=repository,
                request_timeout_seconds=request_timeout_seconds,
                author_pdf_chunk_size=author_pdf_chunk_size,
                pdf_font_path=pdf_font_path,
                pdf_bold_font_path=pdf_bold_font_path,
                pdf_generator=pdf_generator,
                artworks_pdf_generator=artworks_pdf_generator,
            )
        finally:
            active_guard.release(chat_id)
        return

    await _process_user_text_unlocked(
        message,
        repository=repository,
        request_timeout_seconds=request_timeout_seconds,
        author_pdf_chunk_size=author_pdf_chunk_size,
        pdf_font_path=pdf_font_path,
        pdf_bold_font_path=pdf_bold_font_path,
        pdf_generator=pdf_generator,
        artworks_pdf_generator=artworks_pdf_generator,
    )


async def _process_user_text_unlocked(
    message: Any,
    repository: ArtworkRepository,
    request_timeout_seconds: float,
    author_pdf_chunk_size: int,
    pdf_font_path: str | None,
    pdf_bold_font_path: str | None,
    pdf_generator: PdfGenerator,
    artworks_pdf_generator: PdfGenerator,
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
            author_pdf_chunk_size=author_pdf_chunk_size,
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
    await message.answer(ROW_QUERY_ACCEPTED_TEXT)

    try:
        result = await asyncio.to_thread(repository.find_by_row_id, row_id)
    except Exception as exc:
        if _is_airtable_permissions_error(exc):
            logger.exception(
                "Airtable access denied for row lookup: row_id=%s status=403 type=INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND",
                row_id,
            )
            await message.answer(AIRTABLE_PERMISSION_ERROR_TEXT)
            return
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
    await _send_card(message, _preview_image_url(artwork), caption, request_timeout_seconds)

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
    author_pdf_chunk_size: int,
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
    except Exception as exc:
        if _is_airtable_permissions_error(exc):
            logger.exception(
                "Airtable access denied for author lookup: query=%s status=403 type=INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND",
                normalized_query,
            )
            await message.answer(AIRTABLE_PERMISSION_ERROR_TEXT)
            return
        logger.exception("Airtable author lookup failed for query=%s", normalized_query)
        await message.answer(AIRTABLE_ERROR_TEXT)
        return

    if not artworks:
        await message.answer(AUTHOR_NOT_FOUND_TEXT)
        return

    await message.answer(format_author_found_text(len(artworks)))

    try:
        chunks = _chunked(artworks, max(1, author_pdf_chunk_size))
        total_chunks = len(chunks)
        for chunk_index, artwork_chunk in enumerate(chunks, start=1):
            pdf_bytes = await asyncio.to_thread(
                artworks_pdf_generator,
                artwork_chunk,
                request_timeout_seconds,
                pdf_font_path,
                pdf_bold_font_path,
            )
            filename_suffix = f"_{chunk_index}_of_{total_chunks}" if total_chunks > 1 else ""
            caption_suffix = f", часть {chunk_index}/{total_chunks}" if total_chunks > 1 else ""
            document = BufferedInputFile(
                pdf_bytes,
                filename=f"artworks_{_safe_filename_part(normalized_query)}{filename_suffix}.pdf",
            )
            await message.answer_document(
                document=document,
                caption=f"PDF по автору: {normalized_query}{caption_suffix}",
            )
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


def _chunked(items: list[Artwork], chunk_size: int) -> list[list[Artwork]]:
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def _preview_image_url(artwork: Artwork) -> str | None:
    for image_url in artwork.image_urls:
        if image_url:
            return image_url
    return artwork.image_url


def _extract_chat_id(message: Any) -> int | None:
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    return chat_id if isinstance(chat_id, int) else None


def _download_image_bytes(image_url: str, request_timeout_seconds: float) -> bytes:
    response = requests.get(
        image_url,
        timeout=request_timeout_seconds,
        headers={"User-Agent": "artbot/1.0"},
    )
    response.raise_for_status()
    return response.content


def _is_airtable_permissions_error(exc: Exception) -> bool:
    for current in _iter_exception_chain(exc):
        if not isinstance(current, requests.exceptions.HTTPError):
            continue
        response = current.response
        if response is None or response.status_code != 403:
            continue
        if _extract_airtable_error_type(response) == "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND":
            return True
    return False


def _iter_exception_chain(exc: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    visited: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in visited:
        chain.append(current)
        visited.add(id(current))
        current = current.__cause__ or current.__context__
    return chain


def _extract_airtable_error_type(response: requests.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    error_type = error.get("type")
    if isinstance(error_type, str):
        return error_type
    return None
