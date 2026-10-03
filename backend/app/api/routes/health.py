from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check():
    return {
        "status": "healthy",
        "service": "Indian Vehicle Number Plate Recognition API",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }
