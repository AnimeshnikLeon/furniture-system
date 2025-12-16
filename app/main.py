from decimal import Decimal, InvalidOperation
from pathlib import Path
from math import ceil
from typing import List, Dict, Any

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    Request,
    status,
    Form,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas, services
from .database import SessionLocal

app = FastAPI(title="Furniture Production System")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# Вспомогательные функции для HTML‑интерфейса
# =========================================================

def build_status_messages(request: Request) -> List[Dict[str, Any]]:
    """
    Преобразует код статуса в человекочитаемые сообщения
    для отображения в интерфейсе.
    """
    code = request.query_params.get("status")
    if not code:
        return []

    mapping = {
        "product_created": (
            "success",
            "Продукт добавлен",
            "Новая запись о продукции успешно сохранена в базе данных.",
        ),
        "product_updated": (
            "success",
            "Продукт обновлён",
            "Изменения сохранены.",
        ),
        "product_deleted": (
            "info",
            "Продукт удалён",
            "Запись о продукции удалена без ошибок.",
        ),
        "product_not_found": (
            "error",
            "Продукт не найден",
            "Запрошенный продукт не существует или уже был удалён.",
        ),
        "workshop_created": (
            "success",
            "Цех добавлен",
            "Информация о новом цехе успешно сохранена.",
        ),
        "workshop_updated": (
            "success",
            "Цех обновлён",
            "Информация о цехе успешно изменена.",
        ),
        "workshop_deleted": (
            "info",
            "Цех удалён",
            "Запись о цехе удалена.",
        ),
        "workshop_not_found": (
            "error",
            "Цех не найден",
            "Запрошенный цех не существует или уже был удалён.",
        ),
    }

    msg = mapping.get(code)
    if not msg:
        return []

    msg_type, title, text = msg
    return [{"type": msg_type, "title": title, "text": text}]


def parse_price_ru(
    raw_value: str,
    field_errors: Dict[str, str],
    field_key: str,
) -> Decimal | None:
    """
    Парсинг денежного значения из строки (поддержка ',' и '.').
    При ошибке записывает сообщение в field_errors[field_key].
    """
    cleaned = (raw_value or "").strip().replace(" ", "").replace(",", ".")
    if not cleaned:
        field_errors[field_key] = "Укажите минимальную стоимость."
        return None

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        field_errors[field_key] = "Введите число в формате 1234,56."
        return None

    if value < 0:
        field_errors[field_key] = "Стоимость не может быть отрицательной."
        return None

    return value.quantize(Decimal("0.01"))


def parse_positive_int(
    raw_value: str,
    field_errors: Dict[str, str],
    field_key: str,
    field_title: str,
) -> int | None:
    """
    Парсинг целого положительного числа для форм HTML.
    """
    cleaned = (raw_value or "").strip()
    if not cleaned:
        field_errors[field_key] = f"Укажите значение поля «{field_title}»."
        return None

    try:
        value = int(cleaned)
    except ValueError:
        field_errors[field_key] = f"Поле «{field_title}» должно быть целым числом."
        return None

    if value <= 0:
        field_errors[field_key] = f"Поле «{field_title}» должно быть больше нуля."
        return None

    return value


# =========================================================
# Справочники
# =========================================================

@app.get("/product-types", response_model=List[schemas.ProductTypeOut])
def list_product_types(db: Session = Depends(get_db)):
    return db.query(models.ProductType).order_by(models.ProductType.name).all()


@app.get("/material-types", response_model=List[schemas.MaterialTypeOut])
def list_material_types(db: Session = Depends(get_db)):
    return db.query(models.MaterialType).order_by(models.MaterialType.name).all()


@app.get("/workshop-types", response_model=List[schemas.WorkshopTypeOut])
def list_workshop_types(db: Session = Depends(get_db)):
    return db.query(models.WorkshopType).order_by(models.WorkshopType.name).all()


