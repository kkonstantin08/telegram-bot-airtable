# Manual Guide

Этот гайд описывает все ручные действия, которые остаются после подготовки кода. Он рассчитан на запуск проекта с нуля на Windows в текущей папке проекта.

## 1. Подготовить Python и зависимости

1. Откройте PowerShell.
2. Перейдите в папку проекта:

```powershell
cd "C:\Users\user\Desktop\Заказы\Telegram_Bot_AirTable\Бот_Airtable"
```

3. Создайте виртуальное окружение:

```powershell
python -m venv .venv
```

4. Установите зависимости:

```powershell
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

5. Проверьте локальные тесты без внешних токенов:

```powershell
.\scripts\check.ps1
```

Ожидаемый результат: тесты завершаются успешно, в выводе есть `12 passed`, локальный e2e печатает сценарии, в папке `output` создается `sample_artwork_2.pdf`.

## 2. Создать Telegram-бота через BotFather

1. Откройте Telegram.
2. В поиске найдите `@BotFather`.
3. Откройте официальный чат BotFather.
4. Нажмите `Start` или отправьте:

```text
/start
```

5. Отправьте команду:

```text
/newbot
```

6. BotFather попросит имя бота. Введите человекочитаемое имя, например:

```text
Art Collection Card Bot
```

7. BotFather попросит username. Он должен заканчиваться на `bot`, например:

```text
art_collection_card_bot
```

Если username занят, придумайте другой, например `my_gallery_cards_bot`.

8. BotFather пришлет токен вида:

```text
1234567890:AAExampleTelegramTokenHere
```

9. Сохраните токен. Его нужно вставить в `.env` как `BOT_TOKEN`.

Важно: не публикуйте токен и не отправляйте его посторонним. Если токен утек, в BotFather используйте `/revoke`.

## 3. Подготовить `.env`

1. В PowerShell из папки проекта выполните:

```powershell
Copy-Item .env.example .env
```

2. Откройте файл `.env` в редакторе.
3. Вставьте Telegram-токен:

```env
BOT_TOKEN=1234567890:AAExampleTelegramTokenHere
```

Остальные Airtable-значения будут заполнены после настройки Airtable.

## 4. Создать Airtable base

1. Откройте Airtable в браузере.
2. Войдите в аккаунт.
3. На главной странице нажмите `Create`.
4. Выберите `Start from scratch` или пустую базу.
5. Назовите base, например:

```text
Art Collection
```

6. Создайте таблицу или переименуйте первую таблицу в:

```text
Objects
```

Это значение потом пойдет в `.env`:

```env
AIRTABLE_TABLE_NAME=Objects
```

Если вы назовете таблицу иначе, укажите точное имя в `AIRTABLE_TABLE_NAME`.

## 5. Создать поля Airtable

В таблице `Objects` создайте поля:

| Имя поля | Тип | Пример |
| --- | --- | --- |
| `Row Number` | Autonumber | `1` |
| `Title` | Single line text | `Композиция с красной линией` |
| `Author` | Single line text | `Анна Иванова` |
| `Technique` | Single line text | `Холст, акрил` |
| `Size` | Single line text | `80 x 60 см` |
| `Year` | Number или Single line text | `2024` |
| `Price` | Currency или Single line text | `250 000 ₽` |
| `Image` | Attachment | файл изображения |

### Как создать `Row Number`

1. Нажмите `+` справа от существующих колонок.
2. Введите имя поля:

```text
Row Number
```

3. В типе поля выберите `Autonumber`.
4. Нажмите `Create field`.

Почему так: визуальный номер строки в Airtable может меняться при сортировке и фильтрах. Поле `Autonumber` остается стабильным идентификатором записи.

### Если поле уже есть

Если в вашей базе уже есть стабильное числовое поле, можно использовать его. Тогда в `.env` укажите его точное имя:

```env
AIRTABLE_ROW_ID_FIELD=Internal ID
```

Главное условие: поле должно быть числовым, стабильным и уникальным.

## 6. Создать тестовые записи в Airtable

Создайте 2-3 записи для проверки.

### Тестовая запись 1

| Поле | Значение |
| --- | --- |
| `Title` | `Композиция с красной линией` |
| `Author` | `Анна Иванова` |
| `Technique` | `Холст, акрил` |
| `Size` | `80 x 60 см` |
| `Year` | `2024` |
| `Price` | `250 000 ₽` |
| `Image` | загрузите любое тестовое изображение |

`Row Number` заполнится автоматически, например `1`.

### Тестовая запись 2 без изображения

| Поле | Значение |
| --- | --- |
| `Title` | `Без названия` |
| `Author` | `Петр Орлов` |
| `Technique` | `Бумага, тушь` |
| `Size` | `42 x 30 см` |
| `Year` | `2023` |
| `Price` | `90 000 ₽` |
| `Image` | оставьте пустым |

Ожидаемый результат: бот не падает и отправляет текстовую карточку плюс PDF.

### Тестовая запись 3 с неполными данными

| Поле | Значение |
| --- | --- |
| `Title` | `Фрагмент памяти` |
| `Author` | пусто |
| `Technique` | пусто |
| `Size` | `100 x 100 см` |
| `Year` | пусто |
| `Price` | пусто |
| `Image` | пусто |

Ожидаемый результат: бот подставляет `не указано` для пустых полей.

## 7. Получить Airtable Personal Access Token

1. В Airtable откройте страницу разработчика / токенов.
2. Создайте новый Personal Access Token.
3. Назовите токен, например:

```text
Telegram Art Bot Read Token
```

4. В scopes добавьте право на чтение записей:

```text
data.records:read
```

5. В доступе выберите только нужную base `Art Collection`.
6. Создайте токен.
7. Скопируйте значение токена. Оно обычно начинается с `pat`.
8. Вставьте в `.env`:

```env
AIRTABLE_API_KEY=pat_real_token_here
```

## 8. Получить Base ID

Есть два простых способа.

### Способ 1: из Airtable API docs

1. Откройте Airtable.
2. Откройте нужную base.
3. Откройте API documentation для этой base.
4. Найдите Base ID, он выглядит примерно так:

```text
appXXXXXXXXXXXXXX
```

5. Вставьте в `.env`:

```env
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
```

### Способ 2: из URL

В URL Airtable часто есть фрагмент вида:

```text
https://airtable.com/appXXXXXXXXXXXXXX/...
```

Часть `appXXXXXXXXXXXXXX` и есть Base ID.

## 9. Проверить Table Name

1. Откройте Airtable base.
2. Посмотрите точное имя вкладки таблицы.
3. Если вкладка называется `Objects`, оставьте:

```env
AIRTABLE_TABLE_NAME=Objects
```

4. Если вкладка называется по-другому, например `Works`, укажите:

```env
AIRTABLE_TABLE_NAME=Works
```

Имя чувствительно к пробелам и опечаткам.

## 10. Заполнить полный `.env`

Пример готового `.env`:

```env
BOT_TOKEN=1234567890:AAExampleTelegramTokenHere
AIRTABLE_API_KEY=pat_real_airtable_token_here
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

