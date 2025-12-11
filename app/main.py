from decimal import ROUND_CEILING
from pathlib import Path
from math import ceil
from typing import List

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    Request,
    status,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas
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
# Цеха (CRUD)
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
# Продукция (CRUD)
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
# Связь продукт–цех (маршрут изготовления)
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
# Карточки продукции с расчётом времени
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
                0.0,  # чтобы тип всегда был числовой
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
        # row.total_hours может быть Decimal, float или int -> приводим к float
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
# Главная HTML-страница (для задания 3, но пусть уже будет)
# =========================================================

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    products = list_product_cards(db=db)
    return templates.TemplateResponse(
        "products.html",
        {"request": request, "products": products},
    )
