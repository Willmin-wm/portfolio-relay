# Will's Portfolio Telegram Relay

A tiny Flask server that relays messages from the Cowork scheduled task to Telegram.

## Deploy to Render (free)

1. Push this folder to a **new GitHub repo** (e.g. `portfolio-relay`)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — just click **Deploy**
5. Your relay URL will be: `https://will-portfolio-relay.onrender.com`

## API Usage

```bash
curl -X POST https://will-portfolio-relay.onrender.com/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: will-portfolio-2026" \
  -d '{"message": "Hello from portfolio bot!"}'
```

## Health Check
```
GET https://will-portfolio-relay.onrender.com/
```
