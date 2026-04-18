from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine

from database import DATABASE_URL, Base
from api.users import router as users_router
from api.products import router as products_router
from api.categories import router as categories_router
from api.cart import router as cart_router  # ← Добавь эту строку

@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"message": "Welcome to My Shop Backend!"}

app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(products_router, prefix="/api/v1", tags=["products"])
app.include_router(categories_router, prefix="/api/v1", tags=["categories"])
app.include_router(cart_router, prefix="/api/v1", tags=["cart"])  # ← Добавь эту строку

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
