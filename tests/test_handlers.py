from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from artbot.domain import Artwork, ArtworkRepository, LookupResult, LookupStatus
from artbot.handlers import InMemoryRequestGuard, process_user_text, send_help_message, send_start_message
from artbot.messages import (
    AIRTABLE_ERROR_TEXT,
    AUTHOR_NOT_FOUND_TEXT,
    AUTHOR_QUERY_TOO_SHORT_TEXT,
    DUPLICATE_TEXT,
    NOT_FOUND_TEXT,
    REQUEST_BUSY_TEXT,
    ROW_QUERY_ACCEPTED_TEXT,
)


class FakeMessage:
    def __init__(self, text: str | None = None, chat_id: int = 1) -> None:
        self.text = text
        self.chat = SimpleNamespace(id=chat_id)
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


class RaisingRepository(FakeRepository):
    def find_by_row_id(self, row_id: int) -> LookupResult:
        self.row_queries.append(row_id)
        raise RuntimeError("boom")

    def find_by_author_query(self, query: str) -> list[Artwork]:
        self.author_queries.append(query)
        raise RuntimeError("boom")


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
async def test_existing_row_uses_first_image_url_for_telegram_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloaded_urls: list[str] = []

    def fake_download(image_url: str, *_args: Any) -> bytes:
        downloaded_urls.append(image_url)
        return b"image"

    artwork = Artwork(
        row_id=10,
        title="Title",
        image_url="https://example.com/legacy.jpg",
        image_urls=(
            "https://example.com/first.jpg",
            "https://example.com/second.jpg",
        ),
    )
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("10")
    monkeypatch.setattr("artbot.handlers._download_image_bytes", fake_download)

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert downloaded_urls == ["https://example.com/first.jpg"]
    assert [event["type"] for event in message.events] == ["text", "photo", "document"]


@pytest.mark.asyncio
async def test_existing_row_preview_falls_back_to_legacy_image_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloaded_urls: list[str] = []

    def fake_download(image_url: str, *_args: Any) -> bytes:
        downloaded_urls.append(image_url)
        return b"image"

    artwork = Artwork(
        row_id=11,
        title="Title",
        image_url="https://example.com/legacy.jpg",
    )
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("11")
    monkeypatch.setattr("artbot.handlers._download_image_bytes", fake_download)

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator)

    assert downloaded_urls == ["https://example.com/legacy.jpg"]
    assert [event["type"] for event in message.events] == ["text", "photo", "document"]


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
async def test_text_query_splits_large_author_pdf_into_chunks() -> None:
    artworks = [Artwork(row_id=row_id, title=f"Artwork {row_id}", author="Author") for row_id in range(1, 6)]
    generated_chunks: list[list[int]] = []

    def chunked_pdf_generator(chunk: list[Artwork], *_args: Any, **_kwargs: Any) -> bytes:
        generated_chunks.append([artwork.row_id for artwork in chunk])
        return b"%PDF-1.4\nmulti\n"

    repo = FakeRepository(author_results=artworks)
    message = FakeMessage("Author")

    await process_user_text(
        message,
        repo,
        artworks_pdf_generator=chunked_pdf_generator,
        author_pdf_chunk_size=2,
    )

    assert generated_chunks == [[1, 2], [3, 4], [5]]
    assert [event["type"] for event in message.events] == ["text", "document", "document", "document"]
    assert message.events[1]["filename"] == "artworks_Author_1_of_3.pdf"
    assert message.events[2]["filename"] == "artworks_Author_2_of_3.pdf"
    assert message.events[3]["filename"] == "artworks_Author_3_of_3.pdf"
    assert "1/3" in message.events[1]["caption"]
    assert "2/3" in message.events[2]["caption"]
    assert "3/3" in message.events[3]["caption"]


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


@pytest.mark.asyncio
async def test_busy_same_chat_rejects_row_query_without_repository_call() -> None:
    guard = InMemoryRequestGuard()
    assert guard.try_acquire(10)
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=Artwork(row_id=1), matched_count=1))
    message = FakeMessage("1", chat_id=10)

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator, guard=guard)

    assert repo.row_queries == []
    assert repo.author_queries == []
    assert message.events == [{"type": "text", "text": REQUEST_BUSY_TEXT}]


