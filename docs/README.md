# Furniture Production System

Подсистема для работы с продукцией мебельной компании: просмотр/добавление/редактирование продукции и цехов, а также расчёт времени изготовления продукции как суммы времени по цехам.

---

## Технологии

- Python 3.12
- FastAPI + Jinja2 (HTML‑интерфейс и REST API)
- SQLAlchemy 2.x
- PostgreSQL 16
- Docker / Docker Compose
- Импорт данных из Excel: pandas + openpyxl

---

## Быстрый старт (Docker Compose)

### 1) Подготовить окружение

Скопируйте пример переменных окружения:

```bash
cp .env.example .env
```

### 2) Подготовить данные для импорта

Поместите файлы `*_import.xlsx` в директорию `data/` (в корне проекта) со строгими именами:

- `Workshops_import.xlsx`
- `Product_workshops_import.xlsx`
- `Product_type_import.xlsx`
- `Products_import.xlsx`
- `Material_type_import.xlsx`

### 3) Запуск

```bash
docker-compose up --build
```

Что произойдёт:

- `db` поднимет PostgreSQL и выполнит `db/init.sql` (создание таблиц и ограничений).
- `importer` загрузит данные из `data/` в БД (скрипт `scripts/import_data.py`).
- `app` запустит веб‑приложение на `http://localhost:8000`.

---

## Веб‑интерфейс (задание 3)

- Главный экран (список продукции):  
  `http://localhost:8000/ui/products`

- Список цехов:  
  `http://localhost:8000/ui/workshops`

В интерфейсе реализованы:

- единая шапка с логотипом и названием;
- sidebar‑меню для переключения страниц;
- таблицы со списками и действиями «Редактировать/Удалить»;
- кнопки «Добавить» для продукции и цехов;
- формы добавления/редактирования с серверной валидацией и понятными сообщениями;
- подтверждение удаления (необратимая операция);
- футер `© 2006–2025`.

---

## REST API (задание 2)

Swagger / OpenAPI документация:

- `http://localhost:8000/docs`

Основные эндпоинты:

### Продукция
- `GET /products` — список продукции
- `POST /products` — добавить продукцию
- `PUT /products/{id}` — редактировать продукцию
- `DELETE /products/{id}` — удалить продукцию

### Цеха
- `GET /workshops` — список цехов
- `POST /workshops` — добавить цех
- `PUT /workshops/{id}` — редактировать цех
- `DELETE /workshops/{id}` — удалить цех

### Маршрут изготовления (продукт–цех)
- `GET /products/{id}/workshops` — цеха и время по продукту
- `POST /products/{id}/workshops` — добавить шаг маршрута
- `PUT /products/{id}/workshops/{workshop_id}` — изменить время
- `DELETE /products/{id}/workshops/{workshop_id}` — удалить шаг

### Карточки продукции с временем изготовления
- `GET /product-cards` — список продукции + рассчитанное `production_time_hours`  
  (сумма времени по цехам, округление вверх до целого часа; если цехов нет — 0)

---

## Локальный запуск без Docker (опционально)

1. Поднять PostgreSQL, создать БД и пользователя, выполнить:
   ```bash
   psql -f db/init.sql
   ```

2. Установить зависимости:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r scripts/requirements.txt
   ```

3. Создать `.env` по образцу `.env.example` и указать параметры подключения.

4. Импорт данных:
   ```bash
   python scripts/import_data.py
   ```

5. Запуск приложения:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## Документация по заданиям

- `docs/report1.md` — задание 1 (БД, 3НФ, импорт, ER‑диаграмма)
- `docs/report2.md` — задание 2 (бэкенд и REST API)
- `docs/report3.md` — задание 3 (HTML‑интерфейс, навигация, валидация, сообщения)

ER‑диаграмма должна быть сохранена как `docs/er_diagram.pdf` (экспорт из pgAdmin / DBeaver).
```
