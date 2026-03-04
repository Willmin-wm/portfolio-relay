from flask import Flask, request, jsonify
import urllib.request
import urllib.parse
import json
import os
from datetime import datetime
import pytz

app = Flask(__name__)

API_KEY   = os.environ.get("RELAY_API_KEY", "will-portfolio-2026")
WA_PHONE  = os.environ.get("WA_PHONE",      "16282935371")
WA_APIKEY = os.environ.get("WA_APIKEY",     "8937649")

# Portfolio holdings: ticker -> (shares, ref_price)
HOLDINGS = {
    "GOOG":  (4.87944,  1102.73), "TSM":   (2.78854,  354.69),
    "AMZN":  (3.97516,  208.02),  "NVDA":  (3.91831,  180.06),
    "XLE":   (11.627,   56.37),   "RKLB":  (7.91498,  71.53),
    "TSLA":  (1.43496,  393.46),  "NLR":   (3.81458,  144.46),
    "SOXX":  (1.54461,  336.21),  "CRCL":  (4.98864,  103.60),
    "MP":    (7.21341,  62.24),   "MU":    (1.11774,  380.67),
    "URG":   (260,      1.61),    "COPP":  (10.23978, 40.60),
    "PL":    (14.97236, 25.43),   "USAR":  (18.09943, 19.82),
    "RDW":   (39.42718, 8.90),    "ROBO":  (4.64103,  75.13),
    "ISRG":  (0.6999,   496.39),  "COPX":  (3.97745,  87.20),
    "PLTR":  (2.27035,  146.37),  "DXYZ":  (10.46337, 27.09),
    "AVGO":  (0.75551,  313.58),  "MSFT":  (0.55413,  404.76),
    "BOTZ":  (5.93221,  37.05),   "NFLX":  (2.16592,  97.17),
    "RMBS":  (2.24718,  88.40),   "LRCX":  (0.88527,  217.20),
    "ICLN":  (10.00059, 17.78),   "AIQ":   (3.44973,  48.92),
    "VRT":   (0.65023,  244.57),  "COIN":  (0.71002,  185.12),
    "CC":    (7.45618,  16.95),   "MSTR":  (0.84819,  135.06),
    "QRVO":  (1.16979,  81.00),   "BTBT":  (53.96004, 1.71),
    "LLY":   (0.09083,  1008.38), "WDC":   (0.36359,  250.28),
    "IBIT":  (2.22965,  38.94),   "ET":    (3.55759,  19.02),
    "CRWD":  (0.14724,  391.84),  "BABA":  (0.32082,  136.73),
    "ARKVX": (37.956,   49.88),   "INNOX": (37.03,    18.26),
    "ARKG":  (5.30316,  29.47),   "IDNA":  (5,        30.03),
}

ALERT_THRESHOLD = 0.05  # 5%


# ── WhatsApp ─────────────────────────────────────────────────

def send_whatsapp(text):
    encoded = urllib.parse.quote(text)
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={WA_PHONE}&text={encoded}&apikey={WA_APIKEY}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return {"ok": True, "response": r.read().decode()}


# ── Price fetching ───────────────────────────────────────────

def fetch_prices(tickers):
    prices = {}
    batch_size = 10
    ticker_list = list(tickers)
    for i in range(0, len(ticker_list), batch_size):
        batch = ticker_list[i:i+batch_size]
        symbols = "%2C".join(batch)
        url = (
            f"https://query1.finance.yahoo.com/v7/finance/quote"
            f"?symbols={symbols}&fields=regularMarketPrice,regularMarketChangePercent"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            for q in data.get("quoteResponse", {}).get("result", []):
                sym   = q.get("symbol", "")
                price = q.get("regularMarketPrice")
                pct   = q.get("regularMarketChangePercent")
                if sym and price is not None:
                    prices[sym] = {"price": price, "change_pct": pct or 0.0}
        except Exception:
            pass
    return prices


# ── Message builder ──────────────────────────────────────────

def build_alert_message(prices, session_label):
    pst      = pytz.timezone("America/Los_Angeles")
    now_pst  = datetime.now(pst)
    date_str = now_pst.strftime("%a %b %-d, %Y | %-I:%M %p PST")

    alerts, movers = [], []
    total_current = total_ref = 0.0

    for ticker, (shares, ref_price) in HOLDINGS.items():
        ref_val = shares * ref_price
        total_ref += ref_val
        if ticker in prices:
            cur_price = prices[ticker]["price"]
            pct       = prices[ticker]["change_pct"] / 100.0
            cur_val   = shares * cur_price
            total_current += cur_val
            movers.append((ticker, pct, cur_price, cur_val))
            if abs(pct) >= ALERT_THRESHOLD:
                arrow = "🔺" if pct > 0 else "🔻"
                dollar_impact = cur_val - ref_val
                alerts.append(
                    f"{arrow} {ticker}: {pct:+.1%} -> ${cur_price:.2f} "
                    f"(Impact: ${dollar_impact:+,.0f})"
                )
        else:
            total_current += ref_val

    movers.sort(key=lambda x: x[1], reverse=True)
    top5_gain = movers[:5]
    top5_loss = movers[-5:][::-1]

    daily_change     = total_current - total_ref
    daily_change_pct = (daily_change / total_ref * 100) if total_ref else 0

    sep = "──────────────────"
    lines = [
        f"📊 Portfolio Alert",
        f"{date_str}",
        f"{session_label}",
        sep,
    ]

    if alerts:
        lines += ["🔔 ALERTS (>5% Move)"] + alerts
    else:
        lines += ["🔔 ALERTS", "✅ No positions breached +-5% today"]

    lines += ["", sep, "📈 Top Gainers"]
    for t, pct, price, _ in top5_gain:
        lines.append(f"  {t}: {pct:+.2%} -> ${price:.2f}")

    lines += ["", "📉 Top Losers"]
    for t, pct, price, _ in top5_loss:
        lines.append(f"  {t}: {pct:+.2%} -> ${price:.2f}")

    lines += [
        "",
        sep,
        f"💰 Portfolio Value",
        f"  ${total_current:,.0f} ({daily_change_pct:+.1f}% today)",
        f"  Daily P&L: ${daily_change:+,.0f}",
        f"  15% target: ${total_ref * 1.15:,.0f}",
        "",
        sep,
        "📅 Upcoming Catalysts",
        "  NVDA GTC: Mar 17-21",
        "  MU Earnings: ~Mar 26",
        "  AMZN/GOOG Q1: late Apr",
        "",
        "-- Will's Portfolio Bot",
    ]
    return "\n".join(lines)


# ── Routes ───────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Will Portfolio Alert (WhatsApp)"})


@app.route("/run-alert", methods=["GET"])
def run_alert():
    if request.args.get("key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    pst      = pytz.timezone("America/Los_Angeles")
    hour_pst = datetime.now(pst).hour
    session  = "Pre-Market Check" if hour_pst < 12 else "Mid-Day Check"

    try:
        prices  = fetch_prices(list(HOLDINGS.keys()))
        message = build_alert_message(prices, session)
        result  = send_whatsapp(message)
        return jsonify({"ok": True, "prices_fetched": len(prices), "whatsapp": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
