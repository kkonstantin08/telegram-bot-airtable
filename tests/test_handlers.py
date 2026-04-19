from __future__ import annotations

from typing import Any

import pytest

from artbot.domain import Artwork, ArtworkRepository, LookupResult, LookupStatus
from artbot.handlers import process_user_text, send_help_message, send_start_message
from artbot.messages import (
    AUTHOR_NOT_FOUND_TEXT,
    AUTHOR_QUERY_TOO_SHORT_TEXT,
    DUPLICATE_TEXT,
    NOT_FOUND_TEXT,
    ROW_QUERY_ACCEPTED_TEXT,
)


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
    def __init__(
        self,
        row_result: LookupResult | None = None,
        author_results: list[Artwork] | None = None,
    ) -> None:
        self.row_result = row_result or LookupResult(status=LookupStatus.NOT_FOUND, matched_count=0)
        self.author_results = author_results or []
        self.row_queries: list[int] = []
        self.author_queries: list[str] = []

    def find_by_row_id(self, row_id: int) -> LookupResult:
        self.row_queries.append(row_id)
        return self.row_result

    def find_by_author_query(self, query: str) -> list[Artwork]:
        self.author_queries.append(query)
        return self.author_results


def fake_pdf_generator(*args: Any, **kwargs: Any) -> bytes:
    return b"%PDF-1.4\n%single\n"


def fake_artworks_pdf_generator(*args: Any, **kwargs: Any) -> bytes:
    return b"%PDF-1.4\nmulti\n"


@pytest.mark.asyncio
async def test_start_and_help_messages() -> None:
    start = FakeMessage()
    help_message = FakeMessage()

    await send_start_message(start)
    await send_help_message(help_message)

    assert "номер строки" in start.events[0]["text"]
    assert "фамилию автора" in start.events[0]["text"]
    assert "Поиск по автору" in help_message.events[0]["text"]


@pytest.mark.asyncio
async def test_existing_row_sends_photo_caption_with_price_and_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artwork = Artwork(
        row_id=1,
        title="Title",
        author="Author",
        price="100",
        image_url="https://example.com/a.jpg",
    )
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("1")
    monkeypatch.setattr("artbot.handlers._download_image_bytes", lambda *_args: b"image")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert repo.row_queries == [1]
    assert repo.author_queries == []
    assert [event["type"] for event in message.events] == ["text", "photo", "document"]
    assert message.events[0]["text"] == ROW_QUERY_ACCEPTED_TEXT
    assert "Цена: 100" in message.events[1]["caption"]
    assert message.events[2]["filename"] == "artwork_1.pdf"


@pytest.mark.asyncio
async def test_existing_row_without_image_sends_text_and_pdf() -> None:
    artwork = Artwork(row_id=2, title="Title", author="Author", image_url=None)
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("2")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert [event["type"] for event in message.events] == ["text", "text", "document"]
    assert message.events[0]["text"] == ROW_QUERY_ACCEPTED_TEXT
    assert "Изображение не указано" in message.events[1]["text"]


@pytest.mark.asyncio
async def test_partial_data_does_not_break_response() -> None:
    artwork = Artwork(row_id=3, title=None, author=None, image_url=None)
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("3")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert message.events[0]["text"] == ROW_QUERY_ACCEPTED_TEXT
    assert "не указано" in message.events[1]["text"]
    assert message.events[2]["filename"] == "artwork_3.pdf"


@pytest.mark.asyncio
async def test_not_found_message() -> None:
    repo = FakeRepository(LookupResult(status=LookupStatus.NOT_FOUND, matched_count=0))
    message = FakeMessage("999")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert message.events == [
        {"type": "text", "text": ROW_QUERY_ACCEPTED_TEXT},
        {"type": "text", "text": NOT_FOUND_TEXT},
    ]


@pytest.mark.asyncio
async def test_text_query_searches_by_author_and_sends_one_pdf() -> None:
    artworks = [
        Artwork(row_id=2, title="Second", author="Анна Иванова"),
        Artwork(row_id=1, title="First", author="Иванова Анна"),
    ]
    repo = FakeRepository(author_results=artworks)
    message = FakeMessage("Иванова")

    await process_user_text(
        message,
        repo,
        pdf_generator=fake_pdf_generator,
        artworks_pdf_generator=fake_artworks_pdf_generator,
    )

    assert repo.row_queries == []
    assert repo.author_queries == ["Иванова"]
    assert [event["type"] for event in message.events] == ["text", "document"]
    assert "Найдено работ: 2" in message.events[0]["text"]
    assert message.events[1]["filename"] == "artworks_Иванова.pdf"


@pytest.mark.asyncio
async def test_short_text_query_returns_hint() -> None:
    repo = FakeRepository()
    message = FakeMessage("a")

    await process_user_text(message, repo, artworks_pdf_generator=fake_artworks_pdf_generator)

    assert repo.row_queries == []
    assert repo.author_queries == []
    assert message.events == [{"type": "text", "text": AUTHOR_QUERY_TOO_SHORT_TEXT}]


@pytest.mark.asyncio
async def test_author_not_found_message() -> None:
    repo = FakeRepository(author_results=[])
    message = FakeMessage("Unknown")

    await process_user_text(message, repo, artworks_pdf_generator=fake_artworks_pdf_generator)

    assert repo.author_queries == ["Unknown"]
    assert message.events == [{"type": "text", "text": AUTHOR_NOT_FOUND_TEXT}]


@pytest.mark.asyncio
async def test_duplicate_row_id_is_data_error() -> None:
    repo = FakeRepository(LookupResult(status=LookupStatus.DUPLICATE, matched_count=2))
    message = FakeMessage("4")

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert message.events == [
        {"type": "text", "text": ROW_QUERY_ACCEPTED_TEXT},
        {"type": "text", "text": DUPLICATE_TEXT},
    ]
