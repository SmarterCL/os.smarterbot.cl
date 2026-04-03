from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from ..models.schemas import ProductCreate, ProductResponse

router = APIRouter(prefix="/api/products", tags=["productos"])
_products = []
_next_id = 1

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    global _next_id
    entry = {"id": _next_id, "nombre": product.nombre, "categoria": product.categoria,
             "precio": product.precio, "peso_gramos": product.peso_gramos,
             "descripcion": product.descripcion, "creado_en": datetime.utcnow()}
    _products.append(entry)
    _next_id += 1
    return entry

@router.get("/", response_model=list[ProductResponse])
async def list_products(categoria: Optional[str] = None):
    if categoria:
        return [p for p in _products if p["categoria"] == categoria]
    return _products

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    for p in _products:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")
