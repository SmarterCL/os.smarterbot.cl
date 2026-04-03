from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ValidationRequest(BaseModel):
    """Request to validate a product (food, vehicle, etc.)"""
    id_objeto: str = Field(..., description="Unique object ID (QR code)")
    producto: str = Field(..., description="Product name")
    peso_gramos: Optional[int] = Field(None, description="Weight in grams")
    precio: Optional[float] = Field(None, description="Price in CLP")
    ubicacion: Optional[str] = Field(None, description="Geolocation")
    imagen_url: Optional[str] = Field(None, description="Photo URL for AI analysis")
    categoria: Optional[str] = Field("food", description="Category: food, vehicle, other")


class ScoreResult(BaseModel):
    """AI scoring result"""
    score: Optional[float] = Field(None, ge=0, le=10, description="Score 0-10")
    recomendacion: Optional[str] = Field(None, description="Recommendation text")
    observaciones: list[str] = Field(default_factory=list, description="Observations/risks")


class ValidationResponse(BaseModel):
    """Response from validation endpoint"""
    id_objeto: str
    producto: str
    score: Optional[float] = None
    recomendacion: Optional[str] = None
    observaciones: list[str] = Field(default_factory=list)
    status: str = Field(..., description="pending, completed, error")
    validator_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    validator: str
    uptime: Optional[str] = None


class ProductCreate(BaseModel):
    """Create a new product entry"""
    nombre: str
    categoria: str = "food"
    precio: float
    peso_gramos: Optional[int] = None
    descripcion: Optional[str] = None


class ProductResponse(BaseModel):
    """Product entry response"""
    id: int
    nombre: str
    categoria: str
    precio: float
    peso_gramos: Optional[int] = None
    descripcion: Optional[str] = None
    creado_en: datetime
