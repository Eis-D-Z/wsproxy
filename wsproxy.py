import websockets
import asyncio
import signal
import logging
import os
from urllib.parse import unquote

class WebsocketProxy():
    logger = logging.getLogger('websockets')
    logger.setLevel(logging.INFO)

    def __init__(self):
        self.connections = {}

    async def producer_handler(self, server, path):
        while True:
            message = await self.connections[server].recv()
            self.logger.info(message)
            await server.send(message)
    
    async def consumer_handler(self, server, path):
        async for message in server:
            self.logger.info(message)
            await self.connections[server].send(message)
    
    async def register(self, websocket, url):
        client = await websockets.connect(url)
        self.connections[websocket] = client
    
    async def unregister(self, websocket):
        await self.connection[websocket].close()
        del self.connections[websocket]

    async def handler(self, websocket, path):
        url = unquote(path.split("?")[1].split("=")[1])
        await self.register(websocket, url)
        try:
            consumer_task = asyncio.ensure_future(self.consumer_handler(websocket, path))
            producer_task = asyncio.ensure_future(self.producer_handler(websocket, path))
            done, pending = await asyncio.wait([consumer_task, producer_task],
                                            return_when=asyncio.FIRST_COMPLETED,
                                            )
            for task in pending:
                task.cancel()
        finally:
           await self.unregister(websocket)

    async def stop(self):
        await self.client.close()
        #pid = os.getpid()
        #os.kill(pid, signal.SIGTERM)

    async def server(self, stop):
        async with websockets.serve(self.handler,"127.0.0.1", 8764) as server:
            self.server = server
            await stop


if __name__ == "__main__":

    proxy = WebsocketProxy()
    loop = asyncio.get_event_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    loop.run_until_complete(proxy.server(stop))
    loop.run_forever()
