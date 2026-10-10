# AI Photo Studio

Универсальный ИИ-сервис для генерации, редактирования, улучшения и анализа изображений.

## Возможности

| Функция | Как работает | API-ключ |
|---------|--------------|----------|
| Генерация по тексту | OpenAI Images API (`gpt-image-1`) | Да |
| Редактирование по описанию | OpenAI Images Edit | Да |
| Анализ / VQA | OpenAI Vision (`gpt-4o-mini`) | Да |
| Удаление фона | **rembg** (локально, u2net) | Нет |
| Улучшение качества | **Pillow** (резкость, контраст, 2×) | Нет |
| Авто-режим | AI Router → план операций | Зависит от шагов |
| История | SQLite | Нет |

## Требования

- Python **3.11** или **3.12** (рекомендуется)
- Windows 10/11, macOS или Linux
- Для генерации/редактирования/анализа — ключ [OpenAI](https://platform.openai.com/api-keys)

> **Примечание:** `rembg` требует Python ≥3.10 и <3.14. При первой загрузке модели u2net скачается ~176 МБ.

## Установка (Windows PowerShell)

```powershell
# 1. Перейти в папку проекта
cd ai_photo_studio

# 2. Создать виртуальное окружение
python -m venv venv

# 3. Активировать
.\venv\Scripts\Activate.ps1

# Если политика выполнения блокирует скрипты:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 4. Обновить pip и установить зависимости
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Настроить окружение
copy .env.example .env
# Откройте .env и укажите OPENAI_API_KEY=sk-...
```

## Установка (Linux / macOS)

```bash
cd ai_photo_studio
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Отредактируйте .env
```

## Настройка `.env`

Минимально для полной работы:

```env
OPENAI_API_KEY=sk-ваш-ключ
OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_VISION_MODEL=gpt-4o-mini
APP_ENV=development
```

Без ключа работают: удаление фона, улучшение качества, история, UI. Генерация/редактирование/анализ в `development` автоматически переключаются на mock-провайдер (заглушка).

## Запуск

```powershell
# из папки ai_photo_studio с активированным venv
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Откройте в браузере: **http://127.0.0.1:8000**

Проверка API:

```powershell
curl http://127.0.0.1:8000/api/health
```

## API (кратко)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Веб-интерфейс |
| GET | `/api/health` | Здоровье сервиса |
| GET | `/api/providers` | Список провайдеров |
| POST | `/api/generate` | JSON: prompt, n, width… |
| POST | `/api/edit` | multipart: image + prompt |
| POST | `/api/analyze` | multipart: image + question |
| POST | `/api/enhance` | multipart: image + mode |
| POST | `/api/remove-background` | multipart: image |
| POST | `/api/auto-process` | multipart: prompt + optional image |
| GET | `/api/history` | История |
| GET | `/api/results/{filename}` | Файл результата |

## Тесты

```powershell
pytest tests/ -v
```

Тесты не вызывают платные API — используется mock-провайдер и локальные алгоритмы.

## Типичные ошибки

| Симптом | Решение |
|---------|---------|
| `Провайдер «openai» не настроен` | Добавьте `OPENAI_API_KEY` в `.env` |
| `rembg` / onnxruntime ошибки | `pip install "rembg[cpu]"`; Python 3.11–3.12 |
| 413 / файл слишком большой | Лимит `MAX_UPLOAD_SIZE_MB` (по умолчанию 15) |
| Path traversal на `/api/results` | Имена файлов санитизируются — это ожидаемо |
| Медленный первый remove-bg | Скачивается модель u2net |

## Архитектура

```
app/
  core/          # конфиг, логи, исключения
  api/           # FastAPI-маршруты
  services/      # бизнес-логика + AI Router
  providers/     # подключаемые нейросети (OpenAI, mock…)
  models/        # SQLAlchemy + Pydantic
  utils/         # валидация изображений, хранилище
```

Чтобы добавить нового провайдера: реализуйте интерфейс из `providers/base.py` и зарегистрируйте в `providers/registry.py`.

## Безопасность

- Проверка реального формата изображения (Pillow), не только MIME
- Ограничение размера и разрешения
- Защита от path traversal при выдаче результатов
- API-ключи только в `.env` (не в репозитории)
- Пользовательский текст не исполняется как код

## Сценарий демо на хакатоне (5–7 мин)

1. Открыть UI, показать health и список провайдеров.
2. **Удаление фона** — локально, без ключа: загрузить фото человека/товара → «Удаление фона».
3. **Улучшение** — то же фото, режим «Авто» / «2×».
4. **Генерация** (с ключом): «Фотореалистичный спорткар на закате в горах».
5. **Авто-режим** с загруженным авто:  
   «Удали фон, поставь автомобиль на ночную улицу Токио, улучши качество».
6. Показать **Историю** и скачивание результата.
7. Кратко: модульные провайдеры, SQLite, готовность к PostgreSQL.

## Лицензия

Учебный / демонстрационный проект. Модели OpenAI и rembg имеют собственные условия использования.
