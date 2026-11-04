# Checkout.com Sandbox Payments Demo

A small demo that takes test payments through the Checkout.com sandbox in four ways, side by side:

| Tab | What it shows |
|---|---|
| **Direct API** | The browser tokenizes the card with the public key, then the server charges the token with `POST /payments` |
| **Flow** | The server creates a payment session (`POST /payment-sessions`), then the browser mounts the Flow component |
| **Hosted Page** | The server creates a Hosted Payments Page and the shopper is redirected to it |
| **Payment Links** | The server creates a shareable payment link |

The secret key stays on the server. The browser only sees the public key.

## Requirements

- Python 3.8 or newer. It uses only the standard library, so there's nothing to install.
- A Checkout.com sandbox account with a public key, a secret key and a processing channel ID.
- An internet connection, because the page loads the Flow script from `checkout-web-components.checkout.com`.

## Run it

1. Copy `.env.example` to `.env` and fill in your sandbox values.
2. Start the server:
   ```
   python server.py        # on Windows: py server.py
   ```
3. Open http://localhost:8000.

## Test details

- Card: `4242 4242 4242 4242`, any future expiry date, CVV `100`
- Payments show up in the sandbox dashboard under Payments > Processing > All payments.

## Notes

- This is a sandbox demo, not production code.
- In production, verify the `Cko-Signature` header on webhooks before trusting them.
- For production card capture, use Flow or Frames rather than a hand-built form, so you stay in the lowest PCI scope.
