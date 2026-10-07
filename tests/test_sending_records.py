from typing import Any

from ecommerce_mail_dns import PublishRequest, publish_sending_domain
from ecommerce_mail_dns.infrai_client import InfraiClient


class RecordingClient(InfraiClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"method": method, "path": path, **kwargs})
        if path == "/dns/domain/add":
            return {"zone_id": "zone_shop_42"}
        if path == "/email/domain/verify":
            return {"verification": {"status": "verified"}}
        return {}


def test_publish_plan_uses_zone_and_covers_order_lifecycle() -> None:
    client = RecordingClient()

    result = publish_sending_domain(
        client,
        PublishRequest(
            domain="mail.shop.example",
            spf_include="spf.sender.example",
            dmarc_report_address="dmarc@shop.example",
            ttl=900,
        ),
    )

    upserts = [call for call in client.calls if call["path"] == "/dns/record/upsert"]
    assert [call["body"] for call in upserts] == [
        {
            "zone_id": "zone_shop_42",
            "record_type": "TXT",
            "name": "mail.shop.example",
            "content": "v=spf1 include:spf.sender.example -all",
            "ttl": 900,
            "metadata": {"pipeline": "ecommerce-mail"},
        },
        {
            "zone_id": "zone_shop_42",
            "record_type": "TXT",
            "name": "_dmarc.mail.shop.example",
            "content": "v=DMARC1; p=reject; rua=mailto:dmarc@shop.example",
            "ttl": 900,
            "metadata": {"pipeline": "ecommerce-mail"},
        },
    ]
    assert result.streams == ("checkout", "fulfillment", "receipts", "order-updates")
    assert result.verification_status == "verified"
    assert client.calls[-2]["path"] == "/email/domain/rotate_dkim"
    assert client.calls[-1]["path"] == "/email/domain/verify"
