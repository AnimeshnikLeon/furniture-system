from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class ProductType(Base):
    __tablename__ = "product_type"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    coefficient = Column(Numeric(6, 2), nullable=False)

    products = relationship("Product", back_populates="product_type")


class MaterialType(Base):
    __tablename__ = "material_type"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    loss_percent = Column(Numeric(5, 4), nullable=False)

    products = relationship("Product", back_populates="material_type")


class WorkshopType(Base):
    __tablename__ = "workshop_type"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    workshops = relationship("Workshop", back_populates="workshop_type")


class Workshop(Base):
    __tablename__ = "workshop"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    workshop_type_id = Column(Integer, ForeignKey("workshop_type.id"), nullable=False)
    workers_required = Column(Integer, nullable=False)

    workshop_type = relationship("WorkshopType", back_populates="workshops")
    product_links = relationship("ProductWorkshop", back_populates="workshop")


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    article = Column(String(50), unique=True, nullable=False)
    product_type_id = Column(Integer, ForeignKey("product_type.id"), nullable=False)
    material_type_id = Column(Integer, ForeignKey("material_type.id"), nullable=False)
    min_partner_price = Column(Numeric(12, 2), nullable=False)

    product_type = relationship("ProductType", back_populates="products")
    material_type = relationship("MaterialType", back_populates="products")
    workshops = relationship("ProductWorkshop", back_populates="product")


class ProductWorkshop(Base):
    __tablename__ = "product_workshop"
    __table_args__ = (
        UniqueConstraint("product_id", "workshop_id", name="uq_product_workshop"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    workshop_id = Column(Integer, ForeignKey("workshop.id"), nullable=False)
    production_time_hours = Column(Numeric(6, 2), nullable=False)

    product = relationship("Product", back_populates="workshops")
    workshop = relationship("Workshop", back_populates="product_links")
