from fastapi import APIRouter

from .nodes import router as nodes_router

router = APIRouter()

router.include_router(nodes_router, prefix="/nodes", tags=["nodes"])
