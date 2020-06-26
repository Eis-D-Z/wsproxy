import websockets
import asyncio
import signal
import logging
import os
import ssl
import pathlib
from urllib.parse import unquote

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
class WebsocketProxy():

    def __init__(self):
        self.connections = {}

    async def producer_handler(self, server, path):
        while True:
            message = await self.connections[server].recv()
            await server.send(message)
    
    async def consumer_handler(self, server, path):
        async for message in server:
            await self.connections[server].send(message)
    
    async def register(self, websocket, url):
        logger.warning("The url I am about to connect to is {}".format(url))
        try:
            client = await websockets.connect(url, ping_interval=None, subprotocols=['binary'])
        except ssl.SSLCertVerificationError:
            logger.warning("I am going to ignore self-signed")
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            client = await websockets.connect(url, ping_interval=None, ssl=context, subprotocols=['binary'])
        self.connections[websocket] = client
    
    async def unregister(self, websocket):
        await self.connections[websocket].close()
        del self.connections[websocket]

    async def handler(self, websocket, path):
        url = unquote(path.split("?")[1])
        if 'url' not in url:
            msg = ("Please specify a 'url' parameter in the URL path. "
                   "eg: host:8764?url=wss://echo.websocket.org")
            raise ValueError(msg)
        if "&" in url:
            urls = url.split("&")
            for url in urls:
                if 'url' in url:
                    break
        url = url.split("=")[1]
        await self.register(websocket, url)
        logger.warning("Connected!!")
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
        async with websockets.serve(self.handler,"0.0.0.0", 8764, ping_interval=None, subprotocols=['binary']) as server:
            self.server = server
            await stop


if __name__ == "__main__":

    proxy = WebsocketProxy()
    loop = asyncio.get_event_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    loop.run_until_complete(proxy.server(stop))
    loop.run_forever()
