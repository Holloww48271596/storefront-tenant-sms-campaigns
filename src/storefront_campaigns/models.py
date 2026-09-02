from enum import Enum

from pydantic import BaseModel, Field


class TenantState(str, Enum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class TenantCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=64)
    storefront_name: str = Field(min_length=1, max_length=80)


class TenantView(TenantCreate):
    state: TenantState


class TenantStateChange(BaseModel):
    state: TenantState


class CampaignMessage(BaseModel):
    recipient_id: str = Field(min_length=1, max_length=64)
    to: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    body: str = Field(min_length=1, max_length=480)


class CampaignRequest(BaseModel):
    campaign_id: str = Field(min_length=1, max_length=64)
    messages: list[CampaignMessage] = Field(min_length=1, max_length=100)


class MessageReceipt(BaseModel):
    recipient_id: str
    message_id: str


class CampaignReceipt(BaseModel):
    tenant_id: str
    campaign_id: str
    accepted: list[MessageReceipt]


class MessageStatus(BaseModel):
    message_id: str
    status: str