LOG_LEVEL=INFO
REQUEST_TIMEOUT_SECONDS=4
PDF_FONT_PATH=
PDF_BOLD_FONT_PATH=
```

Если PDF показывает кириллицу некорректно, укажите путь к TTF-шрифту:

```env
PDF_FONT_PATH=C:\Windows\Fonts\arial.ttf
PDF_BOLD_FONT_PATH=C:\Windows\Fonts\arialbd.ttf
```

На Windows обычно это не нужно, код сам ищет Arial.

## 11. Запустить бота локально

В PowerShell:

```powershell
cd "C:\Users\user\Desktop\Заказы\Telegram_Bot_AirTable\Бот_Airtable"
.\.venv\Scripts\python -m artbot.main
```

Ожидаемый результат в консоли:

```text
Bot started
```

Оставьте это окно открытым. Пока процесс работает, бот отвечает в Telegram.

## 12. Проверить Telegram-сценарии

Откройте чат со своим ботом.

### Проверка `/start`

Отправьте:

```text
/start
```

Ожидаемый ответ: бот говорит, что нужно прислать номер строки / числовой ID.

### Проверка `/help`

Отправьте:

```text
/help
```

Ожидаемый ответ: краткая инструкция, без текстового поиска.

### Проверка существующего ID

Если первая запись в Airtable получила `Row Number = 1`, отправьте:

```text
1
```

Ожидаемый результат:

1. Бот отправляет изображение с подписью.
2. Подпись содержит название, автора, технику, размер, год, цену.
3. Бот отправляет PDF-файл `artwork_1.pdf`.

### Проверка записи без изображения

Если вторая запись получила `Row Number = 2`, отправьте:

```text
2
```

Ожидаемый результат:

1. Бот отправляет текстовую карточку.
2. В тексте есть `Изображение не указано`.
3. Бот отправляет PDF.

### Проверка несуществующей записи

Отправьте заведомо несуществующий номер:

```text
999999
```

Ожидаемый ответ: `Запись с таким номером не найдена...`

### Проверка нечислового ввода

Отправьте:

```text
abc
```

Ожидаемый ответ: бот просит прислать именно номер строки / числовой ID.

## 13. Проверить PDF

1. В Telegram откройте PDF, который прислал бот.
2. Проверьте, что формат похож на A4-карточку.
3. Проверьте порядок блоков:
   - заголовок,
   - изображение или placeholder,
   - название,
   - автор,
   - техника,
   - размер,
   - год.
4. Проверьте, что цена в PDF не выводится. Цена остается только в сообщении Telegram.
5. Проверьте длинные значения в Airtable, например длинное название. PDF не должен падать.
6. Проверьте запись без изображения. PDF должен сформироваться с placeholder.

## 14. Проверить дублирующийся row ID

Если `Row Number` имеет тип `Autonumber`, дубликаты невозможны штатно. Это лучший вариант.

Если вы используете ручное числовое поле, временно создайте две записи с одинаковым значением, например `100`.

Отправьте боту:

```text
100
```

Ожидаемый результат: бот сообщает, что найдено несколько записей с таким номером, и не выбирает запись автоматически.

После проверки удалите дубликат или исправьте значение.

## 15. Заменить тестовые данные на реальные

1. Откройте Airtable.
2. Удалите тестовые записи или замените значения в них.
3. Для каждой реальной работы заполните:
   - `Title`,
   - `Author`,
   - `Technique`,
   - `Size`,
   - `Year`,
   - `Price`,
   - `Image`.
4. Не редактируйте `Row Number`, если это `Autonumber`.
5. Для проверки отправьте боту row ID одной реальной записи.

## 16. Troubleshooting

### Бот не запускается и пишет, что не хватает переменных

Проверьте, что есть файл `.env`, а не только `.env.example`.

Проверьте строки:

```env
BOT_TOKEN=
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=
```

Они не должны быть пустыми.

### Telegram пишет, что токен неверный

1. Вернитесь в BotFather.
2. Проверьте токен.
3. Убедитесь, что в `.env` нет пробелов вокруг токена.
4. Если токен был отозван, получите новый через BotFather.

### Бот отвечает, что запись не найдена

Проверьте:

1. В `.env` правильно указан `AIRTABLE_BASE_ID`.
2. В `.env` правильно указан `AIRTABLE_TABLE_NAME`.
3. В `.env` правильно указан `AIRTABLE_ROW_ID_FIELD`.
4. В Airtable это поле действительно числовое.
5. Вы отправляете значение из поля `Row Number`, а не визуальный номер строки слева.

### Airtable возвращает ошибку доступа

Проверьте PAT:

1. У токена есть scope `data.records:read`.
2. Токен имеет доступ именно к нужной base.
3. `AIRTABLE_API_KEY` начинается с `pat`.

### PDF не показывает кириллицу

Добавьте в `.env`:

```env
PDF_FONT_PATH=C:\Windows\Fonts\arial.ttf
PDF_BOLD_FONT_PATH=C:\Windows\Fonts\arialbd.ttf
```

Перезапустите бота.

### Изображение не отправляется

Проверьте:

1. В Airtable поле `Image` имеет тип Attachment или содержит прямую URL-ссылку.
2. Файл изображения доступен.
3. Размер изображения не слишком большой для Telegram.

Даже если изображение не отправится, бот должен отправить текст и PDF.

### Ответы дольше 5 секунд

Проверьте:

1. Скорость Airtable.
2. Размер изображения.
3. Стабильность интернета.
4. Значение `REQUEST_TIMEOUT_SECONDS`.

Для нормальных записей с обычным изображением целевое время ответа должно быть в районе нескольких секунд.

## 17. Final verification checklist

Перед передачей или продакшеном проверьте:

- [ ] `.env` заполнен реальными значениями.
- [ ] `AIRTABLE_ROW_ID_FIELD` указывает на стабильное числовое поле.
- [ ] Лучше всего используется `Autonumber`.
- [ ] В таблице нет дубликатов row ID.
- [ ] `/start` отвечает корректно.
- [ ] `/help` отвечает корректно.
- [ ] ID существующей записи возвращает карточку.
- [ ] ID существующей записи возвращает PDF.
- [ ] Номер без записи возвращает понятное сообщение.
- [ ] Текстовый ввод возвращает просьбу прислать число.
- [ ] Запись без изображения не ломает бота.
- [ ] Запись с пустыми полями не ломает бота.
- [ ] PDF открывается и выглядит аккуратно.
- [ ] Логи не содержат неожиданных ошибок.

## 18. Подготовка к передаче или деплою

Минимальный пакет для передачи:

- весь код проекта,
- `.env.example`,
- `README.md`,
- `MANUAL_GUIDE.md`,
- `HANDOFF_SUMMARY.md`,
- список реальных переменных `.env`, переданный безопасным способом.

Не передавайте реальный `.env` через публичный репозиторий.

Для постоянной работы бот можно запустить через Docker на VPS, Windows Server или любом хостинге, где доступен Docker. Текущая версия использует polling, поэтому отдельный публичный webhook URL и открытые порты не нужны.

## 19. Docker-запуск на сервере

Этот способ лучше всего подходит для нормального серверного запуска.

### Что должно быть на сервере

На сервере должны быть установлены:

- Docker,
- Docker Compose plugin.

Проверка:

```bash
docker --version
docker compose version
```

Ожидаемый результат: обе команды показывают версии без ошибок.

### Передать проект на сервер

Вариант 1: через git.

```bash
git clone <your-repository-url>
cd <project-folder>
```

Вариант 2: архивом.

1. Заархивируйте папку проекта без `.venv` и без `.env`.
2. Загрузите архив на сервер.
3. Распакуйте архив.
4. Перейдите в папку проекта.

### Создать `.env` на сервере

В папке проекта на сервере выполните:

```bash
cp .env.example .env
nano .env
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
LOG_LEVEL=INFO
REQUEST_TIMEOUT_SECONDS=4
PDF_FONT_PATH=
PDF_BOLD_FONT_PATH=
```

Сохраните файл:

- в `nano`: `Ctrl+O`, Enter, `Ctrl+X`.

### Собрать Docker image

В папке проекта:

```bash
docker compose build
```

Ожидаемый результат: Docker скачивает `python:3.12-slim`, устанавливает зависимости и завершает сборку без ошибок.

### Запустить бота

```bash
docker compose up -d
```

Ожидаемый результат:

```text
Container ... Started
```

### Посмотреть логи

```bash
docker compose logs -f artbot
```

Ожидаемый результат: в логах есть сообщение о старте бота. Если в `.env` ошибка, она будет видна здесь.

### Проверить в Telegram

Откройте чат с ботом и отправьте:

```text
/start
/help
1
999999
abc
```

Ожидаемые результаты:

- `/start` объясняет сценарий,
- `/help` показывает инструкцию,
- `1` возвращает карточку и PDF,
- `999999` сообщает, что запись не найдена,
- `abc` просит прислать число.

### Остановить контейнер

```bash
docker compose down
```

### Перезапустить контейнер

```bash
docker compose restart artbot
```

### Обновить код на сервере

Если проект развернут через git:

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

Если проект загружен архивом:

1. Остановите контейнер:

```bash
docker compose down
```

2. Замените файлы проекта новой версией.
3. Проверьте, что `.env` остался на месте.
4. Соберите и запустите:

```bash
docker compose build --no-cache
docker compose up -d
```

### Docker troubleshooting

Если команда `docker compose` не найдена:

```bash
docker-compose --version
```

Если доступен только старый `docker-compose`, можно временно использовать:

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f artbot
```

Если контейнер постоянно перезапускается:

```bash
docker compose ps
docker compose logs --tail=100 artbot
```

Чаще всего причина в неправильном `.env`: неверный `BOT_TOKEN`, неверный Airtable PAT, Base ID или имя таблицы.

Если PDF в Docker показывает кириллицу некорректно, пересоберите image. В `Dockerfile` уже установлен пакет `fonts-dejavu-core`, и код автоматически использует DejaVu Sans внутри контейнера.
