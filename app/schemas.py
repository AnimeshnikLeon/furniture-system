from decimal import Decimal
from typing import List, Optional

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


class WorkshopBase(BaseModel):
    name: str
    workshop_type_id: int
    workers_required: int


class WorkshopOut(WorkshopBase):
    id: int
    workshop_type: WorkshopTypeOut

    class Config:
        from_attributes = True


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


class ProductWorkshopOut(BaseModel):
    workshop: WorkshopOut
    production_time_hours: Decimal

    class Config:
        from_attributes = True
