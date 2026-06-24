from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from src.app.core.config import ALGORITHM, SECRET_KEY
from src.app.services.token_denylist import is_revoked

router = APIRouter(tags=["websocket"])

# Хранилище подключений: user_id -> list[WebSocket]
connected_clients: dict[int, list[WebSocket]] = {}


async def notify_user(user_id: int, message: dict) -> None:
    """Отправить сообщение всем WebSocket-подключениям пользователя."""
    clients = connected_clients.get(user_id, [])
    for ws in clients[:]:
        try:
            await ws.send_json(message)
        except Exception:
            clients.remove(ws)


@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket для real-time уведомлений.

    Подключение: ws://host/ws/notifications?token=<jwt>
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # F-10: sub is now the stable numeric user id (str).
        sub: str = payload.get("sub")
        if not sub:
            await websocket.close(code=4001)
            return
        try:
            user_id = int(sub)
        except (ValueError, TypeError):
            await websocket.close(code=4001)
            return
        # F-07 (review fix): check jti denylist — revoked tokens must not open a socket.
        jti: str = payload.get("jti")
        if await is_revoked(jti):
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    from sqlalchemy import select

    from src.app.db.database import async_session_maker
    from src.app.models.user import User

    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            await websocket.close(code=4001)
            return

        ws_user_id = user.id

    await websocket.accept()

    if ws_user_id not in connected_clients:
        connected_clients[ws_user_id] = []
    connected_clients[ws_user_id].append(websocket)

    try:
        while True:
            # Ждём heartbeat от клиента (ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        if ws_user_id in connected_clients:
            if websocket in connected_clients[ws_user_id]:
                connected_clients[ws_user_id].remove(websocket)
            if not connected_clients[ws_user_id]:
                del connected_clients[ws_user_id]
