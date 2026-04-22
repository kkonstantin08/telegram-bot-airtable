from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class AirtableFieldMapping:
    row_id: str
    title: str
    author: str
    technique: str
    size: str
    year: str
    price: str
    image: str
    expertise: str = "Экспертиза"
    framing: str = "Обрамление"
    provenance: str = "Провенанс/публикации/литература"


@dataclass(frozen=True)
class Settings:
    bot_token: str
    airtable_api_key: str
    airtable_base_id: str
    airtable_table_name: str
    fields: AirtableFieldMapping
    log_level: str = "INFO"
    request_timeout_seconds: float = 4.0
    telegram_request_timeout_seconds: float = 300.0
    author_pdf_chunk_size: int = 50
    pdf_font_path: str | None = None
    pdf_bold_font_path: str | None = None

    @classmethod
    def from_env(cls, validate_required: bool = True) -> "Settings":
        load_dotenv()

        settings = cls(
            bot_token=_env("BOT_TOKEN"),
            airtable_api_key=_env("AIRTABLE_API_KEY"),
            airtable_base_id=_env("AIRTABLE_BASE_ID"),
            airtable_table_name=_env("AIRTABLE_TABLE_NAME"),
            fields=AirtableFieldMapping(
                row_id=_env("AIRTABLE_ROW_ID_FIELD", "Row Number"),
                title=_env("AIRTABLE_TITLE_FIELD", "Title"),
                author=_env("AIRTABLE_AUTHOR_FIELD", "Author"),
                technique=_env("AIRTABLE_TECHNIQUE_FIELD", "Technique"),
                size=_env("AIRTABLE_SIZE_FIELD", "Size"),
                year=_env("AIRTABLE_YEAR_FIELD", "Year"),
                price=_env("AIRTABLE_PRICE_FIELD", "Price"),
                image=_env("AIRTABLE_IMAGE_FIELD", "Image"),
                expertise=_env("AIRTABLE_EXPERTISE_FIELD", "Экспертиза"),
                framing=_env("AIRTABLE_FRAMING_FIELD", "Обрамление"),
                provenance=_env(
                    "AIRTABLE_PROVENANCE_FIELD",
                    "Провенанс/публикации/литература",
                ),
            ),
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            request_timeout_seconds=float(_env("REQUEST_TIMEOUT_SECONDS", "4")),
            telegram_request_timeout_seconds=float(
                _env("TELEGRAM_REQUEST_TIMEOUT_SECONDS", "300")
            ),
            author_pdf_chunk_size=max(1, int(_env("AUTHOR_PDF_CHUNK_SIZE", "50"))),
            pdf_font_path=_optional_env("PDF_FONT_PATH"),
            pdf_bold_font_path=_optional_env("PDF_BOLD_FONT_PATH"),
        )

        if validate_required:
            missing = [
                name
                for name, value in {
                    "BOT_TOKEN": settings.bot_token,
                    "AIRTABLE_API_KEY": settings.airtable_api_key,
                    "AIRTABLE_BASE_ID": settings.airtable_base_id,
                    "AIRTABLE_TABLE_NAME": settings.airtable_table_name,
                }.items()
                if not value
            ]
            if missing:
                raise RuntimeError(
                    "Missing required environment variables: "
                    + ", ".join(missing)
                    + ". Copy .env.example to .env and fill real values."
                )

        return settings


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _optional_env(name: str) -> str | None:
    value = _env(name)
    return value or None
