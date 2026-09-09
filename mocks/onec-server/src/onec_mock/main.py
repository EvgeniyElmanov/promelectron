"""FastAPI-приложение OData мок-сервера 1С:УНФ поверх схемы onec (issue #227)."""

import base64
import binascii
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from onec_mock.config import settings
from onec_mock.db import get_session
from onec_mock.images import placeholder_jpeg, warmup_pool
from onec_mock.odata import ENTITIES, FilterError, query_entity

logger = logging.getLogger("onec_mock")

DEFAULT_TOP = 100

# Catalog_НоменклатураПрисоединенныеФайлы(guid'<ref_key>')/$value
_FILE_VALUE_RE = re.compile(
    r"^Catalog_НоменклатураПрисоединенныеФайлы\(guid'(?P<ref_key>[^']+)'\)/\$value$"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=settings.log_level)
    warmup_pool()
    logger.info(
        "onec-mock starting (schema=%s, base_path=%s)", settings.onec_mock_schema, settings.base_path
    )
    yield
    logger.info("onec-mock stopped")


app = FastAPI(title="1C OData Mock Server", lifespan=lifespan)


DbSession = Annotated[AsyncSession, Depends(get_session)]


def odata_error(status_code: int, code: str, value: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"odata.error": {"code": code, "message": {"lang": "ru", "value": value}}},
    )


def check_auth(request: Request) -> JSONResponse | None:
    """Basic Auth по ONEC_MOCK_LOGIN/ONEC_MOCK_PASSWORD; None — ок, иначе 401."""
    header = request.headers.get("authorization", "")
    if header.startswith("Basic "):
        try:
            decoded = base64.b64decode(header[6:]).decode()
        except (binascii.Error, UnicodeDecodeError, ValueError):
            decoded = ""
        if decoded == f"{settings.login}:{settings.password}":
            return None
    response = odata_error(401, "1", "Ошибка аутентификации: неверный логин или пароль")
    response.headers["WWW-Authenticate"] = 'Basic realm="1C:UNF mock"'
    return response


@app.get("/health/")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/status/")
async def status(session: DbSession) -> dict:
    counts: dict[str, int] = {}
    tables = sorted({entity.table for entity in ENTITIES.values()})
    for table in tables:
        result = await session.execute(text(f"SELECT count(*) FROM {settings.onec_mock_schema}.{table}"))
        counts[table] = result.scalar_one()
    return {"status": "ok", "schema": settings.onec_mock_schema, "tables": counts}


def _metadata_base(request: Request) -> str:
    return f"{request.base_url!s}".rstrip("/") + settings.base_path


@app.get(f"{settings.base_path}/{{path:path}}")
async def odata_endpoint(path: str, request: Request, session: DbSession) -> Response:
    auth_error = check_auth(request)
    if auth_error is not None:
        return auth_error

    file_value = _FILE_VALUE_RE.match(path)
    if file_value:
        return await _file_value_response(file_value.group("ref_key"), session)

    entity_name = path.rstrip("/")
    if entity_name not in ENTITIES:
        return odata_error(404, "8", f"Сущность '{entity_name}' не найдена")

    params = request.query_params
    try:
        top = int(params.get("$top", DEFAULT_TOP))
        skip = int(params.get("$skip", 0))
    except ValueError:
        return odata_error(400, "1", "Некорректные значения $top/$skip")
    filter_expr = params.get("$filter")

    try:
        value = await query_entity(
            session,
            settings.onec_mock_schema,
            entity_name,
            filter_expr=filter_expr,
            top=top,
            skip=skip,
        )
    except FilterError as exc:
        return odata_error(400, "1", str(exc))

    return JSONResponse(
        {
            "odata.metadata": f"{_metadata_base(request)}/$metadata#{entity_name}",
            "value": value,
        }
    )


async def _file_value_response(ref_key: str, session: AsyncSession) -> Response:
    result = await session.execute(
        text(f"SELECT 1 FROM {settings.onec_mock_schema}.product_files WHERE ref_key = :ref_key"),
        {"ref_key": ref_key},
    )
    if result.first() is None:
        return odata_error(404, "8", f"Сущность '{ref_key}' не найдена")
    return Response(content=placeholder_jpeg(ref_key), media_type="image/jpeg")