@pytest.mark.asyncio
async def test_busy_same_chat_rejects_author_query_without_repository_call() -> None:
    guard = InMemoryRequestGuard()
    assert guard.try_acquire(10)
    repo = FakeRepository(author_results=[Artwork(row_id=1, author="Иванова")])
    message = FakeMessage("Иванова", chat_id=10)

    await process_user_text(message, repo, artworks_pdf_generator=fake_artworks_pdf_generator, guard=guard)

    assert repo.row_queries == []
    assert repo.author_queries == []
    assert message.events == [{"type": "text", "text": REQUEST_BUSY_TEXT}]


@pytest.mark.asyncio
async def test_busy_different_chat_does_not_block_row_query() -> None:
    guard = InMemoryRequestGuard()
    assert guard.try_acquire(10)
    artwork = Artwork(row_id=2, title="Other chat", image_url=None)
    repo = FakeRepository(LookupResult(status=LookupStatus.FOUND, artwork=artwork, matched_count=1))
    message = FakeMessage("2", chat_id=20)

    await process_user_text(message, repo, pdf_generator=fake_pdf_generator, guard=guard)

    assert repo.row_queries == [2]
    assert message.events[0]["text"] == ROW_QUERY_ACCEPTED_TEXT
    assert message.events[-1]["filename"] == "artwork_2.pdf"


@pytest.mark.asyncio
async def test_guard_releases_chat_after_success() -> None:
    guard = InMemoryRequestGuard()
    first_repo = FakeRepository(
        LookupResult(status=LookupStatus.FOUND, artwork=Artwork(row_id=1, image_url=None), matched_count=1)
    )
    second_repo = FakeRepository(
        LookupResult(status=LookupStatus.FOUND, artwork=Artwork(row_id=2, image_url=None), matched_count=1)
    )

    await process_user_text(FakeMessage("1", chat_id=30), first_repo, pdf_generator=fake_pdf_generator, guard=guard)
    await process_user_text(FakeMessage("2", chat_id=30), second_repo, pdf_generator=fake_pdf_generator, guard=guard)

    assert first_repo.row_queries == [1]
    assert second_repo.row_queries == [2]


@pytest.mark.asyncio
async def test_guard_releases_chat_after_row_lookup_error() -> None:
    guard = InMemoryRequestGuard()
    failing_repo = RaisingRepository()
    healthy_repo = FakeRepository(
        LookupResult(status=LookupStatus.FOUND, artwork=Artwork(row_id=2, image_url=None), matched_count=1)
    )
    first_message = FakeMessage("1", chat_id=40)
    second_message = FakeMessage("2", chat_id=40)

    await process_user_text(first_message, failing_repo, pdf_generator=fake_pdf_generator, guard=guard)
    await process_user_text(second_message, healthy_repo, pdf_generator=fake_pdf_generator, guard=guard)

    assert first_message.events == [
        {"type": "text", "text": ROW_QUERY_ACCEPTED_TEXT},
        {"type": "text", "text": AIRTABLE_ERROR_TEXT},
    ]
    assert healthy_repo.row_queries == [2]


@pytest.mark.asyncio
async def test_guard_releases_chat_after_author_lookup_error() -> None:
    guard = InMemoryRequestGuard()
    failing_repo = RaisingRepository()
    healthy_repo = FakeRepository(author_results=[Artwork(row_id=1, author="Иванова")])
    first_message = FakeMessage("Иванова", chat_id=50)
    second_message = FakeMessage("Иванова", chat_id=50)

    await process_user_text(
        first_message,
        failing_repo,
        artworks_pdf_generator=fake_artworks_pdf_generator,
        guard=guard,
    )
    await process_user_text(
        second_message,
        healthy_repo,
        artworks_pdf_generator=fake_artworks_pdf_generator,
        guard=guard,
    )

    assert first_message.events == [{"type": "text", "text": AIRTABLE_ERROR_TEXT}]
    assert healthy_repo.author_queries == ["Иванова"]
    assert second_message.events[-1]["filename"] == "artworks_Иванова.pdf"
