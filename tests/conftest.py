import asyncio
import pytest
import pytest_asyncio
from typing import Generator

@pytest.fixture(scope="session")
def event_loop():
    """세션 전체에서 유지되는 루프를 생성합니다."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def _shared_loop(event_loop):
    return event_loop