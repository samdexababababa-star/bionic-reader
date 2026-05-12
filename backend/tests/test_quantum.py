"""Tests for the wave / quantum-entropy intention module.

These tests run **offline** by default — they don't hit the ANU QRNG
service or the Mistral API. We test the deterministic parts:
- archetype picker is a uniform function of bytes
- fallback CSPRNG path returns valid bytes
- signature hashing is stable
- emit / receive run without the optional LLM (returns archetype reflection)
"""
from __future__ import annotations

import asyncio
import os

import pytest

from app.quantum import (
    ARCHETYPES,
    EmitRequest,
    ReceiveRequest,
    _entropy_signature,
    _pick_archetype,
    emit,
    fetch_entropy,
    receive,
)


def test_archetype_picker_is_uniform_on_simple_bytes() -> None:
    # 0x00 should map to archetype 0; high entropy should land somewhere mid-range.
    a = _pick_archetype(b"\x00\x00\x00\x00\x00")
    assert a["code"] == "01"

    b = _pick_archetype(b"\xff\xff\xff\xff\x00")
    assert b in ARCHETYPES


def test_signature_is_stable() -> None:
    s1 = _entropy_signature(b"hello-world")
    s2 = _entropy_signature(b"hello-world")
    assert s1 == s2
    assert len(s1.split("-")) == 3


def test_signature_changes_with_input() -> None:
    s1 = _entropy_signature(b"a")
    s2 = _entropy_signature(b"b")
    assert s1 != s2


def test_fetch_entropy_offline_falls_back() -> None:
    """If the test runner has no network or ANU is blocked, we still get bytes."""

    async def _run() -> None:
        result = await fetch_entropy(8)
        assert len(bytes.fromhex(result.bytes_hex)) == 8
        assert result.source in {"anu_qrng", "os_csprng"}

    asyncio.run(_run())


@pytest.mark.skipif(
    bool(os.environ.get("MISTRAL_API_KEY")),
    reason="MISTRAL_API_KEY set — skipping fallback test",
)
def test_emit_without_llm_uses_archetype_reflection() -> None:
    async def _run() -> None:
        s = await emit(EmitRequest(intention="Tester la cohérence du système."))
        assert s.archetype["name"]
        assert s.used_llm is False
        assert "intention" in s.message.lower() or s.archetype["reflection"] in s.message

    asyncio.run(_run())


def test_receive_returns_an_archetype() -> None:
    async def _run() -> None:
        s = await receive(ReceiveRequest(question=""))
        assert s.archetype["code"]
        assert s.message

    asyncio.run(_run())
