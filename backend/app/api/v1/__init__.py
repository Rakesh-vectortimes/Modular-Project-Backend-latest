from fastapi import APIRouter

from app.api.v1 import auth, component_definitions, page_data, pages, software, uploads, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(component_definitions.router)
api_router.include_router(software.router)
api_router.include_router(pages.router)
api_router.include_router(page_data.router)
api_router.include_router(uploads.router)
