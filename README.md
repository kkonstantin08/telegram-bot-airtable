# Telegram Bot Airtable Art Cards

Telegram-бот для коллекции современного искусства. Пользователь отправляет номер строки / стабильный числовой ID записи или фамилию автора. Бот получает данные из Airtable, отправляет карточку объекта в Telegram и формирует PDF A4.

## Что делает проект

- Команда `/start` кратко объясняет сценарий.
- Команда `/help` показывает инструкцию.
- Сценарий по номеру: пользователь отправляет число, например `12`.
- Бот ищет запись в Airtable строго по числовому полю, заданному в `AIRTABLE_ROW_ID_FIELD`.
- Если запись найдена по номеру, бот отправляет изображение с подписью или текстовую карточку без изображения, затем PDF-карточку A4.
- Сценарий по автору: пользователь отправляет фамилию или часть имени автора, бот отправляет один общий PDF по всем найденным работам.
- Цена остается в Telegram-сообщении, но не выводится в PDF.
- Если записей с одним row ID несколько, бот не выбирает одну автоматически и сообщает об ошибке данных.

В проекте намеренно нет поиска по названию, fuzzy search, inline keyboard и списка вариантов.

## Стек

- Python 3.12
- aiogram 3 для Telegram Bot API
- pyairtable для Airtable API
- reportlab для устойчивой прямой генерации PDF
- pytest для локальных проверок
- Docker / Docker Compose для серверного запуска

Выбор сделан в пользу простого локального запуска, малого количества сервисов и прямолинейной поддержки.

## Структура

```text
artbot/
  airtable_repository.py  # доступ к Airtable и строгий lookup по row ID
  config.py               # .env и маппинг полей Airtable
  domain.py               # модели Artwork и LookupResult
  handlers.py             # Telegram handlers и пользовательская логика
  main.py                 # entrypoint бота
  messages.py             # тексты ответов
  mock_repository.py      # локальный mock для e2e без токенов
  pdf_generator.py        # PDF A4
fixtures/
  sample_records.json     # mock-данные для локального e2e
scripts/
  check.ps1               # compile + tests + local e2e
  local_e2e.py            # локальная проверка ключевых сценариев
tests/
  test_*.py
```

## Установка

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Настройка `.env`

Скопируйте пример:

```powershell
Copy-Item .env.example .env
```

Заполните реальные значения:

```env
BOT_TOKEN=1234567890:real_telegram_token
AIRTABLE_API_KEY=pat_real_airtable_token
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Objects
AIRTABLE_ROW_ID_FIELD=Row Number

AIRTABLE_TITLE_FIELD=Title
AIRTABLE_AUTHOR_FIELD=Author
AIRTABLE_TECHNIQUE_FIELD=Technique
AIRTABLE_SIZE_FIELD=Size
AIRTABLE_YEAR_FIELD=Year
AIRTABLE_PRICE_FIELD=Price
AIRTABLE_IMAGE_FIELD=Image
```

`AIRTABLE_ROW_ID_FIELD` должен указывать на стабильное числовое поле Airtable. Рекомендуемый тип поля: `Autonumber`. Не используйте визуальный номер строки в интерфейсе Airtable.

## Поля Airtable

Минимальная таблица:

| Поле | Тип Airtable | Назначение |
| --- | --- | --- |
| `Row Number` | Autonumber | стабильный numeric ID для поиска |
| `Title` | Single line text | название |
| `Author` | Single line text | автор |
| `Technique` | Single line text | техника |
| `Size` | Single line text | размер |
| `Year` | Number или Single line text | год |
| `Price` | Currency или Single line text | цена |
| `Image` | Attachment или URL text | изображение |

Названия можно менять, но тогда нужно поменять соответствующие переменные `AIRTABLE_*_FIELD` в `.env`.

## Запуск бота

```powershell
.\.venv\Scripts\python -m artbot.main
```

После запуска откройте Telegram, найдите своего бота и отправьте:

```text
/start
/help
1
999
abc
```

## Запуск через Docker

Docker-вариант подходит для спокойного деплоя на сервере. Бот работает через polling, поэтому открывать порты не нужно.

1. Заполните `.env` реальными значениями.
2. Соберите image:

```powershell
docker compose build
```

3. Запустите бота:

```powershell
docker compose up -d
```

4. Посмотрите логи:

```powershell
docker compose logs -f artbot
```

5. Остановите бота:

```powershell
docker compose down
```

Для обновления кода на сервере:

```powershell
docker compose build --no-cache
docker compose up -d
```

## Локальные проверки без токенов

Полная локальная проверка:

```powershell
.\scripts\check.ps1
```

То же вручную:

```powershell
.\.venv\Scripts\python -m compileall artbot scripts tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts\local_e2e.py
```

`scripts/local_e2e.py` использует `fixtures/sample_records.json`, не обращается к реальному Airtable и проверяет:

- `/start`
- `/help`
- существующий row ID
- поиск по фамилии автора
- общий PDF по нескольким работам автора
- генерацию PDF
- отсутствие изображения
- неполные данные
- несуществующий row ID
- короткий текстовый ввод
- дублирующийся row ID

После запуска будет создан пример PDF в `output/sample_artwork_2.pdf`.

## Assumptions

- Основной идентификатор записи хранится в отдельном стабильном числовом поле Airtable.
- Рекомендуемое имя этого поля: `Row Number`.
- Рекомендуемый тип этого поля: `Autonumber`.
- Поле `Image` может быть Airtable Attachment или текстовой URL-ссылкой.
- Если изображение отсутствует или не загружается, бот все равно отправляет текст и PDF.
- Если отдельные поля пустые, бот подставляет `не указано`.
- Live e2e с Telegram и Airtable требует реальных `BOT_TOKEN`, Airtable PAT и заполненной базы.

## Ограничения

- Бот работает через polling, без webhook.
- Нет админки, базы данных, очередей и фоновых задач.
- Поиск работает только по одному положительному числовому ID.
- Если Airtable возвращает две записи с одним row ID, бот считает это ошибкой данных.

## Финальные ручные действия

Подробно они расписаны в `MANUAL_GUIDE.md`. Коротко:

1. Создать Telegram-бота через BotFather.
2. Создать Airtable base и таблицу с нужными полями.
3. Создать Airtable PAT с доступом на чтение этой базы.
4. Заполнить `.env`.
5. Запустить `.\scripts\check.ps1`.
6. Запустить `.\.venv\Scripts\python -m artbot.main`.
7. Проверить сценарии в Telegram.
