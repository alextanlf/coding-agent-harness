# tests/test_mechanism_demo.py
import pytest
import asyncio
from demo.mechanism_demo import run_demo

@pytest.mark.asyncio
async def test_demo_runs_without_error():
    results = await run_demo()
    assert isinstance(results, list)
    assert len(results) == 3

@pytest.mark.asyncio
async def test_demo_guardrail_blocks():
    results = await run_demo()
    demo1 = results[0]
    assert demo1["name"] == "guardrail_block"
    assert demo1["blocked"] is True

@pytest.mark.asyncio
async def test_demo_sandbox_blocks():
    results = await run_demo()
    demo2 = results[1]
    assert demo2["name"] == "sandbox_block"
    assert demo2["blocked"] is True

@pytest.mark.asyncio
async def test_demo_hitl_flow():
    results = await run_demo()
    demo3 = results[2]
    assert demo3["name"] == "hitl_flow"
    assert demo3["state"] == "approved"
