from __future__ import annotations

from typing import Any

import pytest

from artbot.domain import Artwork, ArtworkRepository, LookupResult, LookupStatus
from artbot.handlers import process_user_text, send_help_message, send_start_message
from artbot.messages import DUPLICATE_TEXT, NOT_A_NUMBER_TEXT, NOT_FOUND_TEXT


class FakeMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.events: list[dict[str, Any]] = []

    async def answer(self, text: str, **kwargs: Any) -> None:
        self.events.append({"type": "text", "text": text, **kwargs})

    async def answer_photo(self, photo: str, caption: str | None = None, **kwargs: Any) -> None:
        self.events.append({"type": "photo", "photo": photo, "caption": caption, **kwargs})

    async def answer_document(self, document: Any, caption: str | None = None, **kwargs: Any) -> None:
        self.events.append({"type": "document", "filename": document.filename, "caption": caption, **kwargs})


class FakeRepository(ArtworkRepository):
    def __init__(self, result: LookupResult) -> None:
        self.result = result
        self.queries: list[int] = []

    def find_by_row_id(self, row_id: int) -> LookupResult:
        self.queries.append(row_id)
        return self.result


def fake_pdf_generator(*args: Any, **kwargs: Any) -> bytes:
    return b"%PDF-1.4\n%test\n"


@pytest.mark.asyncio
async def test_start_and_help_messages() -> None:
    start = FakeMessage()
    help_message = FakeMessage()

    await send_start_message(start)
    await send_help_message(help_message)

    assert "номер строки" in start.events[0]["text"]
    assert "Текстовые запросы не поддерживаются" in help_message.events[0]["text"]


@pytest.mark.asyncio
async def test_existing_row_sends_photo_and_pdf() -> None:
    artwork = Artwork(row_id=1, title="Title", author="Author", image_url="https://example.com/a.jpg")
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("1")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert repo.queries == [1]
    assert [event["type"] for event in message.events] == ["photo", "document"]
    assert message.events[0]["photo"] == "https://example.com/a.jpg"
    assert message.events[1]["filename"] == "artwork_1.pdf"


@pytest.mark.asyncio
async def test_existing_row_without_image_sends_text_and_pdf() -> None:
    artwork = Artwork(row_id=2, title="Title", author="Author", image_url=None)
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("2")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert [event["type"] for event in message.events] == ["text", "document"]
    assert "Изображение не указано" in message.events[0]["text"]


@pytest.mark.asyncio
async def test_partial_data_does_not_break_response() -> None:
    artwork = Artwork(row_id=3, title=None, author=None, image_url=None)
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("3")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert "не указано" in message.events[0]["text"]
    assert message.events[1]["filename"] == "artwork_3.pdf"


@pytest.mark.asyncio
async def test_not_found_message() -> None:
    repo = FakeRepository(LookupResult(status=LookupStatus.NOT_FOUND, matched_count=0))
    message = FakeMessage("999")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert message.events == [{"type": "text", "text": NOT_FOUND_TEXT}]


@pytest.mark.asyncio
async def test_not_number_message_and_no_lookup() -> None:
    repo = FakeRepository(LookupResult(status=LookupStatus.NOT_FOUND, matched_count=0))
    message = FakeMessage("not a number")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert repo.queries == []
    assert message.events == [{"type": "text", "text": NOT_A_NUMBER_TEXT}]


@pytest.mark.asyncio
async def test_duplicate_row_id_is_data_error() -> None:
    repo = FakeRepository(LookupResult(status=LookupStatus.DUPLICATE, matched_count=2))
    message = FakeMessage("4")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert message.events == [{"type": "text", "text": DUPLICATE_TEXT}]
