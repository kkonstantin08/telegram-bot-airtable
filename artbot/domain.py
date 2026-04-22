from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Artwork:
    row_id: int
    title: str | None = None
    author: str | None = None
    technique: str | None = None
    size: str | None = None
    year: str | None = None
    price: str | None = None
    image_url: str | None = None
    image_urls: tuple[str, ...] = ()
    expertise_image_urls: tuple[str, ...] = ()
    framing_image_urls: tuple[str, ...] = ()
    provenance: str | None = None
    airtable_record_id: str | None = None


class LookupStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class LookupResult:
    status: LookupStatus
    artwork: Artwork | None = None
    matched_count: int = 0


class ArtworkRepository:
    def find_by_row_id(self, row_id: int) -> LookupResult:
        raise NotImplementedError

    def find_by_author_query(self, query: str) -> list[Artwork]:
        raise NotImplementedError
