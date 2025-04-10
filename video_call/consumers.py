import json
import websockets
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

DEEPGRAM_API_KEY = "ec2ada5f787c5931030a5be25576d8fc61cfe164"
DEEPGRAM_URL = f"wss://api.deepgram.com/v1/listen?access_token={DEEPGRAM_API_KEY}"

class DeepgramConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.deepgram_ws = await websockets.connect(DEEPGRAM_URL)

        # Task to receive from Deepgram and forward to client
        self.recv_task = asyncio.create_task(self.receive_from_deepgram())

    async def disconnect(self, close_code):
        self.recv_task.cancel()
        await self.deepgram_ws.close()

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            await self.deepgram_ws.send(bytes_data)

    async def receive_from_deepgram(self):
        try:
            async for message in self.deepgram_ws:
                await self.send(message)
        except websockets.ConnectionClosed:
            pass
