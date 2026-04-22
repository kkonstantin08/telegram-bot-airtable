# Telegram Bot Airtable Art Cards

Telegram-бот для выдачи карточек произведений искусства из Airtable.

Пользователь отправляет боту номер записи или фамилию автора. Бот получает данные из Airtable, отправляет карточку в Telegram и формирует PDF A4.

## Возможности

- Поиск одной работы по стабильному числовому ID из Airtable.
- Поиск работ по фамилии или части имени автора.
- Отправка карточки в Telegram: главное фото, основные поля и цена.
- Генерация PDF без цены: фото работы, описание, провенанс, экспертиза и обрамление.
- Поддержка нескольких фото в полях `Image`, `Экспертиза`, `Обрамление`.
- Обработка пустых полей: бот не падает, а пропускает отсутствующие данные или пишет `не указано`.
- Разбиение больших PDF по автору на несколько файлов.

## Как устроен проект

```text
artbot/
  main.py                  # точка входа бота
  config.py                # чтение .env и настройка полей Airtable
  domain.py                # модели данных
  airtable_repository.py   # запросы к Airtable
  handlers.py              # обработчики Telegram-сообщений
  messages.py              # тексты ответов бота
  pdf_generator.py         # генерация PDF
  mock_repository.py       # тестовый репозиторий для локальной проверки
fixtures/
  sample_records.json      # тестовые данные
scripts/
  check.ps1                # локальная проверка проекта
  local_e2e.py             # e2e-проверка без Telegram и Airtable
tests/
  test_*.py                # автотесты
Dockerfile                 # сборка Docker-образа
docker-compose.yml         # запуск контейнера
.env.example               # пример переменных окружения
```

## Требования

Для локального запуска:

- Python 3.12
- pip

Для серверного запуска:

- Docker
- Docker Compose plugin
- исходящий доступ к Airtable API и Telegram Bot API

## Поля Airtable

В таблице Airtable должны быть такие поля:

| Поле | Тип | Назначение |
| --- | --- | --- |
| `Row Number` | Autonumber | стабильный ID для поиска |
| `Title` | Single line text | название |
| `Author` | Single line text | автор |
| `Technique` | Single line text | техника |
| `Size` | Single line text | размер |
| `Year` | Number или text | год |
| `Price` | Currency или text | цена, выводится только в Telegram |
| `Image` | Attachment | одно или несколько фото работы |
| `Экспертиза` | Attachment | одно или несколько фото документов |
| `Обрамление` | Attachment | одно или несколько фото обрамления |
| `Провенанс/публикации/литература` | Long text | текстовый раздел PDF |

`Row Number` лучше делать именно типом `Autonumber`. Визуальный номер строки в Airtable может меняться при сортировке и фильтрах, а `Autonumber` остается стабильным.

Если названия полей в Airtable отличаются, их можно указать в `.env` через переменные `AIRTABLE_*_FIELD`.

## Порядок фото

Бот получает фото из Airtable через API. В Telegram отправляется первое фото из поля `Image`, а в PDF попадают все фото из `Image`.

Если визуальный порядок в Airtable отличается от порядка, который Airtable отдает через API, бот не сможет надежно определить порядок сам. Для строгого порядка можно доработать сортировку по имени файла, например `01_main.jpg`, `02_detail.jpg`, `03_back.jpg`.

## Настройка `.env`

Скопируйте пример:

```bash
cp .env.example .env
```

На Windows:

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
AIRTABLE_EXPERTISE_FIELD=Экспертиза
AIRTABLE_FRAMING_FIELD=Обрамление
AIRTABLE_PROVENANCE_FIELD=Провенанс/публикации/литература

LOG_LEVEL=INFO
REQUEST_TIMEOUT_SECONDS=4
TELEGRAM_REQUEST_TIMEOUT_SECONDS=300
AUTHOR_PDF_CHUNK_SIZE=50

