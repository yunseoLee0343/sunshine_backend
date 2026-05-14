"""TICKET-048 — RetrievalRequest schema validation tests."""

from __future__ import annotations

import uuid

import pytest

from app.domain.retrieval import ALL_RAG_LAYERS
from app.schemas.retrieval import RetrievalRequest


def _base(**kwargs) -> dict:
    return {
        "request_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "question": "몬스테라 물주기",
        **kwargs,
    }


# ---------------------------------------------------------------------------
# Alias: query → question
# ---------------------------------------------------------------------------


def test_query_alias_accepted() -> None:
    data = {
        "request_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "query": "몬스테라 여름 물 주기",
    }
    req = RetrievalRequest(**data)
    assert req.question == "몬스테라 여름 물 주기"


def test_query_alias_does_not_appear_as_extra() -> None:

    # "query" is aliased away before extra="forbid" kicks in — must not raise
    data = {
        "request_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "query": "test",
    }
    req = RetrievalRequest(**data)
    assert req.question == "test"


def test_question_kwarg_still_works() -> None:
    req = RetrievalRequest(**_base())
    assert req.question == "몬스테라 물주기"


# ---------------------------------------------------------------------------
# Alias: selected_rag_layers → rag_layers
# ---------------------------------------------------------------------------


def test_selected_rag_layers_alias_accepted() -> None:
    data = {
        "request_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "question": "test",
        "selected_rag_layers": ["care_knowledge"],
    }
    req = RetrievalRequest(**data)
    assert req.rag_layers == ["care_knowledge"]


def test_rag_layers_kwarg_still_works() -> None:
    req = RetrievalRequest(**_base(rag_layers=["species_profile"]))
    assert req.rag_layers == ["species_profile"]


def test_rag_layers_default_is_all_layers() -> None:
    req = RetrievalRequest(**_base())
    assert set(req.rag_layers) == set(ALL_RAG_LAYERS)


# ---------------------------------------------------------------------------
# plant_id field
# ---------------------------------------------------------------------------


def test_plant_id_defaults_to_none() -> None:
    req = RetrievalRequest(**_base())
    assert req.plant_id is None


def test_plant_id_accepted() -> None:
    pid = uuid.uuid4()
    req = RetrievalRequest(**_base(plant_id=pid))
    assert req.plant_id == pid


# ---------------------------------------------------------------------------
# Invalid RAG layers
# ---------------------------------------------------------------------------


def test_companion_plant_layer_rejected() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(**_base(rag_layers=["companion_plant"]))


def test_user_memory_layer_rejected() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(**_base(rag_layers=["user_memory"]))


# ---------------------------------------------------------------------------
# Existing validations still hold
# ---------------------------------------------------------------------------


def test_empty_question_rejected() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(request_id=uuid.uuid4(), user_id=uuid.uuid4(), question="")


def test_extra_field_rejected() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(**_base(unknown_field="bad"))
