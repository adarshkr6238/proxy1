---
title: tgbotspace proxy
emoji: 🌐
colorFrom: gray
colorTo: gray
sdk: docker
pinned: false
---

# HTTP Forward Proxy

Simple async HTTP/HTTPS forward proxy used by the [tgbotspace](https://huggingface.co/spaces/shadow62/tgbotspace) Hugging Face Space to reach `api.telegram.org` (which HF Spaces blocks outbound to).

## How it works

Send a request to any path on this server with header `X-Target-URL` set to the URL you want to reach. The proxy forwards method, headers, body and query string, and returns the upstream response.

### Authentication
If the environment variable `PROXY_KEY` is set, requests must include header `X-Proxy-Key` matching that value.

### Host allowlist (optional)
Set `ALLOWED_HOSTS` as a comma-separated list to restrict which hosts can be reached through the proxy. If unset, all hosts are allowed.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `10000` | Listen port (Render sets this automatically) |
| `PROXY_KEY` | _(empty)_ | Optional shared secret for the `X-Proxy-Key` header |
| `ALLOWED_HOSTS` | _(empty = all)_ | Comma-separated host allowlist |
| `CONNECT_TIMEOUT` | `30` | TCP connect timeout (seconds) |
| `READ_TIMEOUT` | `300` | Total request timeout (seconds) |

## Deploy on Render

1. New → Web Service → connect this repo.
2. Runtime: Docker (it auto-detects the `Dockerfile`).
3. Add environment variables (set `PROXY_KEY` to a strong secret).
4. Deploy. Render auto-deploys on every push to `main`.

## Client usage example

```bash
curl -X POST \
  -H "X-Target-URL: https://api.telegram.org/bot<TOKEN>/getMe" \
  -H "X-Proxy-Key: <your-key>" \
  https://your-service.onrender.com/
```
