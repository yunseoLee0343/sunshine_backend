"""Generic base repository providing common CRUD primitives."""

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Minimal CRUD wrapper around an AsyncSession for a single model type."""

    def __init__(self, model: type[T], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def add(self, instance: T) -> T:
        """Persist a new instance (flush to get server-assigned values)."""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get(self, id: uuid.UUID) -> T | None:
        """Fetch a single row by primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def delete(self, instance: T) -> None:
        """Delete an instance and flush."""
        await self.session.delete(instance)
        await self.session.flush()
