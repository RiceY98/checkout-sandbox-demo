# Checkout.com Sandbox Payments Demo


| Tab | What it shows |
|---|---|
| **Direct API** | The browser tokenizes the card with the public key, then the server charges the token with `POST /payments` |
| **Flow** | The server creates a payment session (`POST /payment-sessions`), then the browser mounts the Flow component |
| **Hosted Page** | The server creates a Hosted Payments Page and the shopper is redirected to it |
| **Payment Links** | The server creates a shareable payment link |



## Test details

- Card: `4242424242424242`, any future expiry date, CVV `100`
- Payments show up in the sandbox dashboard under Payments > Processing > All payments.

**FOR SANDBOX USE - Eric Tan Checkoout Demo**
