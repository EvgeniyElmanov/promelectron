from fastapi import APIRouter, HTTPException, Request

from seed_data import seed_data

router = APIRouter()

SEED_SECRET = "promelectron-test-seed-2024"


@router.post("/seed")
async def run_seed(request: Request):
    """Run seed_data.py to populate test DB. Protected by simple secret header."""
    secret = request.headers.get("x-seed-secret")
    if secret != SEED_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        await seed_data()
        return {"status": "ok", "message": "Seed completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
