"""
Simple async Reverse Proxy for Telegram Bot API on Render.
Forwards all requests to https://api.telegram.org.
"""

import asyncio
import logging
import os
from aiohttp import web, ClientSession, ClientTimeout

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("proxy")

PORT = int(os.environ.get("PORT", 10000))
PROXY_KEY = os.environ.get("PROXY_KEY", "")
TELEGRAM_API = "https://api.telegram.org"

@web.middleware
async def auth_middleware(request, handler):
    if PROXY_KEY:
        # Check X-Proxy-Key header or Bearer token
        key = request.headers.get("X-Proxy-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if key != PROXY_KEY:
            return web.Response(status=403, text="Forbidden")
    return await handler(request)

async def proxy_handler(request: web.Request) -> web.Response:
    # Build target URL on api.telegram.org
    path = request.match_info.get("path", "")
    target_url = f"{TELEGRAM_API}/{path}"
    
    # Check for key in query parameters
    key = request.query.get("key") or request.headers.get("X-Proxy-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if PROXY_KEY and key != PROXY_KEY:
        return web.Response(status=403, text="Forbidden")
    
    # ... rest is same ...

async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="Reverse Proxy is running")

def create_app() -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_route("*", "/health", health_handler)
    app.router.add_route("*", "/{path:.*}", proxy_handler)
    return app

if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting reverse proxy on 0.0.0.0:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
