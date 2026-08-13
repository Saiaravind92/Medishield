import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.graph import pipeline_graph

router = APIRouter(tags=["WebSocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws/case-execution/{case_id}")
async def websocket_case_execution(websocket: WebSocket, case_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Heartbeat ping
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
