import json
import logging
import websockets
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

DEEPGRAM_API_KEY = "f6dc1594bbe6685c8e391f5ef6dcf445f10d3c77"
DEEPGRAM_URL = f"wss://api.deepgram.com/v1/listen?access_token={DEEPGRAM_API_KEY}"

logger = logging.getLogger('deepgram')


class DeepgramConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        logger.info("WebSocket connection accepted for client: %s", self.channel_name)

        try:
            self.deepgram_ws = await websockets.connect(
                DEEPGRAM_URL,
                extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
            )
            logger.info("Connected to Deepgram WebSocket endpoint.")
        except Exception as e:
            logger.exception("Failed to connect to Deepgram WebSocket: %s", e)
            await self.close()
            return

        # Task to receive from Deepgram and forward to client
        self.recv_task = asyncio.create_task(self.receive_from_deepgram())
        logger.debug("Created async task for receiving data from Deepgram.")

    async def disconnect(self, close_code):
        logger.info("WebSocket disconnect initiated for client: %s | Code: %s", self.channel_name, close_code)

        if hasattr(self, 'recv_task'):
            self.recv_task.cancel()
            logger.debug("Cancelled Deepgram receive task.")

        if hasattr(self, 'deepgram_ws'):
            try:
                await self.deepgram_ws.close()
                logger.info("Closed Deepgram WebSocket connection.")
            except Exception as e:
                logger.exception("Error closing Deepgram WebSocket: %s", e)

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            try:
                await self.deepgram_ws.send(bytes_data)
                logger.debug("Sent binary data to Deepgram WebSocket.")
            except Exception as e:
                logger.exception("Error sending binary data to Deepgram: %s", e)

    async def receive_from_deepgram(self):
        try:
            async for message in self.deepgram_ws:
                await self.send(message)
                logger.debug("Received message from Deepgram and sent to client.")
        except websockets.ConnectionClosed:
            logger.warning("Deepgram WebSocket connection closed.")
        except Exception as e:
            logger.exception("Unexpected error in receiving from Deepgram: %s", e)