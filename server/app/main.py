from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine

from server.app.api.cart import router as cart_router
from server.app.api.categories import router as categories_router
from server.app.api.orders import router as orders_router
from server.app.api.products import router as products_router
from server.app.api.users import router as users_router
from server.app.api.auth import router as auth_router
from server.app.db.database import DATABASE_URL, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Подключаем все роутеры — ТОЛЬКО ОДИН РАЗ
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(products_router, prefix="/api/v1", tags=["products"])
app.include_router(categories_router, prefix="/api/v1", tags=["categories"])
app.include_router(cart_router, prefix="/api/v1", tags=["cart"])
app.include_router(orders_router, prefix="/api/v1", tags=["orders"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])


@app.get("/")
async def read_root():
    return {"message": "Welcome to My Shop Backend!"}

