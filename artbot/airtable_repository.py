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


def _record_to_artwork(
    record: dict[str, Any],
    row_id: int,
    fields: AirtableFieldMapping,
) -> Artwork:
    values = record.get("fields", {})
    return Artwork(
        row_id=row_id,
        title=_to_text(values.get(fields.title)),
        author=_to_text(values.get(fields.author)),
        technique=_to_text(values.get(fields.technique)),
        size=_to_text(values.get(fields.size)),
        year=_to_text(values.get(fields.year)),
        price=_to_text(values.get(fields.price)),
        image_url=_extract_image_url(values.get(fields.image)),
        airtable_record_id=record.get("id"),
    )


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
    if not value:
        return None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("url"):
                return str(item["url"]).strip()
        return None

    if isinstance(value, dict) and value.get("url"):
        return str(value["url"]).strip()

    return None
