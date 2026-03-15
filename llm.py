from __future__ import annotations

from typing import Any

from crewai.llms.base_llm import BaseLLM
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class GoogleGenaiLLM(BaseLLM):
    """CrewAI BaseLLM wrapper backed by langchain-google-genai."""

    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float | None = None,
        stop: list[str] | None = None,
        fallback_models: list[str] | None = None,
    ) -> None:
        super().__init__(model, temperature, stop)
        self.api_key = api_key
        self.fallback_models = [m for m in (fallback_models or []) if m and m != model]
        self.client = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
        )

    def _invoke(self, model: str, messages: list[Any]) -> str:
        if model != self.model:
            client = ChatGoogleGenerativeAI(
                model=model,
                temperature=self.temperature,
                google_api_key=self.api_key,
            )
            response = client.invoke(messages)
            # Persist the working model/client for subsequent calls.
            self.model = model
            self.client = client
        else:
            response = self.client.invoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    if "text" in part:
                        parts.append(str(part["text"]))
                    elif "content" in part:
                        parts.append(str(part["content"]))
                    else:
                        parts.append(str(part))
                else:
                    parts.append(str(part))
            return "".join(parts).strip()
        if isinstance(content, str):
            return content
        return str(content)

    def call(
        self,
        messages: str | list[dict[str, str]],
        tools: list[dict] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
    ) -> str:
        lc_messages: list[Any]
        if isinstance(messages, str):
            lc_messages = [HumanMessage(content=messages)]
        else:
            lc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))

        try:
            return self._invoke(self.model, lc_messages)
        except Exception as exc:
            msg = str(exc)
            should_fallback = (
                "NOT_FOUND" in msg
                or "not found" in msg
                or "RESOURCE_EXHAUSTED" in msg
                or "Quota exceeded" in msg
                or "429" in msg
            )
            if should_fallback and self.fallback_models:
                for fallback in self.fallback_models:
                    try:
                        return self._invoke(fallback, lc_messages)
                    except Exception:
                        continue
            raise

    def supports_function_calling(self) -> bool:
        return False
