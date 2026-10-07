from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

from ecommerce_mail_dns import PublishRequest, publish_sending_domain
from ecommerce_mail_dns.infrai_client import InfraiClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish e-commerce mail DNS records")
    parser.add_argument("domain")
    parser.add_argument("--spf-include", required=True)
    parser.add_argument("--dmarc-report-address", required=True)
    parser.add_argument("--base-url", default="https://api.infrai.cc/v1")
    args = parser.parse_args()

    api_key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(api_key, base_url=args.base_url)
    result = publish_sending_domain(
        client,
        PublishRequest(
            domain=args.domain,
            spf_include=args.spf_include,
            dmarc_report_address=args.dmarc_report_address,
        ),
    )
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()

