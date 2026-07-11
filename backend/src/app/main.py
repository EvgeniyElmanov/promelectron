import asyncio
import json
import os
from contextlib import asynccontextmanager
from logging import getLogger

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import create_async_engine

from src.app.api.admin import router as admin_router
from src.app.api.analytics import router as analytics_router
from src.app.api.auth import router as auth_router
from src.app.api.cart import router as cart_router
from src.app.api.categories import router as categories_router
from src.app.api.cdek import router as cdek_router
from src.app.api.delivery_methods import router as delivery_methods_router
from src.app.api.favorites import router as favorites_router
from src.app.api.notifications import router as notifications_router
from src.app.api.onec import router as onec_router
from src.app.api.orders import router as orders_router
from src.app.api.payments import router as payments_router
from src.app.api.products import router as products_router
from src.app.api.recipients import router as recipients_router
from src.app.api.reviews import router as reviews_router
from src.app.api.seed import router as seed_router
from src.app.api.users import router as users_router
from src.app.api.ws import router as ws_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.app.db.database import DATABASE_URL
from src.app.services.storage_service import storage
from src.app.utils.rate_limiter import limiter

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


_default_cors = '["http://localhost:5173", "http://127.0.0.1:5173"]'
_cors_origins = json.loads(os.getenv("CORS_ORIGINS", _default_cors))

app = FastAPI(lifespan=lifespan)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/uploads/{path:path}")
async def serve_upload(path: str, size: str | None = None):
    if size:
        if size not in ("small", "medium", "large"):
            raise HTTPException(status_code=400, detail="Invalid size. Allowed: small, medium, large")
        base, _ = os.path.splitext(path)
        path = f"{base}_{size}.webp"

    url = storage.get_url(path)
    if url.startswith("http"):
        return RedirectResponse(url=url, status_code=307)
    # Local fallback — serve from filesystem
    filepath = os.path.join("uploads", path)
    if os.path.exists(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="File not found")


# Подключаем все роутеры
# categories ДО products, иначе /products/{id} перехватит /categories"
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(admin_router, prefix="/api/v1", tags=["admin"])
app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
app.include_router(categories_router, prefix="/api/v1", tags=["categories"])
app.include_router(products_router, prefix="/api/v1", tags=["products"])
app.include_router(recipients_router, prefix="/api/v1", tags=["recipients"])
app.include_router(cart_router, prefix="/api/v1", tags=["cart"])
app.include_router(orders_router, prefix="/api/v1", tags=["orders"])
app.include_router(payments_router, prefix="/api/v1", tags=["payments"])
app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])
app.include_router(onec_router, prefix="/api/v1", tags=["onec"])
app.include_router(ws_router)
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(reviews_router, prefix="/api/v1", tags=["reviews"])
app.include_router(favorites_router, prefix="/api/v1", tags=["favorites"])
app.include_router(seed_router, prefix="/api/v1", tags=["seed"])
app.include_router(cdek_router, prefix="/api/v1", tags=["cdek"])
app.include_router(delivery_methods_router, prefix="/api/v1", tags=["delivery-methods"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def read_root():
    return {"message": "Welcome to My Shop Backend!"}
