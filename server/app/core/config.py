import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    database_url: str


settings = Settings(
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"),
    algorithm=os.getenv("ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    database_url=os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost/shop_db"
    ),
)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

