from fastapi import APIRouter
from app.api.endpoints import router as endpoints_router

router = APIRouter()

# Include the endpoints router containing all Phase 3 routes
router.include_router(endpoints_router)

@router.get("/")
async def root():
    return {"message": "API is running"}
