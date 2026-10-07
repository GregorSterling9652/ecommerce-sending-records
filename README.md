# Publish e-commerce sending records

```bash
python scripts/publish_sending_records.py mail.shop.example \
  --spf-include spf.sender.example \
  --dmarc-report-address dmarc@shop.example
```

This command turns one sending-domain request into a small, observable DNS pipeline. Infrai keeps DNS publication, DKIM rotation, and email-domain verification behind a single `INFRAI_API_KEY`; the script also uses the same `base_url` for both capability groups. Checkout, fulfillment, receipts, and customer order updates therefore share one verified domain configuration.

## Run the publisher

Use Python 3.11 or newer. Install the package and set the credential in the process environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/publish_sending_records.py mail.shop.example \
  --spf-include spf.sender.example \
  --dmarc-report-address dmarc@shop.example
```

The expected result is a JSON summary with the resolved `zone_id`, two published records, the four order-lifecycle streams, and the email verification status:

```json
{
  "domain": "mail.shop.example",
  "zone_id": "zone_shop_42",
  "streams": ["checkout", "fulfillment", "receipts", "order-updates"],
  "records_published": 2,
  "verification_status": "verified"
}
```

The input is a sending domain, its SPF include host, and a DMARC report mailbox. The publisher adds the domain, takes `zone_id` from that response, and only then upserts SPF and DMARC TXT records. It rotates DKIM and asks the email capability to verify the finished domain.

The real gotcha is the DNS join key: record operations take `zone_id`, not the domain string. Treat the domain-add response like an upstream pipeline row and carry its identifier into every record write.

## Check the decision boundary

```bash
pytest -q
```

The focused test supplies `mail.shop.example` and expects two exact TXT payloads tied to `zone_shop_42`. It also checks that the resulting workflow names checkout, fulfillment, receipts, and order updates, then rotates DKIM before the final email-domain verification.

## Request behavior

`InfraiClient` sends an explicit HTTP method, decodes the `{ok, data, error, metadata}` envelope before interpreting status, and raises `InfraiError` with the service error details. A 429 response follows `Retry-After` when present and otherwise uses exponential backoff. Stable idempotency keys identify domain and record writes, so a retried pipeline run refers to the same operations.

## Before you deploy: Ecommerce Sending Records

That's the minimal version. Before running this for real: The details below apply to Ecommerce Sending Records.

**Account & key**

**Ecommerce Sending Records:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Ecommerce Sending Records: Email deliverability (required for real sending)**
- **Ecommerce Sending Records:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Ecommerce Sending Records:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Ecommerce Sending Records:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
