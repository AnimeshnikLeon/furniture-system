from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ProductTypeOut(BaseModel):
    id: int
    name: str
    coefficient: Decimal

    class Config:
        from_attributes = True


class MaterialTypeOut(BaseModel):
    id: int
    name: str
    loss_percent: Decimal

    class Config:
        from_attributes = True


class WorkshopTypeOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# ---------- Workshops ----------

class WorkshopBase(BaseModel):
    name: str
    workshop_type_id: int
    workers_required: int


class WorkshopCreate(WorkshopBase):
    pass


class WorkshopUpdate(BaseModel):
    name: Optional[str] = None
    workshop_type_id: Optional[int] = None
    workers_required: Optional[int] = None


class WorkshopOut(WorkshopBase):
    id: int
    workshop_type: WorkshopTypeOut

    class Config:
        from_attributes = True


# ---------- Products ----------

class ProductBase(BaseModel):
    name: str
    article: str
    product_type_id: int
    material_type_id: int
    min_partner_price: Decimal


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    product_type_id: Optional[int] = None
    material_type_id: Optional[int] = None
    min_partner_price: Optional[Decimal] = None


class ProductOut(ProductBase):
    id: int
    product_type: ProductTypeOut
    material_type: MaterialTypeOut

    class Config:
        from_attributes = True


# ---------- Product–Workshop link ----------

class ProductWorkshopBase(BaseModel):
    workshop_id: int
    production_time_hours: Decimal


class ProductWorkshopCreate(ProductWorkshopBase):
    pass


class ProductWorkshopUpdate(BaseModel):
    production_time_hours: Optional[Decimal] = None


class ProductWorkshopOut(BaseModel):
    workshop: WorkshopOut
    production_time_hours: Decimal

    class Config:
        from_attributes = True


# ---------- Product card with total time ----------

class ProductCard(BaseModel):
    id: int
    product_type: str
    name: str
    article: str
    min_partner_price: Decimal
    material_type: str
    production_time_hours: int

    class Config:
        from_attributes = True


# ---------- Raw material calculation ----------

class RawMaterialCalcRequest(BaseModel):
    product_type_id: int
    material_type_id: int
    quantity: int
    param1: float
    param2: float


class RawMaterialCalcResult(BaseModel):
    result: int
