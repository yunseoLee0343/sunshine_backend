from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime_endpoint import RuntimeEndpoint


class RuntimeEndpointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, name: str) -> RuntimeEndpoint | None:
        result = await self._session.execute(
            select(RuntimeEndpoint).where(
                RuntimeEndpoint.name == name,
                RuntimeEndpoint.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def upsert_endpoint(
        self,
        name: str,
        provider: str,
        model: str,
        base_url: str,
    ) -> RuntimeEndpoint:
        now = datetime.now(UTC)
        row = await self.get_active(name)
        if row is None:
            # Also check any inactive row with same name.
            result = await self._session.execute(
                select(RuntimeEndpoint).where(RuntimeEndpoint.name == name)
            )
            row = result.scalar_one_or_none()

        if row is None:
            row = RuntimeEndpoint(
                id=uuid.uuid4(),
                name=name,
                provider=provider,
                model=model,
                base_url=base_url,
                is_active=True,
                health_status="unknown",
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.provider = provider
            row.model = model
            row.base_url = base_url
            row.is_active = True
            row.health_status = "unknown"
            row.updated_at = now

        await self._session.flush()
        return row

    async def update_health(
        self,
        name: str,
        status: str,
        checked_at: datetime | None = None,
    ) -> None:
        row = await self.get_active(name)
        if row is None:
            return
        row.health_status = status
        row.last_health_check_at = checked_at or datetime.now(UTC)
        await self._session.flush()
