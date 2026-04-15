from __future__ import annotations

from artbot.domain import Artwork

MISSING_VALUE = "не указано"

START_TEXT = (
    "Здравствуйте. Я отправляю карточку объекта из Airtable.\n\n"
    "Пришлите номер строки / числовой ID записи, например: 12."
)

HELP_TEXT = (
    "Как пользоваться:\n"
    "1. Откройте Airtable и найдите стабильный числовой ID записи.\n"
    "2. Отправьте этот номер боту одним сообщением.\n"
    "3. Бот пришлет изображение, краткую карточку и PDF.\n\n"
    "Поиск работает только по числовому ID. Текстовые запросы не поддерживаются."
)

NOT_A_NUMBER_TEXT = "Пришлите, пожалуйста, только номер строки / числовой ID записи. Например: 12."
NOT_FOUND_TEXT = "Запись с таким номером не найдена. Проверьте номер строки в Airtable."
DUPLICATE_TEXT = (
    "В Airtable найдено несколько записей с таким номером. "
    "Это ошибка данных: проверьте поле стабильного row ID."
)
AIRTABLE_ERROR_TEXT = "Не получилось получить данные из Airtable. Попробуйте еще раз немного позже."
PDF_ERROR_TEXT = "Карточку отправил, но PDF сейчас сформировать не удалось. Ошибка уже записана в лог."
IMAGE_ERROR_SUFFIX = "\n\nИзображение не удалось отправить, но данные записи доступны."


def format_artwork_caption(artwork: Artwork) -> str:
    rows = [
        f"#{artwork.row_id}",
        f"Название: {_value(artwork.title)}",
        f"Автор: {_value(artwork.author)}",
        f"Техника: {_value(artwork.technique)}",
        f"Размер: {_value(artwork.size)}",
        f"Год: {_value(artwork.year)}",
        f"Цена: {_value(artwork.price)}",
    ]
    caption = "\n".join(rows)
    if len(caption) <= 950:
        return caption
    return caption[:947].rstrip() + "..."


def _value(value: str | None) -> str:
    return value if value else MISSING_VALUE
