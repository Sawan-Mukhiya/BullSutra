"""Factory for creating LLM chat models with fallback and fake support."""
import json
import re
from typing import Literal, Optional, Any
from bullsutra.core.config import settings
from bullsutra.agents.llm.schemas import BriefNarrative

class FakeNarrator:
    """Deterministic narrator for tests and offline CI runs."""
    def __init__(self, schema: Any = None):
        self.schema = schema

    def with_structured_output(self, schema: Any):
        return FakeNarrator(schema=schema)

    async def ainvoke(self, messages: Any) -> BriefNarrative:
        # Extract the input json from the user message
        content = ""
        for m in messages:
            if hasattr(m, "content"):
                content += str(m.content)
            elif isinstance(m, dict):
                content += str(m.get("content", ""))
            else:
                content += str(m)

        # Parse symbol and consensus if possible
        sym = "Security"
        label = "HOLD"
        score = 0.0
        conf = 0.0
        try:
            m_json = re.search(r"Input:\s*(\{.*\})", content, re.DOTALL)
            if m_json:
                data = json.loads(m_json.group(1))
                sym = data.get("symbol", sym)
                cons = data.get("consensus", {})
                label = cons.get("label", label)
                score = cons.get("score", score)
                conf = cons.get("confidence", conf)
        except Exception:
            pass

        return BriefNarrative(
            news=f"News sentiment for {sym} shows moderate coverage with steady signals.",
            fundamentals=f"Fundamentals for {sym} indicate stable quarterly financial performance.",
            technicals=f"Technicals for {sym} reflect consistent moving average patterns.",
            risk=f"Risk metrics for {sym} demonstrate balanced volatility and liquidity.",
            debate_summary=f"Debate resolved agent divergences into a final {label} consensus.",
            summary=f"Analysis of {sym} yields a {label} stance with consensus score {score:.2f} and confidence {conf:.2f}. Drivers and risks remain in normal ranges. Investors should account for market uncertainty.",
        )

class OpenAICompatChat:
    """Minimal OpenAI-compatible chat client (e.g. OmniRoute) using JSON mode.

    Avoids a langchain-openai dependency and the token overhead of tool schemas.
    """
    def __init__(self, model: str, base_url: str, api_key: str = "", schema: Any = None):
        self.model, self.base_url, self.api_key, self.schema = model, base_url.rstrip("/"), api_key, schema

    def with_structured_output(self, schema: Any):
        return OpenAICompatChat(self.model, self.base_url, self.api_key, schema)

    async def ainvoke(self, messages: Any) -> Any:
        import httpx
        msgs = list(messages)
        if self.schema is not None:
            fields = ", ".join(self.schema.model_fields)
            msgs[0] = {**msgs[0], "content": f"{msgs[0]['content']}\nReturn one JSON object with keys: {fields}."}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={"model": self.model, "messages": msgs, "temperature": 0.0,
                      "response_format": {"type": "json_object"}},
            )
            r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        if self.schema is None:
            return content
        m = re.search(r"\{.*\}", content, re.DOTALL)  # tolerate ```json fences
        return self.schema.model_validate_json(m.group(0) if m else content)

def get_llm(role: Literal["primary", "fallback"]) -> Any:
    """Return configured ChatModel or None if not configured."""
    if role == "primary":
        provider = settings.LLM_PROVIDER
        model = settings.LLM_MODEL
    else:
        provider = settings.LLM_FALLBACK_PROVIDER
        model = settings.LLM_FALLBACK_MODEL

    if provider == "fake":
        return FakeNarrator()

    if provider == "gemini":
        if not settings.GOOGLE_API_KEY:
            return None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=0.0,
                timeout=settings.LLM_TIMEOUT_SECONDS,
                max_retries=0,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        except Exception:
            return None

    if provider == "omniroute":
        return OpenAICompatChat(model, settings.OMNIROUTE_BASE_URL, settings.OMNIROUTE_API_KEY)

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.0,
            )
        except Exception:
            return None

    return None
