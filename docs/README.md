# Furniture Production System

Подсистема для работы с продукцией мебельной компании.

## Запуск через Docker

1. Склонируйте репозиторий, перейдите в каталог.
2. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
3. Поместите файлы `*_import.xlsx` в директорию `data/` с такими именами:
   - `Workshops_import.xlsx`
   - `Product_workshops_import.xlsx`
   - `Product_type_import.xlsx`
   - `Products_import.xlsx`
   - `Material_type_import.xlsx`
4. Запустите:
   ```bash
   docker-compose up --build
   ```
   - Сервис `db` поднимет PostgreSQL и выполнит `db/init.sql`.
   - Сервис `importer` загрузит данные из `data/` в БД.
   - Сервис `app` запустит API на `http://localhost:8000`.

## Проверка API

- Список продукции:
  - `GET http://localhost:8000/products`
- Добавление продукции:
  - `POST http://localhost:8000/products` (JSON‑тело см. в `/docs`)
- Редактирование:
  - `PUT http://localhost:8000/products/{id}`
- Список цехов:
  - `GET http://localhost:8000/workshops`
- Маршрут и время изготовления по продукту:
  - `GET http://localhost:8000/products/{id}/workshops`

Интерактивная документация: `http://localhost:8000/docs`.

## Локальный запуск без Docker (опционально)

1. Установить PostgreSQL, создать БД `furniture`, пользователя и выполнить `db/init.sql`.
2. Создать виртуальное окружение Python 3.12+, установить зависимости:
   ```bash
   pip install -r scripts/requirements.txt
   ```
3. Заполнить `.env` с параметрами подключения.
4. Импорт данных:
   ```bash
   python scripts/import_data.py
   ```
5. Запуск API:
   ```bash
   uvicorn app.main:app --reload
   ```