from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pathlib import Path

from .database import SessionLocal
from . import models, schemas

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


@app.get("/workshops", response_model=List[schemas.WorkshopOut])
def list_workshops(db: Session = Depends(get_db)):
    return db.query(models.Workshop).all()


@app.get("/products", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()


@app.get("/product-cards", response_model=List[schemas.ProductCard])
def list_product_cards(db: Session = Depends(get_db)):
    query = (
        db.query(
            models.Product.id.label("id"),
            models.Product.name.label("name"),
            models.Product.article.label("article"),
            models.Product.min_partner_price.label("min_partner_price"),
            models.ProductType.name.label("product_type"),
            models.MaterialType.name.label("material_type"),
            func.coalesce(func.sum(models.ProductWorkshop.production_time_hours), 0).label(
                "total_hours"
            ),
        )
        .join(models.ProductType, models.Product.product_type_id == models.ProductType.id)
        .join(models.MaterialType, models.Product.material_type_id == models.MaterialType.id)
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

    result = []
    for row in query.all():
        # row.total_hours - Decimal; округляем вверх, получаем int
        total_hours = int((row.total_hours.to_integral_value(rounding="ROUND_CEILING")))
        result.append(
            schemas.ProductCard(
                id=row.id,
                product_type=row.product_type,
                name=row.name,
                article=row.article,
                min_partner_price=row.min_partner_price,
                material_type=row.material_type,
                production_time_hours=total_hours,
            )
        )

    return result


@app.post("/products", response_model=schemas.ProductOut)
def create_product(prod: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_prod = models.Product(**prod.dict())
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    return db_prod


@app.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, upd: schemas.ProductUpdate, db: Session = Depends(get_db)):
    db_prod = db.get(models.Product, product_id)
    if not db_prod:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in upd.dict(exclude_unset=True).items():
        setattr(db_prod, field, value)
    db.commit()
    db.refresh(db_prod)
    return db_prod


@app.get("/products/{product_id}/workshops", response_model=List[schemas.ProductWorkshopOut])
def get_product_workshops(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.workshops

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    products = list_product_cards(db=db)
    return templates.TemplateResponse(
        "products.html",
        {"request": request, "products": products}
    )
