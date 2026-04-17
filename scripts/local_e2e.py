from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from artbot.handlers import process_user_text, send_help_message, send_start_message
from artbot.mock_repository import MemoryArtworkRepository, load_artworks_from_fixture
from artbot.pdf_generator import generate_artwork_pdf, generate_artworks_pdf

logging.getLogger("artbot.handlers").setLevel(logging.CRITICAL)


def local_pdf_generator(*args: Any, **kwargs: Any) -> bytes:
    artwork = replace(args[0], image_url=None)
    return generate_artwork_pdf(artwork)


def local_artworks_pdf_generator(*args: Any, **kwargs: Any) -> bytes:
    artworks = [replace(artwork, image_url=None) for artwork in args[0]]
    return generate_artworks_pdf(artworks)


class FakeMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.events: list[dict[str, Any]] = []

    async def answer(self, text: str, **kwargs: Any) -> None:
        self.events.append({"type": "text", "text": text, **kwargs})

    async def answer_photo(self, photo: str, caption: str | None = None, **kwargs: Any) -> None:
        self.events.append({"type": "photo", "photo": photo, "caption": caption, **kwargs})

    async def answer_document(self, document: Any, caption: str | None = None, **kwargs: Any) -> None:
        self.events.append(
            {
                "type": "document",
                "filename": getattr(document, "filename", None),
                "size": len(getattr(document, "data", b"")),
                "caption": caption,
                **kwargs,
            }
        )


async def main() -> None:
    fixtures_path = ROOT / "fixtures" / "sample_records.json"
    output_dir = ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    repository = MemoryArtworkRepository(load_artworks_from_fixture(fixtures_path))

    scenarios = [
        ("start", None),
        ("help", None),
        ("existing_with_image", "1"),
        ("existing_without_image", "2"),
        ("partial_data", "3"),
        ("duplicate_id", "4"),
        ("author_search", "Иванова"),
        ("author_not_found", "Сидоров"),
        ("short_author_query", "x"),
        ("not_found", "999"),
    ]

    for name, text in scenarios:
        message = FakeMessage(text)
        if name == "start":
            await send_start_message(message)
        elif name == "help":
            await send_help_message(message)
        else:
            await process_user_text(
                message,
                repository=repository,
                pdf_generator=local_pdf_generator,
                artworks_pdf_generator=local_artworks_pdf_generator,
            )
        print(f"\n[{name}]")
        for event in message.events:
            print(json.dumps(event, ensure_ascii=True))

    sample = repository.find_by_row_id(2).artwork
    if sample:
        pdf_bytes = generate_artwork_pdf(sample)
        pdf_path = output_dir / "sample_artwork_2.pdf"
        pdf_path.write_bytes(pdf_bytes)
        safe_path = str(pdf_path).encode("unicode_escape").decode("ascii")
        print(f"\nGenerated sample PDF: {safe_path} ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
