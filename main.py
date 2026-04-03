from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import engine, Base

from api.users import router as user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который выполнится при запуске
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # Приложение запущено
    # Код после yield выполнится при выключении (необязательно)

app = FastAPI(title="My Shop Backend", lifespan=lifespan)

# Подключаем роуты
app.include_router(user_router, prefix="/api/v1", tags=["users"])

@app.get("/")
def read_root():
    return {"message": "Welcome to My Shop API!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)