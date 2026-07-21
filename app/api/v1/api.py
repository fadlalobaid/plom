from fastapi import APIRouter

from app.api.v1.endpoints import auth, diagnosis, doctors, patients, statistics, xray_images

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(doctors.router)
api_router.include_router(patients.router)
api_router.include_router(xray_images.router)
api_router.include_router(diagnosis.router)
api_router.include_router(statistics.router)