# =========================================================
# Цеха (CRUD, JSON API)
# =========================================================

@app.get("/workshops", response_model=List[schemas.WorkshopOut])
def list_workshops(db: Session = Depends(get_db)):
    return db.query(models.Workshop).all()


@app.get("/workshops/{workshop_id}", response_model=schemas.WorkshopOut)
def get_workshop(workshop_id: int, db: Session = Depends(get_db)):
    ws = db.get(models.Workshop, workshop_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return ws


@app.post(
    "/workshops",
    response_model=schemas.WorkshopOut,
    status_code=status.HTTP_201_CREATED,
)
def create_workshop(
    workshop: schemas.WorkshopCreate,
    db: Session = Depends(get_db),
):
    ws = models.Workshop(**workshop.dict())
    db.add(ws)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Workshop with this name already exists",
        )
    db.refresh(ws)
    return ws


@app.put("/workshops/{workshop_id}", response_model=schemas.WorkshopOut)
def update_workshop(
    workshop_id: int,
    upd: schemas.WorkshopUpdate,
    db: Session = Depends(get_db),
):
    ws = db.get(models.Workshop, workshop_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop not found")

    for field, value in upd.dict(exclude_unset=True).items():
        setattr(ws, field, value)

    db.commit()
    db.refresh(ws)
    return ws


@app.delete("/workshops/{workshop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workshop(workshop_id: int, db: Session = Depends(get_db)):
    ws = db.get(models.Workshop, workshop_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop not found")

    db.delete(ws)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =========================================================
# Продукция (CRUD, JSON API)
# =========================================================

@app.get("/products", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()


@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.get(models.Product, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod


@app.post(
    "/products",
    response_model=schemas.ProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product(prod: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_prod = models.Product(**prod.dict())
    db.add(db_prod)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Product with this article or name already exists",
        )
    db.refresh(db_prod)
    return db_prod


@app.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    upd: schemas.ProductUpdate,
    db: Session = Depends(get_db),
):
    db_prod = db.get(models.Product, product_id)
    if not db_prod:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in upd.dict(exclude_unset=True).items():
        setattr(db_prod, field, value)

    db.commit()
    db.refresh(db_prod)
    return db_prod


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_prod = db.get(models.Product, product_id)
    if not db_prod:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_prod)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =========================================================
# Связь продукт–цех (маршрут изготовления, JSON API)
# =========================================================

@app.get(
    "/products/{product_id}/workshops",
    response_model=List[schemas.ProductWorkshopOut],
)
def get_product_workshops(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product.workshops


@app.post(
    "/products/{product_id}/workshops",
    response_model=schemas.ProductWorkshopOut,
    status_code=status.HTTP_201_CREATED,
)
def add_product_workshop(
    product_id: int,
    body: schemas.ProductWorkshopCreate,
    db: Session = Depends(get_db),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    workshop = db.get(models.Workshop, body.workshop_id)
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")

    link = models.ProductWorkshop(
        product_id=product_id,
        workshop_id=body.workshop_id,
        production_time_hours=body.production_time_hours,
    )

    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="This workshop is already linked to the product",
        )
    db.refresh(link)
    return link


@app.put(
    "/products/{product_id}/workshops/{workshop_id}",
    response_model=schemas.ProductWorkshopOut,
)
def update_product_workshop(
    product_id: int,
    workshop_id: int,
    body: schemas.ProductWorkshopUpdate,
    db: Session = Depends(get_db),
):
    link = (
        db.query(models.ProductWorkshop)
        .filter_by(product_id=product_id, workshop_id=workshop_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Product-workshop link not found")

    for field, value in body.dict(exclude_unset=True).items():
        setattr(link, field, value)

    db.commit()
    db.refresh(link)
    return link


@app.delete(
    "/products/{product_id}/workshops/{workshop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_workshop(
    product_id: int,
    workshop_id: int,
    db: Session = Depends(get_db),
):
    link = (
        db.query(models.ProductWorkshop)
        .filter_by(product_id=product_id, workshop_id=workshop_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Product-workshop link not found")

    db.delete(link)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =========================================================
# Карточки продукции с расчётом времени (JSON API)
# =========================================================

@app.get("/product-cards", response_model=List[schemas.ProductCard])
def list_product_cards(db: Session = Depends(get_db)):
    """
    Возвращает карточки продукции с суммарным временем изготовления.
    Время = сумма времени по всем цехам, округлённая вверх до целого часа.
    """
    query = (
        db.query(
            models.Product.id.label("id"),
            models.Product.name.label("name"),
            models.Product.article.label("article"),
            models.Product.min_partner_price.label("min_partner_price"),
            models.ProductType.name.label("product_type"),
            models.MaterialType.name.label("material_type"),
            func.coalesce(
                func.sum(models.ProductWorkshop.production_time_hours),
                0.0,
            ).label("total_hours"),
        )
        .join(models.ProductType, models.Product.product_type_id == models.ProductType.id)
        .join(
            models.MaterialType,
            models.Product.material_type_id == models.MaterialType.id,
        )
        .outerjoin(
            models.ProductWorkshop,
            models.Product.id == models.ProductWorkshop.product_id,
        )
        .group_by(
            models.Product.id,
            models.Product.name,
            models.Product.article,
            models.Product.min_partner_price,
            models.ProductType.name,
            models.MaterialType.name,
        )
        .order_by(models.ProductType.name, models.Product.name)
    )

    result: List[schemas.ProductCard] = []
    for row in query.all():
        total_hours_num = float(row.total_hours or 0.0)
        total_hours_int = int(ceil(total_hours_num))

        result.append(
            schemas.ProductCard(
                id=row.id,
                product_type=row.product_type,
                name=row.name,
                article=row.article,
                min_partner_price=row.min_partner_price,
                material_type=row.material_type,
                production_time_hours=total_hours_int,
            )
        )
    return result


# =========================================================
# Расчёт количества сырья (JSON API)
# =========================================================

@app.post(
    "/calculate-raw-material",
    response_model=schemas.RawMaterialCalcResult,
)
def calculate_raw_material_endpoint(
    body: schemas.RawMaterialCalcRequest,
    db: Session = Depends(get_db),
):
    """
    Обёртка над сервисным методом расчёта количества сырья.

    Позволяет использовать единый алгоритм расчёта из внешних систем.
    """
    result = services.calculate_raw_material_amount(
        db=db,
        product_type_id=body.product_type_id,
        material_type_id=body.material_type_id,
        quantity=body.quantity,
        param1=body.param1,
        param2=body.param2,
    )
    return schemas.RawMaterialCalcResult(result=result)


# =========================================================
# HTML‑интерфейс (задание 3 и 4)
# =========================================================

@app.get("/", response_class=HTMLResponse)
def root_redirect():
    """
    Корневая страница перенаправляет на основной экран подсистемы.
    """
    return RedirectResponse(url="/ui/products", status_code=status.HTTP_302_FOUND)


# ---------- Продукция: список, добавление, редактирование (HTML) ----------

@app.get("/ui/products", response_class=HTMLResponse)
def ui_products_list(request: Request, db: Session = Depends(get_db)):
    """
    Табличный список продукции с расчётом времени изготовления.
    """
    products = list_product_cards(db=db)
    context = {
        "request": request,
        "products": products,
        "active_page": "products",
        "messages": build_status_messages(request),
    }
    return templates.TemplateResponse("products.html", context)


@app.get("/ui/products/new", response_class=HTMLResponse)
def ui_product_new(request: Request, db: Session = Depends(get_db)):
    """
    Форма добавления новой продукции.
    """
    product_types = db.query(models.ProductType).order_by(models.ProductType.name).all()
    material_types = db.query(models.MaterialType).order_by(models.MaterialType.name).all()

    context = {
        "request": request,
        "active_page": "products",
        "product_types": product_types,
        "material_types": material_types,
        "is_edit": False,
        "form_data": {},
        "field_errors": {},
        "messages": [],
    }
    return templates.TemplateResponse("product_form.html", context)


@app.get("/ui/products/{product_id}/edit", response_class=HTMLResponse)
def ui_product_edit(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Форма редактирования существующей продукции.
    """
    product = db.get(models.Product, product_id)
    if not product:
        return RedirectResponse(
            url="/ui/products?status=product_not_found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    product_types = db.query(models.ProductType).order_by(models.ProductType.name).all()
    material_types = db.query(models.MaterialType).order_by(models.MaterialType.name).all()

    form_data = {
        "id": product.id,
        "name": product.name,
        "article": product.article,
        "product_type_id": product.product_type_id,
        "material_type_id": product.material_type_id,
        "min_partner_price": str(product.min_partner_price).replace(".", ","),
    }

    context = {
        "request": request,
        "active_page": "products",
        "product_types": product_types,
        "material_types": material_types,
        "is_edit": True,
        "form_data": form_data,
        "field_errors": {},
        "messages": [],
    }
    return templates.TemplateResponse("product_form.html", context)


@app.post("/ui/products/save", response_class=HTMLResponse)
async def ui_product_save(
    request: Request,
    product_id: str = Form(default="", alias="id"),
    name: str = Form(default=""),
    article: str = Form(default=""),
    product_type_id: str = Form(default=""),
    material_type_id: str = Form(default=""),
    min_partner_price: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """
    Обработчик сохранения продукции (создание или обновление).
    Выполняет серверную валидацию и показывает понятные сообщения об ошибках.
    """
    is_edit = bool((product_id or "").strip())
    field_errors: Dict[str, str] = {}

    name_clean = (name or "").strip()
    article_clean = (article or "").strip()

    if not name_clean:
        field_errors["name"] = "Укажите наименование продукции."

    if not article_clean:
        field_errors["article"] = "Укажите артикул продукции."

    # Валидация справочников
    pt_id = parse_positive_int(product_type_id, field_errors, "product_type_id", "Тип продукции")
    mt_id = parse_positive_int(material_type_id, field_errors, "material_type_id", "Основной материал")

    # Валидация цены
    price = parse_price_ru(min_partner_price, field_errors, "min_partner_price")

    # Пересобираем данные формы для повторного вывода
    form_data = {
        "id": (product_id or "").strip(),
        "name": name_clean,
        "article": article_clean,
        "product_type_id": pt_id,
        "material_type_id": mt_id,
        "min_partner_price": min_partner_price,
    }

    if field_errors:
        product_types = db.query(models.ProductType).order_by(models.ProductType.name).all()
        material_types = db.query(models.MaterialType).order_by(models.MaterialType.name).all()

        context = {
            "request": request,
            "active_page": "products",
            "product_types": product_types,
            "material_types": material_types,
            "is_edit": is_edit,
            "form_data": form_data,
            "field_errors": field_errors,
            "messages": [
                {
                    "type": "error",
                    "title": "Ошибка ввода данных",
                    "text": "Исправьте ошибки в форме и повторите попытку.",
                }
            ],
        }
        return templates.TemplateResponse(
            "product_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if is_edit:
        try:
            product_pk = int(product_id)
        except ValueError:
            return RedirectResponse(
                url="/ui/products?status=product_not_found",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        product = db.get(models.Product, product_pk)
        if not product:
            return RedirectResponse(
                url="/ui/products?status=product_not_found",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        product.name = name_clean
        product.article = article_clean
        product.product_type_id = pt_id
        product.material_type_id = mt_id
        product.min_partner_price = price
    else:
        product = models.Product(
            name=name_clean,
            article=article_clean,
            product_type_id=pt_id,
            material_type_id=mt_id,
            min_partner_price=price,
        )
        db.add(product)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Нарушение уникальности (артикул или название)
        product_types = db.query(models.ProductType).order_by(models.ProductType.name).all()
        material_types = db.query(models.MaterialType).order_by(models.MaterialType.name).all()

        field_errors["__all__"] = (
            "Продукт с таким артикулом или наименованием уже существует. "
            "Измените значения и попробуйте ещё раз."
        )
        context = {
            "request": request,
            "active_page": "products",
            "product_types": product_types,
            "material_types": material_types,
            "is_edit": is_edit,
            "form_data": form_data,
            "field_errors": field_errors,
            "messages": [
                {
                    "type": "error",
                    "title": "Дублирование данных",
                    "text": field_errors["__all__"],
                }
            ],
        }
        return templates.TemplateResponse(
            "product_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    status_code_param = "product_updated" if is_edit else "product_created"
    return RedirectResponse(
        url=f"/ui/products?status={status_code_param}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/ui/products/{product_id}/delete")
def ui_product_delete(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Удаление продукции с предварительным подтверждением на стороне клиента.
    """
    product = db.get(models.Product, product_id)
    if not product:
        return RedirectResponse(
            url="/ui/products?status=product_not_found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(product)
    db.commit()

    return RedirectResponse(
        url="/ui/products?status=product_deleted",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get(
    "/ui/products/{product_id}/workshops",
    response_class=HTMLResponse,
)
def ui_product_workshops(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Страница списка цехов, участвующих в изготовлении конкретного продукта.
    Показывает название цеха, требуемое количество сотрудников
    и время нахождения изделия в каждом цехе.
    """
    product = db.get(models.Product, product_id)
    if not product:
        return RedirectResponse(
            url="/ui/products?status=product_not_found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Получаем связанные с продуктом цеха с сортировкой по названию цеха
    links = (
        db.query(models.ProductWorkshop)
        .join(models.Workshop)
        .filter(models.ProductWorkshop.product_id == product_id)
        .order_by(models.Workshop.name)
        .all()
    )

    total_hours_float = sum(float(link.production_time_hours or 0.0) for link in links)
    total_hours_int = int(ceil(total_hours_float))

    context = {
        "request": request,
        "active_page": "products",
        "product": product,
        "links": links,
        "total_hours": total_hours_int,
        "messages": build_status_messages(request),
    }
    return templates.TemplateResponse("product_workshops.html", context)


# ---------- Цеха: список, добавление, редактирование (HTML) ----------

@app.get("/ui/workshops", response_class=HTMLResponse)
def ui_workshops_list(request: Request, db: Session = Depends(get_db)):
    workshops = db.query(models.Workshop).order_by(models.Workshop.name).all()
    context = {
        "request": request,
        "workshops": workshops,
        "active_page": "workshops",
        "messages": build_status_messages(request),
    }
    return templates.TemplateResponse("workshops.html", context)


@app.get("/ui/workshops/new", response_class=HTMLResponse)
def ui_workshop_new(request: Request, db: Session = Depends(get_db)):
    workshop_types = (
        db.query(models.WorkshopType)
        .order_by(models.WorkshopType.name)
        .all()
    )
    context = {
        "request": request,
        "active_page": "workshops",
        "workshop_types": workshop_types,
        "is_edit": False,
        "form_data": {},
        "field_errors": {},
        "messages": [],
    }
    return templates.TemplateResponse("workshop_form.html", context)


@app.get("/ui/workshops/{workshop_id}/edit", response_class=HTMLResponse)
def ui_workshop_edit(
    workshop_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    workshop = db.get(models.Workshop, workshop_id)
    if not workshop:
        return RedirectResponse(
            url="/ui/workshops?status=workshop_not_found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    workshop_types = (
        db.query(models.WorkshopType)
        .order_by(models.WorkshopType.name)
        .all()
    )

    form_data = {
        "id": workshop.id,
        "name": workshop.name,
        "workshop_type_id": workshop.workshop_type_id,
        "workers_required": workshop.workers_required,
    }

    context = {
        "request": request,
        "active_page": "workshops",
        "workshop_types": workshop_types,
        "is_edit": True,
        "form_data": form_data,
        "field_errors": {},
        "messages": [],
    }
    return templates.TemplateResponse("workshop_form.html", context)


@app.post("/ui/workshops/save", response_class=HTMLResponse)
async def ui_workshop_save(
    request: Request,
    workshop_id: str = Form(default="", alias="id"),
    name: str = Form(default=""),
    workshop_type_id: str = Form(default=""),
    workers_required: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """
    Сохранение информации о цехе.
    """
    is_edit = bool((workshop_id or "").strip())
    field_errors: Dict[str, str] = {}

    name_clean = (name or "").strip()
    if not name_clean:
        field_errors["name"] = "Укажите название цеха."

    wt_id = parse_positive_int(
        workshop_type_id,
        field_errors,
        "workshop_type_id",
        "Тип цеха",
    )
    workers = parse_positive_int(
        workers_required,
        field_errors,
        "workers_required",
        "Количество сотрудников",
    )

    form_data = {
        "id": (workshop_id or "").strip(),
        "name": name_clean,
        "workshop_type_id": wt_id,
        "workers_required": workers_required,
    }

    if field_errors:
        workshop_types = (
            db.query(models.WorkshopType)
            .order_by(models.WorkshopType.name)
            .all()
        )
        context = {
            "request": request,
            "active_page": "workshops",
            "workshop_types": workshop_types,
            "is_edit": is_edit,
            "form_data": form_data,
            "field_errors": field_errors,
            "messages": [
                {
                    "type": "error",
                    "title": "Ошибка ввода данных",
                    "text": "Исправьте ошибки в форме и повторите попытку.",
                }
            ],
        }
        return templates.TemplateResponse(
            "workshop_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if is_edit:
        try:
            ws_pk = int(workshop_id)
        except ValueError:
            return RedirectResponse(
                url="/ui/workshops?status=workshop_not_found",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        workshop = db.get(models.Workshop, ws_pk)
        if not workshop:
            return RedirectResponse(
                url="/ui/workshops?status=workshop_not_found",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        workshop.name = name_clean
        workshop.workshop_type_id = wt_id
        workshop.workers_required = workers
    else:
        workshop = models.Workshop(
            name=name_clean,
            workshop_type_id=wt_id,
            workers_required=workers,
        )
        db.add(workshop)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        workshop_types = (
            db.query(models.WorkshopType)
            .order_by(models.WorkshopType.name)
            .all()
        )
        field_errors["__all__"] = (
            "Цех с таким названием уже существует. "
            "Измените название и попробуйте ещё раз."
        )
        context = {
            "request": request,
            "active_page": "workshops",
            "workshop_types": workshop_types,
            "is_edit": is_edit,
            "form_data": form_data,
            "field_errors": field_errors,
            "messages": [
                {
                    "type": "error",
                    "title": "Дублирование данных",
                    "text": field_errors["__all__"],
                }
            ],
        }
        return templates.TemplateResponse(
            "workshop_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    status_param = "workshop_updated" if is_edit else "workshop_created"
    return RedirectResponse(
        url=f"/ui/workshops?status={status_param}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/ui/workshops/{workshop_id}/delete")
def ui_workshop_delete(
    workshop_id: int,
    db: Session = Depends(get_db),
):
    workshop = db.get(models.Workshop, workshop_id)
    if not workshop:
        return RedirectResponse(
            url="/ui/workshops?status=workshop_not_found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(workshop)
    db.commit()

    return RedirectResponse(
        url="/ui/workshops?status=workshop_deleted",
        status_code=status.HTTP_303_SEE_OTHER,
    )

