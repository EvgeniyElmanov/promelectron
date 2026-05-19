from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from server.app.core.config import ALGORITHM, SECRET_KEY

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
        email: str = payload.get("sub")
        if not email:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    from server.app.db.database import async_session_maker
    from server.app.models.user import User
    from sqlalchemy import select

    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user:
            await websocket.close(code=4001)
            return

        user_id = user.id

    await websocket.accept()

    if user_id not in connected_clients:
        connected_clients[user_id] = []
    connected_clients[user_id].append(websocket)

    try:
        while True:
            # Ждём heartbeat от клиента (ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        if user_id in connected_clients:
            if websocket in connected_clients[user_id]:
                connected_clients[user_id].remove(websocket)
            if not connected_clients[user_id]:
                del connected_clients[user_id]
