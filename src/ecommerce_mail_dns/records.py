from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class PublishRequest:
    domain: str
    spf_include: str
    dmarc_report_address: str
    ttl: int = 3600


@dataclass(frozen=True)
class PublishResult:
    domain: str
    zone_id: str
    streams: tuple[str, ...]
    records_published: int
    verification_status: str


def _record_plan(request: PublishRequest) -> tuple[Mapping[str, Any], ...]:
    return (
        {
            "record_type": "TXT",
            "name": request.domain,
            "content": f"v=spf1 include:{request.spf_include} -all",
            "ttl": request.ttl,
            "metadata": {"pipeline": "ecommerce-mail"},
        },
        {
            "record_type": "TXT",
            "name": f"_dmarc.{request.domain}",
            "content": f"v=DMARC1; p=reject; rua=mailto:{request.dmarc_report_address}",
            "ttl": request.ttl,
            "metadata": {"pipeline": "ecommerce-mail"},
        },
    )


def publish_sending_domain(client: InfraiClient, request: PublishRequest) -> PublishResult:
    domain_data = client.request(
        "POST",
        "/dns/domain/add",
        body={"domain": request.domain, "metadata": {"workload": "ecommerce"}},
        idempotency_key=client.operation_key(request.domain, "add-domain"),
    )
    zone_id = str(domain_data["zone_id"])

    records = _record_plan(request)
    for record in records:
        payload = {"zone_id": zone_id, **record}
        client.request(
            "PUT",
            "/dns/record/upsert",
            body=payload,
            idempotency_key=client.operation_key(
                request.domain, f"upsert:{record['name']}:{record['record_type']}"
            ),
        )

    client.request(
        "POST",
        "/email/domain/rotate_dkim",
        idempotency_key=client.operation_key(request.domain, "rotate-dkim"),
    )
    verification = client.request(
        "POST",
        "/email/domain/verify",
        body={"domain": request.domain},
        idempotency_key=client.operation_key(request.domain, "verify-email-domain"),
    )
    verification_data = verification.get("verification", {})

    return PublishResult(
        domain=request.domain,
        zone_id=zone_id,
        streams=("checkout", "fulfillment", "receipts", "order-updates"),
        records_published=len(records),
        verification_status=str(verification_data["status"]),
    )
