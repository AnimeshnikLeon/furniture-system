# Отчёт по заданию 2 (бэкенд подсистемы продукции)

## Цель

Разработать серверную часть подсистемы для работы с продукцией мебельной компании:
- получать и изменять данные о продукции и цехах;
- рассчитывать время изготовления продукции как сумму времени пребывания в каждом цехе;
- работать с ранее созданной БД PostgreSQL.

## 1. Выбор фреймворка и стека

- **Фреймворк**: FastAPI  
  Причины выбора:
  - простое описание REST‑эндпоинтов;
  - автоматическая генерация OpenAPI и Swagger UI;
  - тесная интеграция с Pydantic и type hints.
- **ORM**: SQLAlchemy 2.x — удобная работа с PostgreSQL, декларативные модели.
- **СУБД**: PostgreSQL (из задания 1), подключение через `psycopg2-binary`.
- Всё упаковано в Docker‑контейнеры и запускается через `docker compose`.

## 2. Архитектура бэкенда

Структура каталога `app/`:

- `database.py` — создание `engine`, `SessionLocal`, базового класса ORM.
- `models.py` — ORM‑модели: `ProductType`, `MaterialType`, `WorkshopType`,
  `Workshop`, `Product`, `ProductWorkshop`.
- `schemas.py` — Pydantic‑схемы для ввода/вывода данных (DTO).
- `main.py` — FastAPI‑приложение, описание REST‑эндпоинтов и бизнес‑логики.

Слои разделены:

- **БД‑слой** — SQLAlchemy‑модели и связи.
- **Схемы** — объекты, которые уезжают в сеть (ответы API) и принимаются от клиента.
- **Контроллеры** — функции FastAPI (`@app.get/post/...`), которые получают запросы,
  открывают сессию БД, вызывают ORM и возвращают схемы.

## 3. Подключение БД к бэкенду

- Параметры подключения хранятся в `.env`
  (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`).
- `database.py` строит строку подключения и создаёт:

  ```python
  engine = create_engine(DB_URL, echo=False, future=True)
  SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
  ```

- В `main.py` используется зависимость `get_db()`:
  на каждый HTTP‑запрос создаётся сессия SQLAlchemy и корректно закрывается.

## 4. Архитектура API (REST)

Выбрана REST‑архитектура. Реализованы следующие группы эндпоинтов.

### 4.1. Справочники

- `GET /product-types` — список типов продукции.
- `GET /material-types` — список типов материалов.
- `GET /workshop-types` — список типов цехов.

Используются для построения выпадающих списков при создании/редактировании продукции.

### 4.2. Цеха (CRUD)

- `GET /workshops` — список всех цехов.
- `GET /workshops/{id}` — получение одного цеха.
- `POST /workshops` — создание нового цеха.
- `PUT /workshops/{id}` — редактирование существующего цеха.
- `DELETE /workshops/{id}` — удаление цеха.

При создании/редактировании используются схемы `WorkshopCreate` и `WorkshopUpdate`.
Нарушение уникальности названия ловится через `IntegrityError` и
отдаётся с кодом 400 вместо падения сервера.

### 4.3. Продукция (CRUD)

- `GET /products` — список всех продуктов с типом и материалом.
- `GET /products/{id}` — получение одного продукта.
- `POST /products` — создание нового продукта.
- `PUT /products/{id}` — изменение полей продукта.
- `DELETE /products/{id}` — удаление продукта.

Используются схемы `ProductCreate`, `ProductUpdate`, `ProductOut`.
При создании ловится конфликт по артикулу/названию и возвращается 400.

### 4.4. Маршрут изготовления (связь продукт–цех)

- `GET /products/{id}/workshops` — список всех шагов изготовления для продукта
  (цех + время пребывания). Схема ответа `ProductWorkshopOut`.
- `POST /products/{id}/workshops` — добавить новый шаг:
  указывается `workshop_id` и `production_time_hours`.
- `PUT /products/{id}/workshops/{workshop_id}` — обновить время для существующей
  пары продукт–цех.
- `DELETE /products/{id}/workshops/{workshop_id}` — удалить шаг маршрута.

При добавлении проверяется существование и продукта, и цеха;
повторная попытка привязать один и тот же цех к продукту возвращает 400.

### 4.5. Расчёт времени изготовления продукции

Реализовано в эндпоинте:

- `GET /product-cards` — карточки продукции с рассчитанным временем изготовления.

Алгоритм:

```sql
SELECT
  product.id,
  ...,
  COALESCE(SUM(product_workshop.production_time_hours), 0) AS total_hours
FROM product
JOIN product_type ...
JOIN material_type ...
LEFT JOIN product_workshop ON product.id = product_workshop.product_id
GROUP BY product.id, ...
```

Далее в Python каждая сумма округляется вверх до целого:

```python
total_hours_int = int(total_hours_decimal.to_integral_value(rounding=ROUND_CEILING))
```

В API это представлено схемой `ProductCard`, где `production_time_hours` — `int`.

## 5. Алгоритм и отладка

1. После сборки контейнеров (`docker compose up --build`)
   - БД создаётся по `db/init.sql`.
   - Скрипт `import_data.py` загружает данные из Excel.
   - FastAPI‑приложение стартует на `http://localhost:8000`.

2. Для проверки работы бэкенда использовался Swagger UI (`/docs`):
   - Тестировались все CRUD‑операции на продуктах и цехах.
   - При попытке запросить/изменить несуществующий объект возвращается 404.
   - При нарушении уникальности названия цеха или артикула продукта
     возвращается 400, а не 500.

3. Корректность расчёта времени изготовления проверялась выборочно:
   - Для нескольких изделий вручную суммировалось время по всем цехам по данным
     `Product_workshops_import.xlsx`;
   - Результат, выданный `/product-cards`, совпадает с суммой,
     округлённой до целого вверх.
