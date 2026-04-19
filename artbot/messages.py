from __future__ import annotations

from artbot.domain import Artwork

MISSING_VALUE = "не указано"

START_TEXT = (
    "Здравствуйте. Я отправляю карточки объектов из Airtable.\n\n"
    "Пришлите номер строки / числовой ID записи, например: 12.\n"
    "Или пришлите фамилию автора, например: Иванов."
)

HELP_TEXT = (
    "Как пользоваться:\n"
    "1. Отправьте номер строки / числовой ID, чтобы получить одну карточку.\n"
    "2. Отправьте фамилию или часть имени автора, чтобы получить общий PDF по найденным работам.\n\n"
    "Поиск по номеру идет по стабильному числовому полю Airtable. "
    "Поиск по автору идет по вхождению в поле автора."
)

NOT_A_NUMBER_TEXT = "Пришлите положительный номер строки или фамилию автора."
ROW_QUERY_ACCEPTED_TEXT = "Запрос принят. Ищу работу и готовлю карточку."
REQUEST_BUSY_TEXT = "Предыдущий запрос еще выполняется. Дождитесь ответа, затем отправьте новый запрос."
NOT_FOUND_TEXT = "Запись с таким номером не найдена. Проверьте артикул в Airtable."
DUPLICATE_TEXT = (
    "В Airtable найдено несколько записей с таким номером. "
    "Это ошибка данных: проверьте поле стабильного row ID."
)
AUTHOR_QUERY_TOO_SHORT_TEXT = "Для поиска по автору пришлите минимум 2 символа."
AUTHOR_NOT_FOUND_TEXT = "Работы по такому автору не найдены. Проверьте написание фамилии."
AIRTABLE_ERROR_TEXT = "Не получилось получить данные из Airtable. Попробуйте еще раз немного позже."
PDF_ERROR_TEXT = "Карточку отправил, но PDF сейчас сформировать не удалось. Ошибка уже записана в лог."
IMAGE_ERROR_SUFFIX = "\n\nИзображение не удалось отправить, но данные записи доступны."


def format_author_found_text(count: int) -> str:
    return f"Найдено работ: {count}. Формирую общий PDF."


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
