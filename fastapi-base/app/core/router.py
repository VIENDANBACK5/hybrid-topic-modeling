from fastapi import APIRouter
from app.api import api_healthcheck

router = APIRouter()

router.include_router(api_healthcheck.router, tags=["[Current] Health Check"])
