from dataclasses import dataclass, field

import pytest

from storefront_campaigns.campaign_manager import CampaignManager
from storefront_campaigns.infrai_sms import SmsSendResult
from storefront_campaigns.models import (
    CampaignMessage,
    CampaignRequest,
    TenantCreate,
    TenantState,
)


@dataclass
class RecordingSms:
    sends: list[dict[str, str]] = field(default_factory=list)

    def send(self, *, to: str, body: str, idempotency_key: str) -> SmsSendResult:
        self.sends.append({"to": to, "body": body, "key": idempotency_key})
        return SmsSendResult(message_id=f"msg_{len(self.sends)}")

    def status(self, message_id: str) -> dict[str, object]:
        return {"message_id": message_id, "status": "delivered"}


def campaign() -> CampaignRequest:
    return CampaignRequest(
        campaign_id="repeat-buyers-june",
        messages=[
            CampaignMessage(
                recipient_id="buyer-17",
                to="+14155550117",
                body="Northstar Goods: your order history offer is ready.",
            ),
            CampaignMessage(
                recipient_id="buyer-23",
                to="+14155550123",
                body="Northstar Goods: your order history offer is ready.",
            ),
        ],
    )


def test_only_active_tenant_can_send_and_each_message_keeps_its_identity() -> None:
    sms = RecordingSms()
    manager = CampaignManager(sms)
    manager.onboard(TenantCreate(tenant_id="northstar", storefront_name="Northstar Goods"))

    with pytest.raises(PermissionError):
        manager.send_campaign("northstar", campaign())
    assert sms.sends == []

    manager.change_state("northstar", TenantState.ACTIVE)
    receipt = manager.send_campaign("northstar", campaign())

    assert [item.message_id for item in receipt.accepted] == ["msg_1", "msg_2"]
    assert [item["key"] for item in sms.sends] == [
        "northstar:repeat-buyers-june:buyer-17",
        "northstar:repeat-buyers-june:buyer-23",
    ]

    manager.change_state("northstar", TenantState.SUSPENDED)
    with pytest.raises(PermissionError):
        manager.send_campaign("northstar", campaign())
    assert len(sms.sends) == 2

