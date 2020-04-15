import websockets
import asyncio
import signal
import logging
import os

class WebsocketProxy():
    logger = logging.getLogger('websockets')
    logger.setLevel(logging.INFO)
    
    async def producer_handler(self, server, path):
        while True:
            message = await self.client.recv()
            self.logger.info(message)
            await server.send(message)
    
    async def consumer_handler(self, server, path):
        async for message in server:
            self.logger.info(message)
            await self.client.send(message)

    async def handler(self, websocket, path):
        try:
            consumer_task = asyncio.ensure_future(self.consumer_handler(websocket, path))
            producer_task = asyncio.ensure_future(self.producer_handler(websocket, path))
            done, pending = await asyncio.wait([consumer_task, producer_task],
                                            return_when=asyncio.FIRST_COMPLETED,
                                            )
            for task in pending:
                task.cancel()
        finally:
            self.stop()

    def stop(self):
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)

    async def server(self, stop, websocket_url):
        async with websockets.serve(self.handler,"192.168.2.3", 8764) as server:
            self.server = server
            async with websockets.connect(websocket_url) as client:
                self.client = client
                await stop

    def start(self, websocket_url="wss://echo.websocket.org/"):
        loop = asyncio.get_event_loop()
        stop = loop.create_future()
        loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
        loop.run_until_complete(self.server(stop,websocket_url))
