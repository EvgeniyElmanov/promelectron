from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
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


class WidgetAction(str, Enum):
    offices = "offices"
    calculate = "calculate"


class WidgetOfficesParams(BaseModel):
    action: WidgetAction
    city_code: int | None = None
    postal_code: str | None = None
    country_code: str | None = None
    type: str | None = None


class WidgetCalculateRequest(BaseModel):
    action: WidgetAction
    type: int | None = None
    date: str | None = None
    currency: int | str | None = None
    lang: str | None = None
    from_location: dict[str, Any] | None = None
    to_location: dict[str, Any] | int | None = None
    services: list[dict[str, Any]] | None = None
    packages: list[dict[str, Any]] = Field(default_factory=list)
    delivery_point: str | None = None


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


@router.get("/widget-service/")
@router.post("/widget-service/")
@conditional_limit("1000/minute")
async def cdek_widget_service(request: Request):
    """Public proxy for the official CDEK widget service.

    Supports ``action=offices`` (GET) and ``action=calculate`` (POST),
    forwarding read-only requests to the CDEK API using configured credentials.
    """
    action = request.query_params.get("action")
    body: dict[str, Any] = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
    if not action:
        action = body.get("action")

    try:
        validated_action = WidgetAction(action)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Unknown or missing action") from exc

    if validated_action == WidgetAction.offices:
        params = {
            k: v
            for k, v in request.query_params.items()
            if k in WidgetOfficesParams.model_fields and k != "action"
        }
        try:
            WidgetOfficesParams(action=validated_action, **params)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid offices parameters: {exc}") from exc

        client = CdekClient()
        try:
            result = await client.get_delivery_points(params)
        except CdekAPIError as exc:
            raise HTTPException(status_code=502, detail=f"CDEK API error: {exc}") from exc
        finally:
            await client.close()
        return JSONResponse(content=result, headers={"X-Service-Version": "3.x"})

    if validated_action == WidgetAction.calculate:
        if request.method != "POST":
            raise HTTPException(status_code=405, detail="calculate requires POST")

        allowed_fields = set(WidgetCalculateRequest.model_fields) - {"action"}
        payload = {k: v for k, v in body.items() if k in allowed_fields}
        try:
            WidgetCalculateRequest(action=validated_action, **payload)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid calculate body: {exc}") from exc

        client = CdekClient()
        try:
            result = await client.calculate_tariffs(payload)
        except CdekAPIError as exc:
            raise HTTPException(status_code=502, detail=f"CDEK API error: {exc}") from exc
        finally:
            await client.close()
        return JSONResponse(content=result, headers={"X-Service-Version": "3.x"})

    raise HTTPException(status_code=400, detail="Unknown or missing action")
