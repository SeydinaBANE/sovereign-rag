from __future__ import annotations

from sovereign_rag.ports.llm import LLMResponse


class MistralLLM:
    """Mistral chat-completion adapter (sovereign EU provider)."""

    def __init__(
        self,
        api_key: str,
        model: str = "mistral-large-latest",
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> None:
        from mistralai import Mistral

        self._client = Mistral(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def complete(self, system: str, prompt: str) -> LLMResponse:
        response = self._client.chat.complete(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            model=self._model,
        )
