from fastapi import APIRouter
from app.config import get_available_models, DEFAULT_MODEL

router = APIRouter()


@router.get("")
def list_models():
    return {
        "available": get_available_models(),
        "default": DEFAULT_MODEL,
    }
