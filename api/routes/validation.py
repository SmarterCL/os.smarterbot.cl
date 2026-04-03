from fastapi import APIRouter, HTTPException
from ..models.schemas import ValidationRequest, ValidationResponse
from ..services.validator import ValidatorService

router = APIRouter(prefix="/api", tags=["validador"])
validator_service = ValidatorService()

@router.post("/validar", response_model=ValidationResponse)
async def validar_producto(req: ValidationRequest):
    payload = req.model_dump()
    result = await validator_service.validate(payload)
    return ValidationResponse(
        id_objeto=result.get("id_objeto", req.id_objeto),
        producto=result.get("producto", req.producto),
        score=result.get("score"),
        recomendacion=result.get("recomendacion"),
        observaciones=result.get("observaciones", []),
        status=result.get("status", "pending"),
    )

@router.get("/validar/{id_objeto}")
async def get_validacion(id_objeto: str):
    return {"id_objeto": id_objeto, "status": "not_found"}
