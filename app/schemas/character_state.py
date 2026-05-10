"""TICKET-004 — Character State API request / response schemas.

Strict ``model_config = "forbid"``: callers may NOT inject mood, expression,
status_message, or any other character field. They may only supply
``user_id`` + ``condition``; the deterministic engine resolves the rest.
"""

import uuid

from pydantic import BaseModel, ConfigDict

from app.domain.character_state import Condition
from app.schemas.plants import CharacterBlock


class CharacterStateUpdateRequest(BaseModel):
    """Request to deterministically update a plant's character state.

    ``extra="forbid"`` ensures callers cannot pass mood / expression /
    status_message / primary_action / reason_code directly.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID
    condition: Condition


class CharacterStateResponse(BaseModel):
    character: CharacterBlock
