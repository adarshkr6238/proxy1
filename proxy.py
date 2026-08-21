"""
Simple async HTTP/HTTPS forward proxy.
Forwards all incoming requests to the target server and returns the response.
Used by the HF Space Telegram bot to reach api.telegram.org (which HF blocks).
"""

import asyncio
import logging
import os
import sys
from urllib.parse import urlparse

import aiohttp
from aiohttp import web, ClientSession

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("proxy")

PORT = int(os.environ.get("PORT", 10000))
# Optional shared-secret check. If set, requests must include header X-Proxy-Key.
PROXY_KEY = os.environ.get("PROXY_KEY", "")

# Hosts we are willing to forward to. If empty, all hosts are allowed.
ALLOWED_HOSTS = set(
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()
)

# Timeouts
CONNECT_TIMEOUT = int(os.environ.get("CONNECT_TIMEOUT", 30))
READ_TIMEOUT = int(os.environ.get("READ_TIMEOUT", 300))


@web.middleware
async def auth_middleware(request, handler):
    if PROXY_KEY:
        if request.headers.get("X-Proxy-Key") != PROXY_KEY:
            logger.warning(f"Rejected unauthorized request from {request.remote}")
            return web.Response(status=403, text="Forbidden: missing X-Proxy-Key")
    return await handler(request)


async def proxy_handler(request: web.Request) -> web.Response:
    """Forward any incoming request to the target URL provided via the
    `X-Target-URL` header. Body, method, headers and query string are
    forwarded. Streaming responses are supported for large downloads.
    """
    target_url = request.headers.get("X-Target-URL")
    if not target_url:
        return web.Response(status=400, text="Missing X-Target-URL header")

    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        return web.Response(status=400, text="Only http/https targets allowed")
    if ALLOWED_HOSTS and parsed.hostname not in ALLOWED_HOSTS:
        logger.warning(f"Blocked target host: {parsed.hostname}")
        return web.Response(status=403, text=f"Host {parsed.hostname} not allowed")

    # Build headers to forward (drop hop-by-hop and our internal headers)
    skip = {
        "host",
        "content-length",
        "transfer-encoding",
        "connection",
        "x-target-url",
        "x-proxy-key",
    }
    fwd_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in skip
    }

    body = await request.read() if request.body_exists else None

    timeout = aiohttp.ClientTimeout(
        connect=CONNECT_TIMEOUT, total=READ_TIMEOUT, sock_connect=CONNECT_TIMEOUT
    )

    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=fwd_headers,
                params=request.query,
                data=body,
                allow_redirects=False,
            ) as resp:
                # Build response headers
                resp_headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() not in skip
                }
                # Stream the body back
                response_body = await resp.read()
                return web.Response(
                    status=resp.status,
                    body=response_body,
                    headers=resp_headers,
                )
    except asyncio.TimeoutError:
        logger.error(f"Timeout forwarding to {target_url}")
        return web.Response(status=504, text="Gateway Timeout")
    except aiohttp.ClientError as e:
        logger.error(f"Client error forwarding to {target_url}: {e}")
        return web.Response(status=502, text=f"Bad Gateway: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return web.Response(status=500, text=f"Internal Proxy Error: {e}")


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="Proxy is running")


def create_app() -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_route("*", "/health", health_handler)
    app.router.add_route("*", "/{path:.*}", proxy_handler)
    return app


if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting proxy on 0.0.0.0:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
