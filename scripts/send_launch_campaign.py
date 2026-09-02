import json
import os

from storefront_campaigns.campaign_manager import CampaignManager
from storefront_campaigns.infrai_sms import InfraiSmsClient
from storefront_campaigns.models import (
    CampaignMessage,
    CampaignRequest,
    TenantCreate,
    TenantState,
)


phone = os.environ.get("DEMO_PHONE")
if not phone:
    raise SystemExit("DEMO_PHONE is required")

manager = CampaignManager(InfraiSmsClient())
manager.onboard(TenantCreate(tenant_id="linen-shop", storefront_name="Linen Shop"))
manager.change_state("linen-shop", TenantState.ACTIVE)
receipt = manager.send_campaign(
    "linen-shop",
    CampaignRequest(
        campaign_id="summer-returning-buyers",
        messages=[
            CampaignMessage(
                recipient_id="customer-1042",
                to=phone,
                body="Linen Shop: your summer storefront preview is open.",
            )
        ],
    ),
)
statuses = manager.campaign_status([item.message_id for item in receipt.accepted])
print(json.dumps({"campaign": receipt.model_dump(), "statuses": [s.model_dump() for s in statuses]}, indent=2))

