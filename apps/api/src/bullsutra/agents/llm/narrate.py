"""LLM narrative generation with number guard, caching, and graceful fallback."""
import asyncio
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, Set
import structlog
from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.core.config import settings
from bullsutra.agents.constants import PROMPT_VERSION
from bullsutra.agents.llm.schemas import BriefNarrative
from bullsutra.agents.llm.factory import get_llm
from bullsutra.db.repositories.llm_cache import get_cached, set_cache

logger = structlog.get_logger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "v1"

@lru_cache(maxsize=1)
def _load_prompts() -> Tuple[str, Template]:
    sys_file = PROMPTS_DIR / "narrate_system.md"
    user_file = PROMPTS_DIR / "narrate_user.md.j2"
    with open(sys_file, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    with open(user_file, "r", encoding="utf-8") as f:
        user_tmpl = Template(f.read())
    return sys_prompt, user_tmpl

def _round_floats(obj: Any, nd: int = 3) -> Any:
    """Round floats recursively: fewer prompt tokens and a tighter number guard."""
    if isinstance(obj, float):
        return round(obj, nd)
    if isinstance(obj, dict):
        return {k: _round_floats(v, nd) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(v, nd) for v in obj]
    return obj

def _extract_numbers(text: str) -> List[float]:
    """Extract numeric values from a string."""
    matches = re.findall(r"\b\d+(?:[.,]\d+)?\b", text)
    nums = []
    for m in matches:
        clean = m.replace(",", "")
        try:
            nums.append(float(clean))
        except ValueError:
            pass
    return nums

def _validate_number_guard(text: str, allowed_numbers: Set[float]) -> bool:
    """Validate that every number in text is present in the input JSON."""
    nums = _extract_numbers(text)
    for n in nums:
        # Check if n or n/100 or n*100 is within 1% tolerance of any allowed number
        matched = False
        for allowed in allowed_numbers:
            tol = 0.01 * max(1.0, abs(allowed))
            if (
                abs(n - allowed) <= tol
                or abs(n - (allowed * 100.0)) <= tol
                or abs(n - (allowed / 100.0)) <= tol
            ):
                matched = True
                break
        if not matched:
            return False
    return True

async def narrate(
    brief_input: Dict[str, Any],
    db: Optional[AsyncSession] = None,
) -> Tuple[Optional[BriefNarrative], Optional[str]]:
    """Generate LLM narrative for a brief.
    
    Returns (BriefNarrative | None, model_name_used | None).
    Never raises an exception.
    """
    input_json_str = json.dumps(_round_floats(brief_input), sort_keys=True, separators=(",", ":"), default=str)
    allowed_numbers = set(_extract_numbers(input_json_str))

    primary_model_name = f"{settings.LLM_PROVIDER}:{settings.LLM_MODEL}"
    cache_key = hashlib.sha256(
        f"{PROMPT_VERSION}:{primary_model_name}:{input_json_str}".encode("utf-8")
    ).hexdigest()

    # Check cache if db session available
    if db is not None:
        try:
            cached_val = await get_cached(db, cache_key, primary_model_name)
            if cached_val:
                return BriefNarrative(**cached_val), primary_model_name
        except Exception as e:
            logger.warning("llm_cache_read_error", error=str(e))

    sys_prompt, user_tmpl = _load_prompts()
    user_prompt = user_tmpl.render(input_json=input_json_str)

    # Helper to call and guard
    async def try_call_model(llm: Any, model_name: str) -> Optional[BriefNarrative]:
        structured_llm = llm.with_structured_output(BriefNarrative)
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        narrative: Optional[BriefNarrative] = None
        for attempt in range(1 + settings.LLM_MAX_RETRIES):
            try:
                res = await asyncio.wait_for(
                    structured_llm.ainvoke(messages),
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
                if isinstance(res, BriefNarrative):
                    narrative = res
                elif isinstance(res, dict):
                    narrative = BriefNarrative(**res)
                break
            except Exception as e:
                logger.warning("llm_invoke_attempt_failed", attempt=attempt, model=model_name, error=str(e))
                if attempt < settings.LLM_MAX_RETRIES:
                    await asyncio.sleep(1.0 if attempt == 0 else 3.0)

        if narrative is None:
            return None

        # Number guard check
        fields = ["news", "fundamentals", "technicals", "risk", "summary"]
        if narrative.debate_summary:
            fields.append("debate_summary")

        guard_failed = any(
            not _validate_number_guard(getattr(narrative, f), allowed_numbers)
            for f in fields
            if getattr(narrative, f)
        )

        if guard_failed:
            logger.info("llm_number_guard_triggered", model=model_name)
            # Retry once with explicit instruction
            retry_messages = list(messages) + [
                {"role": "assistant", "content": narrative.model_dump_json()},
                {
                    "role": "user",
                    "content": "Your previous answer used numbers not present in the input. Use only numbers from the input.",
                },
            ]
            try:
                narrative_retry = await asyncio.wait_for(
                    structured_llm.ainvoke(retry_messages),
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
                if isinstance(narrative_retry, dict):
                    narrative_retry = BriefNarrative(**narrative_retry)
                
                if isinstance(narrative_retry, BriefNarrative):
                    # Check fields again, set failing fields to None on narrative_retry
                    for f in fields:
                        val = getattr(narrative_retry, f)
                        if val and not _validate_number_guard(val, allowed_numbers):
                            setattr(narrative_retry, f, None)
                    narrative = narrative_retry
                else:
                    for f in fields:
                        val = getattr(narrative, f)
                        if val and not _validate_number_guard(val, allowed_numbers):
                            setattr(narrative, f, None)
            except Exception:
                # Set failing fields to None on original narrative
                for f in fields:
                    val = getattr(narrative, f)
                    if val and not _validate_number_guard(val, allowed_numbers):
                        setattr(narrative, f, None)

        return narrative

    # 1. Try primary model
    primary_llm = get_llm("primary")
    if primary_llm is not None:
        try:
            res = await try_call_model(primary_llm, primary_model_name)
            if res is not None:
                if db is not None:
                    try:
                        await set_cache(db, cache_key, primary_model_name, res.model_dump(mode="json"))
                    except Exception as e:
                        logger.warning("llm_cache_write_error", error=str(e))
                return res, primary_model_name
        except Exception as e:
            logger.warning("primary_llm_failed", error=str(e))

    # 2. Try fallback model (skip if identical to primary: it would just repeat the same failure)
    fallback_model_name = f"{settings.LLM_FALLBACK_PROVIDER}:{settings.LLM_FALLBACK_MODEL}"
    fallback_llm = get_llm("fallback") if fallback_model_name != primary_model_name else None
    if fallback_llm is not None:
        try:
            res = await try_call_model(fallback_llm, fallback_model_name)
            if res is not None:
                if db is not None:
                    try:
                        await set_cache(db, cache_key, primary_model_name, res.model_dump(mode="json"))
                    except Exception as e:
                        logger.warning("llm_cache_write_error", error=str(e))
                return res, fallback_model_name
        except Exception as e:
            logger.warning("fallback_llm_failed", error=str(e))

    return None, None
