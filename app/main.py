from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .database import SessionLocal
from . import models, schemas

app = FastAPI(title="Furniture Production System")


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
