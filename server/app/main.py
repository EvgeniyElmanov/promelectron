import asyncio
import os
from contextlib import asynccontextmanager
from logging import getLogger

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import create_async_engine

from server.app.api.admin import router as admin_router
from server.app.api.auth import router as auth_router
from server.app.api.cart import router as cart_router
from server.app.api.categories import router as categories_router
from server.app.api.favorites import router as favorites_router
from server.app.api.orders import router as orders_router
from server.app.api.products import router as products_router
from server.app.api.reviews import router as reviews_router
from server.app.api.users import router as users_router
from server.app.db.database import DATABASE_URL

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(DATABASE_URL)

    # Применяем миграции Alembic при старте
    alembic_cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
    if os.path.exists(alembic_cfg_path):
        try:
            await asyncio.to_thread(_run_alembic_migrations, alembic_cfg_path)
        except Exception as e:
            logger.warning("Alembic migration skipped: %s", e)

    yield
    await engine.dispose()


def _run_alembic_migrations(cfg_path: str) -> None:
    alembic_cfg = Config(cfg_path)
    command.upgrade(alembic_cfg, "head")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Подключаем все роутеры
# categories ДО products, иначе /products/{id} перехватит /categories"
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(admin_router, prefix="/api/v1", tags=["admin"])
app.include_router(categories_router, prefix="/api/v1", tags=["categories"])
app.include_router(products_router, prefix="/api/v1", tags=["products"])
app.include_router(cart_router, prefix="/api/v1", tags=["cart"])
app.include_router(orders_router, prefix="/api/v1", tags=["orders"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(reviews_router, prefix="/api/v1", tags=["reviews"])
app.include_router(favorites_router, prefix="/api/v1", tags=["favorites"])


@app.get("/")
async def read_root():
    return {"message": "Welcome to My Shop Backend!"}
