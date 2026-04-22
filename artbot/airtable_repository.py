from __future__ import annotations

import logging
from typing import Any

from pyairtable import Api

from artbot.config import AirtableFieldMapping
from artbot.domain import Artwork, ArtworkRepository, LookupResult, LookupStatus

logger = logging.getLogger(__name__)


class AirtableArtworkRepository(ArtworkRepository):
    def __init__(
        self,
        api_key: str,
        base_id: str,
        table_name: str,
        fields: AirtableFieldMapping,
        request_timeout_seconds: float = 4.0,
    ) -> None:
        self.fields = fields
        timeout = (request_timeout_seconds, request_timeout_seconds)
        api = Api(api_key, timeout=timeout)
        self.table = api.table(base_id, table_name)

    def find_by_row_id(self, row_id: int) -> LookupResult:
        formula = f"{{{self.fields.row_id}}} = {row_id}"
        logger.info("Looking up Airtable record by %s=%s", self.fields.row_id, row_id)

        records = self.table.all(formula=formula, max_records=2)
        if not records:
            return LookupResult(status=LookupStatus.NOT_FOUND, matched_count=0)

        if len(records) > 1:
            logger.error(
                "Duplicate Airtable row ID detected: field=%s value=%s count_at_least=%s",
                self.fields.row_id,
                row_id,
                len(records),
            )
            return LookupResult(status=LookupStatus.DUPLICATE, matched_count=len(records))

        return LookupResult(
            status=LookupStatus.FOUND,
            artwork=_record_to_artwork(records[0], row_id, self.fields),
            matched_count=1,
        )

    def find_by_author_query(self, query: str) -> list[Artwork]:
        normalized_query = query.strip().lower()
        formula = (
            f'FIND("{_escape_formula_string(normalized_query)}", '
            f"LOWER({{{self.fields.author}}} & \"\")) > 0"
        )
        logger.info("Looking up Airtable records by author query=%s", normalized_query)

        records = self.table.all(formula=formula)
        artworks: list[Artwork] = []
        for record in records:
            row_id = _extract_row_id(record, self.fields)
            if row_id is None:
                logger.error(
                    "Skipping Airtable record with missing/invalid row ID: record_id=%s field=%s",
                    record.get("id"),
                    self.fields.row_id,
                )
                continue
            artworks.append(_record_to_artwork(record, row_id, self.fields))

        return sorted(artworks, key=lambda artwork: artwork.row_id)


def _record_to_artwork(
    record: dict[str, Any],
    row_id: int,
    fields: AirtableFieldMapping,
) -> Artwork:
    values = record.get("fields", {})
    image_urls = _extract_image_urls(values.get(fields.image))
    return Artwork(
        row_id=row_id,
        title=_to_text(values.get(fields.title)),
        author=_to_text(values.get(fields.author)),
        technique=_to_text(values.get(fields.technique)),
        size=_to_text(values.get(fields.size)),
        year=_to_text(values.get(fields.year)),
        price=_to_text(values.get(fields.price)),
        image_url=image_urls[0] if image_urls else None,
        image_urls=image_urls,
        expertise_image_urls=_extract_image_urls(values.get(fields.expertise)),
        framing_image_urls=_extract_image_urls(values.get(fields.framing)),
        provenance=_to_text(values.get(fields.provenance)),
        airtable_record_id=record.get("id"),
    )


def _extract_row_id(record: dict[str, Any], fields: AirtableFieldMapping) -> int | None:
    value = record.get("fields", {}).get(fields.row_id)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdecimal():
        return int(value.strip())
    return None


def _escape_formula_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        joined = ", ".join(str(item).strip() for item in value if str(item).strip())
        return joined or None
    return str(value).strip() or None


def _extract_image_url(value: Any) -> str | None:
    urls = _extract_image_urls(value)
    return urls[0] if urls else None


def _extract_image_urls(value: Any) -> tuple[str, ...]:
    if not value:
        return ()

    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()

    if isinstance(value, list):
        urls: list[str] = []
        for item in value:
            url = item.get("url") if isinstance(item, dict) else item
            if url:
                stripped = str(url).strip()
                if stripped:
                    urls.append(stripped)
        return tuple(urls)

    if isinstance(value, dict) and value.get("url"):
        stripped = str(value["url"]).strip()
        return (stripped,) if stripped else ()

    return ()
