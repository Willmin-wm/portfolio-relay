from flask import Flask, request, jsonify
import urllib.request
import urllib.parse
import json
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8514182866:AAF87qphDkIA_Qn0Fh6UVmChC_00Pgm3ML8")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",  "787324774")
API_KEY   = os.environ.get("RELAY_API_KEY",     "will-portfolio-2026")   # simple auth

def send_telegram(text):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id":    CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15) as r:
        return json.loads(r.read())

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Will Portfolio Telegram Relay"})

@app.route("/send", methods=["POST"])
def send():
    # Simple API-key auth
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    body = request.get_json(silent=True) or {}
    text = body.get("message", "").strip()
    if not text:
        return jsonify({"error": "missing 'message' field"}), 400

    try:
        result = send_telegram(text)
        return jsonify({"ok": True, "telegram": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
