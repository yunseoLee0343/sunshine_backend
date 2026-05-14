"""TICKET-053 — demo seed window validation tests."""

from __future__ import annotations


def test_demo_seed_uses_latest_not_1h() -> None:
    import app.seeds.demo_seed as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert 'window="latest"' in src or "window='latest'" in src
    assert 'window="1h"' not in src and "window='1h'" not in src


def test_demo_seed_has_24h_snapshot() -> None:
    import app.seeds.demo_seed as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert 'window="24h"' in src or "window='24h'" in src


def test_demo_seed_has_7d_snapshot() -> None:
    import app.seeds.demo_seed as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert 'window="7d"' in src or "window='7d'" in src
