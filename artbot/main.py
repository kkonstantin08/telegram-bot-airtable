from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from artbot.airtable_repository import AirtableArtworkRepository
from artbot.config import Settings
from artbot.handlers import router


async def main() -> None:
    settings = Settings.from_env(validate_required=True)
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    repository = AirtableArtworkRepository(
        api_key=settings.airtable_api_key,
        base_id=settings.airtable_base_id,
        table_name=settings.airtable_table_name,
        fields=settings.fields,
        request_timeout_seconds=settings.request_timeout_seconds,
    )

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    logging.getLogger(__name__).info("Bot started")
    await dispatcher.start_polling(
        bot,
        repository=repository,
        request_timeout_seconds=settings.request_timeout_seconds,
        pdf_font_path=settings.pdf_font_path,
        pdf_bold_font_path=settings.pdf_bold_font_path,
    )


if __name__ == "__main__":
    asyncio.run(main())
