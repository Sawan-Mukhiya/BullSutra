"""Tests for LLM layer number guard and FakeNarrator."""
import pytest
from bullsutra.agents.llm.schemas import BriefNarrative
from bullsutra.agents.llm.factory import FakeNarrator
from bullsutra.agents.llm.narrate import _validate_number_guard, _extract_numbers, narrate

def test_extract_numbers():
    text = "The score was 0.25 with 14% growth and 2,500 shares at Rs. 150.50"
    nums = _extract_numbers(text)
    assert 0.25 in nums
    assert 14.0 in nums
    assert 2500.0 in nums
    assert 150.5 in nums

def test_number_guard_validation():
    allowed = {0.25, 14.0, 150.0, 50.0}
    
    # Valid: numbers in allowed
    assert _validate_number_guard("Score 0.25 is moderate with 50% ratio.", allowed) is True
    
    # Valid percentage scale: 0.14 is allowed because 14.0 is in allowed
    assert _validate_number_guard("Return was 0.14.", allowed) is True

    # Invalid: 42 is not in allowed
    assert _validate_number_guard("Target price is 42.00.", allowed) is False

@pytest.mark.asyncio
async def test_fake_narrator_generation():
    fake = FakeNarrator()
    narrative = await fake.ainvoke([{"role": "user", "content": "Input: {\"symbol\": \"NABIL\", \"consensus\": {\"label\": \"BUY\", \"score\": 0.65, \"confidence\": 0.70}}" }])
    assert isinstance(narrative, BriefNarrative)
    assert "NABIL" in narrative.news
    assert "BUY" in narrative.summary
    assert len(narrative.summary) > 20
