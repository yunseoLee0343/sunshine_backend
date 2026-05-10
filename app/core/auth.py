"""Request-scoped user identification — TICKET-025.

MVP: reads X-User-Id header only; no JWT, OAuth, or external provider.

Design:
  - get_current_user returns None when the header is absent so existing
    query-param / request-body tests continue to work without modification.
  - resolve_user_id picks up the header value first, then falls back to the
    query-param or body value; 422 when neither is present.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> CurrentUser | None:
    """FastAPI dependency: parse X-User-Id header into CurrentUser.

    Returns None when the header is absent (routes fall back to their
    existing query-param / body user_id parameter for backward compat).
    Raises 422 when the header is present but is not a valid UUID.
    """
    if x_user_id is None:
        return None
    try:
        return CurrentUser(user_id=uuid.UUID(x_user_id))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="X-User-Id must be a valid UUID",
        )


def resolve_user_id(
    query_user_id: uuid.UUID | None,
    current_user: CurrentUser | None,
) -> uuid.UUID:
    """Return the effective user UUID: header wins, then query param.

    Raises 422 when neither source is present.
    """
    if current_user is not None:
        return current_user.user_id
    if query_user_id is not None:
        return query_user_id
    raise HTTPException(
        status_code=422,
        detail="user identity required: supply X-User-Id header or ?user_id= query param",
    )
