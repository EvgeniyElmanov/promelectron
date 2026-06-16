from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.db.database import get_db
from src.app.services.cdek_client import CdekAPIError, CdekClient
from src.app.services.cdek_service import CdekService
from src.app.utils.auth import get_current_active_user
from src.app.utils.rate_limiter import conditional_limit

router = APIRouter(prefix="/cdek", tags=["cdek"])


class CalculateDeliveryRequest(BaseModel):
    items: list[dict[str, Any]]
    supplier_id: int
    to_location: dict[str, Any] | None = None
    delivery_point: str | None = None


class CalculateDeliveryResponse(BaseModel):
    tariffs: list[dict[str, Any]]


@router.post("/calculate/", response_model=CalculateDeliveryResponse)
@conditional_limit("30/minute")
async def calculate_delivery(
    request: Request,
    data: CalculateDeliveryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Calculate CDEK delivery tariffs for cart items."""
    try:
        tariffs = await CdekService.calculate_delivery(
            db=db,
            items=data.items,
            supplier_id=data.supplier_id,
            to_location=data.to_location,
            delivery_point=data.delivery_point,
        )
    except CdekAPIError as exc:
        raise HTTPException(status_code=502, detail=f"CDEK API error: {exc}") from exc
    return CalculateDeliveryResponse(tariffs=tariffs)


@router.get("/pvz/")
@conditional_limit("30/minute")
async def get_delivery_points(
    request: Request,
    city_code: int | None = None,
    postal_code: str | None = None,
):
    """Get CDEK delivery points (PVZ / postamats)."""
    params: dict[str, Any] = {}
    if city_code:
        params["city_code"] = city_code
    if postal_code:
        params["postal_code"] = postal_code

    client = CdekClient()
    try:
        result = await client.get_delivery_points(params)
    except CdekAPIError as exc:
        raise HTTPException(status_code=502, detail=f"CDEK API error: {exc}") from exc
    finally:
        await client.close()
    return result


@router.get("/suggest-cities/")
@conditional_limit("30/minute")
async def suggest_cities(
    request: Request,
    name: str,
    country_code: str = "RU",
):
    """Suggest cities by name via CDEK API."""
    client = CdekClient()
    try:
        result = await client.suggest_cities(name, country_code)
    except CdekAPIError as exc:
        raise HTTPException(status_code=502, detail=f"CDEK API error: {exc}") from exc
    finally:
        await client.close()
    return result


@router.post("/webhooks/cdek/")
async def cdek_webhook(
    request: Request,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Incoming webhook from CDEK."""
    if settings.cdek_test_mode:
        # In test mode CDEK does not send real webhooks; accept for debugging
        pass

    event_type = payload.get("type")
    if event_type == "ORDER_STATUS":
        try:
            await CdekService.handle_order_status_webhook(payload, db)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to process webhook: {exc}") from exc

    return {"status": "ok"}


@router.post("/orders/{order_id}/resync/")
async def resync_cdek_order(
    request: Request,
    order_id: int,
    current_user: Any = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin/debug endpoint to retry CDEK order creation."""
    from src.app.services.cdek_tasks import create_cdek_order_task

    create_cdek_order_task.delay(order_id)
    return {"status": "queued", "order_id": order_id}
