from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RuntimeEndpointUpdateRequest(BaseModel):
    base_url: str
    model: str
    provider: str


class RuntimeEndpointResponse(BaseModel):
    name: str
    provider: str
    model: str
    base_url: str
    health_status: str | None = None
    updated_at: datetime


class RuntimeEndpointCheckResponse(BaseModel):
    endpoint: str
    status: str  # ok | error
    detail: str | None = None
    checked_at: datetime
