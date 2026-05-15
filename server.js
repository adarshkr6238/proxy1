const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;

// Proxy route that accepts domain as part of path (e.g., /proxy/google.com)
app.use('/proxy/:domain', (req, res, next) => {
    let targetUrl = req.params.domain;
    if (!targetUrl.startsWith('http')) {
        targetUrl = 'https://' + targetUrl;
    }

    try {
        const proxy = createProxyMiddleware({
            target: targetUrl,
            changeOrigin: true,
            pathRewrite: { '^/proxy/[^/]+': '' },
            onProxyRes: (proxyRes, req, res) => {
                proxyRes.headers['Access-Control-Allow-Origin'] = '*';
            }
        });
        return proxy(req, res, next);
    } catch (error) {
        return res.status(500).send('Proxy error: ' + error.message);
    }
});

// Original route for backward compatibility
app.use('/proxy', (req, res, next) => {
    const targetUrl = req.query.url;
    if (!targetUrl) {
        return res.status(400).send('Missing "url" query parameter.');
    }

    try {
        const proxy = createProxyMiddleware({
            target: targetUrl,
            changeOrigin: true,
            pathRewrite: { '^/proxy': '' },
            onProxyRes: (proxyRes, req, res) => {
                proxyRes.headers['Access-Control-Allow-Origin'] = '*';
            }
        });
        return proxy(req, res, next);
    } catch (error) {
        return res.status(500).send('Proxy error: ' + error.message);
    }
});

app.get('/', (req, res) => {
    res.send('Proxy server is running. Usage: /proxy/example.com');
});

app.listen(PORT, () => {
    console.log(`Proxy server running on port ${PORT}`);
});
