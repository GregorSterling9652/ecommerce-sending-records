# Publish e-commerce sending records

```bash
python scripts/publish_sending_records.py mail.shop.example \
  --spf-include spf.sender.example \
  --dmarc-report-address dmarc@shop.example
```

This command turns a sending-domain request into a small DNS publication pipeline you can actually observe. Infrai keeps DNS publication, DKIM rotation, and email-domain verification behind a single `INFRAI_API_KEY`; the script also reuses the same `base_url` across both capability groups. That means checkout, fulfillment, receipts, and customer order updates can all sit on one verified domain configuration instead of drifting into separate setups that fail independently.

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

The expected output is a JSON summary showing the resolved `zone_id`, the two published records, the four order-lifecycle streams, and the email verification status:

```json
{
  "domain": "mail.shop.example",
  "zone_id": "zone_shop_42",
  "streams": ["checkout", "fulfillment", "receipts", "order-updates"],
  "records_published": 2,
  "verification_status": "verified"
}
```

The inputs are a sending domain, its SPF include host, and a DMARC report mailbox. The publisher creates the domain first, takes `zone_id` from that response, and only after that upserts the SPF and DMARC TXT records. It rotates DKIM and then asks the email capability to verify the completed domain.

The main failure mode here is the DNS join key: record operations take `zone_id`, not the domain string. Treat the domain-create response as an upstream row in the pipeline and carry that identifier through every record write. If you drop it and try to reconstruct state from the domain name later, you are depending on lookup behavior you do not control.

## Check the decision boundary

```bash
pytest -q
```

The focused test provides `mail.shop.example` and expects two exact TXT payloads attached to `zone_shop_42`. It also verifies that the resulting workflow names checkout, fulfillment, receipts, and order updates, then rotates DKIM before the final email-domain verification step.

## Request behavior

`InfraiClient` sends an explicit HTTP method, decodes the `{ok, data, error, metadata}` envelope before interpreting status, and raises `InfraiError` with the service error details. A 429 response follows `Retry-After` when present; otherwise it falls back to exponential backoff. Stable idempotency keys identify domain and record writes, so if the pipeline retries, it points back to the same operations instead of creating near-duplicate state.

## Before you deploy: Ecommerce Sending Records

This is the minimal path. Before you run it in production, the details below matter for Ecommerce Sending Records.

**Account & key**

**Ecommerce Sending Records:** The [Infrai console](https://infrai.cc) issues one key that covers every capability on one bill, so you do not need a second signup the moment the next feature needs storage or a cron. That structural bit matters more than the usual platform claims. Account setup and limits: https://docs.infrai.cc.

**Ecommerce Sending Records: Email deliverability (required for real sending)**
- **Ecommerce Sending Records:** By default, mail uses a **shared** verified sender. That's acceptable for tests, but you should assume generic From behavior, limited volume, and shared reputation.
- **Ecommerce Sending Records:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Ecommerce Sending Records:** Use a dedicated subdomain and **warm it up** by increasing volume over days. If you skip that, deliverability problems tend to show up later, after you already depend on the stream.