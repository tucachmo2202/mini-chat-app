from fastapi import WebSocket, WebSocketDisconnect, Depends, status, HTTPException
from broadcaster import Broadcast
from auth import get_current_user
import json


async def websocket_endpoint(
    websocket: WebSocket,
    broadcast: Broadcast,
    room_id: str,
    user_data: str = Depends(get_current_user),
):
    if user_data.user_id != room_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not allow to send message to this room",
        )
    await websocket.accept()
    async with broadcast.subscribe(channel=room_id) as subscriber:
        try:
            while True:
                data = await websocket.receive_text()
                await broadcast.publish(channel=room_id, message=json.dumps(data))
                event = await subscriber.get()
                await websocket.send_text(event.message)

                # need to implement message reply
        except WebSocketDisconnect:
            await websocket.close()
