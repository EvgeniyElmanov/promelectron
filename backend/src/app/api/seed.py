import hmac

from fastapi import APIRouter, HTTPException, Request

from seed_data import seed_data
from src.app.core.config import settings

router = APIRouter()

# Секрет читается из env SEED_SECRET через settings (F006/S001, issue #147).
# Атрибут оставлен для обратной совместимости импортов (тесты).
SEED_SECRET = settings.seed_secret


@router.post("/seed")
async def run_seed(request: Request):
    """Run seed_data.py to populate test DB. Protected by secret header.

    Prod-guard: если SEED_SECRET не задан в окружении (prod), endpoint
    всегда отвечает 403 — seed невозможен. Сравнение — через
    hmac.compare_digest (защита от timing attack).
    """
    expected = settings.seed_secret
    secret = request.headers.get("x-seed-secret")
    if not expected or not secret or not hmac.compare_digest(secret, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        await seed_data()
        return {"status": "ok", "message": "Seed completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
