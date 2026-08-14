from __future__ import annotations
from fastapi import Depends, FastAPI, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_session
from app.models import Product
from app.schemas import ProductCreate, ProductRead
app = FastAPI(title="Model Archive API", version="0.2.0")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
@app.post("/api/v1/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, session: Session = Depends(get_session)) -> Product:
    product = Product(**payload.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product
@app.get("/api/v1/products", response_model=list[ProductRead])
def list_products(search: str | None = None, limit: int = Query(default=100, le=500), session: Session = Depends(get_session)) -> list[Product]:
    statement = select(Product).order_by(Product.kit_name).limit(limit)
    if search:
        statement = statement.where(Product.kit_name.ilike(f"%{search}%"))
    return list(session.scalars(statement))
