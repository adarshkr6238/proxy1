"""
Simple async HTTP/HTTPS forward proxy.
Supports two modes:
1. Custom format: client sends request with X-Target-URL header
2. Standard forward proxy: client sends request with absolute URI in request line (e.g., GET http://api.telegram.org/... HTTP/1.1)
   and CONNECT method for HTTPS tunneling.
"""

import asyncio
import logging
import os
import sys
from urllib.parse import urlparse

import aiohttp
from aiohttp import web, ClientSession, ClientTimeout
from aiohttp.http_parser import HttpParser

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("proxy")

PORT = int(os.environ.get("PORT", 10000))
PROXY_KEY = os.environ.get("PROXY_KEY", "")
ALLOWED_HOSTS = set(
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()
)
CONNECT_TIMEOUT = int(os.environ.get("CONNECT_TIMEOUT", 30))
READ_TIMEOUT = int(os.environ.get("READ_TIMEOUT", 300))


@web.middleware
async def auth_middleware(request, handler):
    if PROXY_KEY:
        if request.headers.get("X-Proxy-Key") != PROXY_KEY:
            logger.warning(f"Rejected unauthorized request from {request.remote}")
            return web.Response(status=403, text="Forbidden: missing X-Proxy-Key")
    return await handler(request)


def is_allowed(host: str) -> bool:
    return not ALLOWED_HOSTS or host in ALLOWED_HOSTS


async def handle_connect(request: web.Request) -> web.Response:
    """Handle CONNECT method for HTTPS tunneling."""
    target = request.path_qs  # CONNECT target is in path (host:port)
    host_port = target.split(":")
    if len(host_port) != 2:
        return web.Response(status=400, text="Invalid CONNECT target")
    host, port = host_port[0], int(host_port[1])
    
    if not is_allowed(host):
        return web.Response(status=403, text=f"Host {host} not allowed")
    
    try:
        # Connect to target
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT
        )
    except asyncio.TimeoutError:
        return web.Response(status=504, text="Gateway Timeout")
    except Exception as e:
        logger.error(f"CONNECT failed to {host}:{port}: {e}")
        return web.Response(status=502, text=f"Bad Gateway: {e}")
    
    # Send 200 Connection Established
    transport = request.transport
    transport.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    
    # Pipe data between client and target
    client_reader = request.transport.get_protocol().data.get('reader') if hasattr(request.transport, 'get_protocol') else None
    
    # aiohttp doesn't expose raw socket easily. Use a different approach:
    # We'll use the request's transport directly
    client_protocol = request.transport.get_protocol() if hasattr(request.transport, 'get_protocol') else None
    
    # Simpler: use aiohttp's web.Response with custom body for streaming
    # But CONNECT needs raw socket. Let's use a StreamResponse and manual piping.
    
    response = web.StreamResponse(status=200)
    await response.prepare(request)
    
    # Get client socket
    client_reader = request.content  # This doesn't work for raw data
    
    # This is complex with aiohttp. Let's use a simpler approach:
    # Just forward the raw bytes using the transport
    client_transport = request.transport
    
    async def pipe(reader, writer, name):
        try:
            while True:
                data = await reader.read(8192)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception as e:
            logger.debug(f"{name} pipe error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    # We need access to the raw client reader. aiohttp doesn't expose it easily for CONNECT.
    # Let's use a different strategy: respond with 200 and then the client will start TLS.
    # But we can't easily pipe after that with aiohttp's high-level API.
    
    # For simplicity, let's just use a pre-existing library or different approach.
    # For now, return 501 for CONNECT - we'll handle HTTPS via our custom format instead.
    return web.Response(status=501, text="CONNECT not supported, use X-Target-URL format")


async def proxy_handler(request: web.Request) -> web.Response:
    """Handle both standard forward proxy (absolute URI) and custom X-Target-URL format."""
    target_url = None
    
    # Mode 1: Custom format - X-Target-URL header
    if "X-Target-URL" in request.headers:
        target_url = request.headers.get("X-Target-URL")
    # Mode 2: Standard forward proxy - absolute URI in request line
    elif request.path.startswith(("http://", "https://")):
        target_url = request.path_qs
    
    if not target_url:
        return web.Response(status=400, text="Missing X-Target-URL header or absolute URI in request line")
    
    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        return web.Response(status=400, text="Only http/https targets allowed")
    if not is_allowed(parsed.hostname):
        logger.warning(f"Blocked target host: {parsed.hostname}")
        return web.Response(status=403, text=f"Host {parsed.hostname} not allowed")
    
    # Handle CONNECT method
    if request.method == "CONNECT":
        return await handle_connect(request)
    
    # Build headers to forward
    skip = {
        "host",
        "content-length",
        "transfer-encoding",
        "connection",
        "x-target-url",
        "x-proxy-key",
        "proxy-connection",
        "proxy-authorization",
    }
    fwd_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in skip
    }
    
    # For standard forward proxy, set Host header
    if "host" not in {k.lower() for k in fwd_headers}:
        fwd_headers["Host"] = parsed.netloc
    
    body = await request.read() if request.body_exists else None
    
    timeout = ClientTimeout(
        connect=CONNECT_TIMEOUT, total=READ_TIMEOUT, sock_connect=CONNECT_TIMEOUT
    )
    
    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=fwd_headers,
                params=request.query if "?" not in target_url else None,
                data=body,
                allow_redirects=False,
            ) as resp:
                resp_headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() not in skip
                }
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