PDF_FONT_PATH=
PDF_BOLD_FONT_PATH=
```

### Где взять значения

- `BOT_TOKEN` создается в Telegram через `@BotFather`.
- `AIRTABLE_API_KEY` это Airtable Personal Access Token со scope `data.records:read`.
- `AIRTABLE_BASE_ID` можно взять из URL Airtable или из Airtable API docs. Обычно выглядит как `appXXXXXXXXXXXXXX`.
- `AIRTABLE_TABLE_NAME` это точное название вкладки таблицы в Airtable.

Реальный `.env` нельзя коммитить и отправлять в публичный репозиторий.

## Локальный запуск

Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

На Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Запустите бота:

```bash
python -m artbot.main
```

На Windows:

```powershell
.\.venv\Scripts\python -m artbot.main
```

После запуска откройте Telegram и отправьте боту:

```text
/start
/help
1
```

## Проверка проекта

Полная локальная проверка:

```powershell
.\scripts\check.ps1
```

Ручной вариант:

```bash
python -m compileall artbot scripts tests
python -m pytest -q
python scripts/local_e2e.py
```

Проверка не требует реальных Telegram/Airtable-токенов, потому что использует тестовые данные из `fixtures/sample_records.json`.

## Деплой на сервер через Docker

Бот работает через polling. Публичный webhook URL и открытые входящие порты не нужны. Серверу нужен только исходящий интернет-доступ к Airtable и Telegram.

### Важно про Telegram в России

На российских серверах Telegram API может работать нестабильно или быть недоступен из-за сетевых ограничений. Если бот не подключается к Telegram, может понадобиться:

- сервер вне РФ;
- VPN или прокси на уровне сервера;
- отдельная доработка кода под явный Telegram-прокси.

Проверить доступность Telegram API на сервере можно так:

```bash
curl https://api.telegram.org
```

### Подготовка сервера

Установите Docker и Docker Compose plugin.

Проверка:

```bash
docker --version
docker compose version
```

## Вариант 1. Деплой из архива

Этот способ подходит, если проект передается заказчику архивом.

### 1. Подготовить архив

В архив нужно добавить код проекта, но не добавлять:

```text
.env
.venv/
venv/
output/
.pytest_cache/
__pycache__/
.git/
```

Если архив создается вручную, проверьте, что внутри есть:

```text
artbot/
Dockerfile
docker-compose.yml
requirements-prod.txt
.env.example
README.md
```

### 2. Загрузить архив на сервер

Пример через `scp`:

```bash
scp project.zip user@SERVER_IP:/home/user/
```

### 3. Распаковать

```bash
ssh user@SERVER_IP
cd /home/user
unzip project.zip -d telegram-bot-airtable
cd telegram-bot-airtable
```

Если архив уже содержит папку проекта, перейдите в нее после распаковки.

### 4. Создать `.env`

```bash
cp .env.example .env
nano .env
```

Заполните реальные токены и настройки Airtable.

### 5. Собрать и запустить

```bash
docker compose build
docker compose up -d
```

### 6. Посмотреть логи

```bash
docker compose logs -f artbot
```

## Вариант 2. Деплой через Git, публичный репозиторий

Если репозиторий публичный:

```bash
ssh user@SERVER_IP
cd /home/user
git clone https://github.com/OWNER/REPOSITORY.git telegram-bot-airtable
cd telegram-bot-airtable
cp .env.example .env
nano .env
docker compose build
docker compose up -d
```

Проверка логов:

```bash
docker compose logs -f artbot
```

## Вариант 3. Деплой через Git, приватный репозиторий

Для приватного репозитория есть два нормальных способа: SSH-ключ или GitHub token.

### Способ A. SSH-ключ и Deploy key

На сервере:

```bash
ssh user@SERVER_IP
ssh-keygen -t ed25519 -C "telegram-bot-airtable-server"
cat ~/.ssh/id_ed25519.pub
```

Скопируйте public key и добавьте его в GitHub:

```text
Repository -> Settings -> Deploy keys -> Add deploy key
```

Если серверу нужно только скачивать код, галочку `Allow write access` не включайте.

После этого клонируйте репозиторий:

```bash
cd /home/user
git clone git@github.com:OWNER/REPOSITORY.git telegram-bot-airtable
cd telegram-bot-airtable
cp .env.example .env
nano .env
docker compose build
docker compose up -d
```

### Способ B. HTTPS и Personal Access Token

Создайте GitHub Personal Access Token с доступом к приватному репозиторию.

Клонирование:

```bash
cd /home/user
git clone https://USERNAME:TOKEN@github.com/OWNER/REPOSITORY.git telegram-bot-airtable
cd telegram-bot-airtable
```

После клонирования лучше заменить remote URL, чтобы токен не лежал в `.git/config`:

```bash
git remote set-url origin https://github.com/OWNER/REPOSITORY.git
```

Дальше обычный запуск:

```bash
cp .env.example .env
nano .env
docker compose build
docker compose up -d
```

## Обновление проекта на сервере

### Если проект развернут из архива

1. Остановите контейнер:

```bash
docker compose down
```

2. Замените файлы проекта новой версией.
3. Не удаляйте рабочий `.env`.
4. Пересоберите и запустите:

```bash
docker compose build --no-cache
docker compose up -d
```

### Если проект развернут через Git

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

Если менялись только настройки `.env`, пересборка не нужна:

```bash
docker compose restart artbot
```

## Управление контейнером

Посмотреть статус:

```bash
docker compose ps
```

Посмотреть логи:

```bash
docker compose logs -f artbot
```

Перезапустить:

```bash
docker compose restart artbot
```

Остановить:

```bash
docker compose down
```

## Частые проблемы

### Бот не запускается

Проверьте `.env`. Эти переменные должны быть заполнены:

```env
BOT_TOKEN=
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=
```

### Бот не отвечает в Telegram

Проверьте:

- контейнер запущен: `docker compose ps`;
- в логах нет ошибок: `docker compose logs -f artbot`;
- токен Telegram правильный;
- сервер имеет доступ к `https://api.telegram.org`;
- если сервер в РФ, возможно нужен прокси или VPN.

### Запись не найдена

Проверьте:

- `AIRTABLE_BASE_ID`;
- `AIRTABLE_TABLE_NAME`;
- `AIRTABLE_ROW_ID_FIELD`;
- что пользователь отправляет значение из `Row Number`, а не визуальный номер строки слева.

### Airtable возвращает ошибку доступа

Проверьте Personal Access Token:

- есть scope `data.records:read`;
- токен имеет доступ к нужной base;
- `AIRTABLE_API_KEY` начинается с `pat`.

### PDF не показывает кириллицу

В Docker уже установлен `fonts-dejavu-core`. Если проблема возникла при локальном запуске, укажите шрифт вручную:

```env
PDF_FONT_PATH=C:\Windows\Fonts\arial.ttf
PDF_BOLD_FONT_PATH=C:\Windows\Fonts\arialbd.ttf
```

### Ответы стали медленнее

Чем больше фото в записи, тем дольше бот формирует PDF. Каждое изображение нужно скачать, обработать и вставить в документ.

## Финальная проверка перед сдачей

- [ ] `.env` заполнен реальными значениями.
- [ ] `Row Number` в Airtable является стабильным числовым полем.
- [ ] `/start` и `/help` отвечают.
- [ ] Поиск по номеру возвращает карточку и PDF.
- [ ] Поиск по автору возвращает общий PDF.
- [ ] Запись без фото не ломает бота.
- [ ] PDF открывается и содержит нужные разделы.
- [ ] На сервере контейнер запущен и логи без критических ошибок.
