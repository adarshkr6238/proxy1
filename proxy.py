"""
Simple async Forward Proxy with HTTPS CONNECT support.
Forwards requests to target.
"""

import asyncio
import logging
import os
from aiohttp import web, ClientSession, ClientTimeout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

PORT = int(os.environ.get("PORT", 10000))
# Optional key for basic protection
PROXY_KEY = os.environ.get("PROXY_KEY", "")

async def handle_connect(request: web.Request) -> web.Response:
    """Handle HTTPS CONNECT method."""
    host, port = request.path_qs.split(':')
    port = int(port)
    
    # Connect to target
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except Exception as e:
        return web.Response(status=502, text=str(e))
    
    # Notify client
    # We need to use the raw underlying transport from aiohttp
    # This is a bit tricky, but for simple proxy it works
    
    # Send 200 Connection Established
    # We manually write to the transport
    request.transport.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    
    # Pipe data
    async def pipe(r, w):
        while True:
            try:
                data = await r.read(4096)
                if not data: break
                w.write(data)
                await w.drain()
            except: break
        w.close()
        
    await asyncio.gather(pipe(request.content, writer), pipe(reader, request.transport))
    return web.Response(status=200)

async def proxy_handler(request: web.Request) -> web.Response:
    # Basic auth
    if PROXY_KEY and request.headers.get("Proxy-Authorization") != f"Bearer {PROXY_KEY}":
        return web.Response(status=407, text="Proxy Authentication Required")
        
    if request.method == "CONNECT":
        return await handle_connect(request)
        
    # Regular Forward Proxy
    target_url = request.path_qs
    
    async with ClientSession() as session:
        async with session.request(
            request.method,
            target_url,
            headers={k: v for k, v in request.headers.items() if k.lower() not in ('host', 'proxy-authorization')},
            data=await request.read(),
            allow_redirects=False
        ) as resp:
            return web.Response(
                status=resp.status,
                body=await resp.read(),
                headers={k: v for k, v in resp.headers.items() if k.lower() not in ('transfer-encoding', 'connection')}
            )

async def keep_alive(request: web.Request) -> web.Response:
    return web.Response(text="Keep alive")

app = web.Application()
app.router.add_route("*", "/{path:.*}", proxy_handler)
app.router.add_route("GET", "/ping", keep_alive)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
