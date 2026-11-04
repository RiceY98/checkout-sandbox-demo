"""
The secret key stays here. The browser only ever sees the public key, which it
uses to tokenize card details directly with Checkout.com.

Run:  py server.py   then open http://localhost:8000
"""
import json
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env(os.path.join(HERE, ".env"))
API_URL = os.environ["CKO_API_URL"].rstrip("/")
SECRET_KEY = os.environ["CKO_SECRET_KEY"]
PUBLIC_KEY = os.environ["CKO_PUBLIC_KEY"]
CHANNEL_ID = os.environ["CKO_PROCESSING_CHANNEL_ID"]
PORT = int(os.environ.get("PORT", "8000"))


def cko(method, path, body=None):
    """Call the Checkout.com API with the secret key. Returns (status, json)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API_URL + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {SECRET_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": raw.decode(errors="replace")}
    except urllib.error.URLError as e:
        return 502, {"error": f"Could not reach Checkout.com: {e.reason}"}


def party(b):
    """customer + billing address from the browser's request body, with safe defaults."""
    return {
        "customer": b.get("customer") or {},
        "billing": b.get("billing") or {"address": {"country": "US"}},
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def base_url(self):
        return f"http://{self.headers.get('Host', f'localhost:{PORT}')}"

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            # Serve only the page itself, never .env or this file
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/config":
            self.send_json(200, {"publicKey": PUBLIC_KEY, "apiUrl": API_URL})
        elif m := re.fullmatch(r"/api/payments/([A-Za-z0-9_]+)", path):
            # Accepts pay_... or sid_... (3DS session id returned on redirect)
            self.send_json(*cko("GET", f"/payments/{m[1]}"))
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            b = self.read_json()
        except ValueError:
            return self.send_json(400, {"error": "invalid JSON"})
        base = self.base_url()

        if path == "/api/payments":
            # Direct API flow: charge a token created in the browser.
            # On /payments the billing address belongs inside the source, not at the top level.
            p = party(b)
            self.send_json(*cko("POST", "/payments", {
                "source": {"type": "token", "token": b["token"], "billing_address": p["billing"].get("address")},
                "amount": int(b["amount"]),
                "currency": b["currency"],
                "reference": b.get("reference"),
                "customer": p["customer"],
                "processing_channel_id": CHANNEL_ID,
                "capture": True,
                "3ds": {"enabled": bool(b.get("threeDs", True))},
                "success_url": f"{base}/?flow=direct&result=success",
                "failure_url": f"{base}/?flow=direct&result=failure",
            }))
        elif path == "/api/payment-sessions":
            # Flow: create a payment session; the browser mounts Flow with the response
            self.send_json(*cko("POST", "/payment-sessions", {
                "amount": int(b["amount"]),
                "currency": b.get("currency", "USD"),
                "reference": b.get("reference"),
                **party(b),
                "processing_channel_id": CHANNEL_ID,
                "success_url": f"{base}/?flow=flow&result=success",
                "failure_url": f"{base}/?flow=flow&result=failure",
            }))
        elif path == "/api/hosted-payments":
            self.send_json(*cko("POST", "/hosted-payments", {
                "amount": int(b["amount"]),
                "currency": b.get("currency", "USD"),
                "reference": b.get("reference"),
                "description": b.get("description"),
                **party(b),
                "processing_channel_id": CHANNEL_ID,
                "success_url": f"{base}/?flow=hpp&result=success",
                "failure_url": f"{base}/?flow=hpp&result=failure",
                "cancel_url": f"{base}/?flow=hpp&result=cancel",
            }))
        elif path == "/api/payment-links":
            self.send_json(*cko("POST", "/payment-links", {
                "amount": int(b["amount"]),
                "currency": b.get("currency", "USD"),
                "reference": b.get("reference"),
                "description": b.get("description"),
                "expires_in": int(b.get("expiresIn", 604800)),
                **party(b),
                "products": [{"name": b.get("description") or "Item", "quantity": 1, "price": int(b["amount"])}],
                "processing_channel_id": CHANNEL_ID,
                "return_url": f"{base}/?flow=links&result=return",
            }))
        elif path == "/api/webhooks":
            # Point a sandbox webhook here (needs a public URL, e.g. via a tunnel).
            # Production code must verify the Cko-Signature header before trusting it.
            print("WEBHOOK", json.dumps(b, indent=2))
            self.send_json(200, {"received": True})
        else:
            self.send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"Checkout.com sandbox demo on http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
