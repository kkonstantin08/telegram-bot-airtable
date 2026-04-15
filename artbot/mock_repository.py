from __future__ import annotations

import json
from pathlib import Path

from artbot.domain import Artwork, ArtworkRepository, LookupResult, LookupStatus


class MemoryArtworkRepository(ArtworkRepository):
    def __init__(self, artworks: list[Artwork]) -> None:
        self.artworks = artworks

    def find_by_row_id(self, row_id: int) -> LookupResult:
        matches = [artwork for artwork in self.artworks if artwork.row_id == row_id]
        if not matches:
            return LookupResult(status=LookupStatus.NOT_FOUND, matched_count=0)
        if len(matches) > 1:
            return LookupResult(status=LookupStatus.DUPLICATE, matched_count=len(matches))
        return LookupResult(status=LookupStatus.FOUND, artwork=matches[0], matched_count=1)


def load_artworks_from_fixture(path: str | Path) -> list[Artwork]:
    raw_items = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Artwork(
            row_id=int(item["row_id"]),
            title=item.get("title"),
            author=item.get("author"),
            technique=item.get("technique"),
            size=item.get("size"),
            year=item.get("year"),
            price=item.get("price"),
            image_url=item.get("image_url"),
            airtable_record_id=item.get("airtable_record_id"),
        )
        for item in raw_items
    ]
