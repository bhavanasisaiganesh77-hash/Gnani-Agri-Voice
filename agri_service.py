"""One place that turns a farmer's question into an answer: rate limit -> prompt -> LLM provider."""

import agri_prompts as P
import languages as L
import llm_service as S
import ratelimit

HISTORY_TURNS = 10  # last messages sent as context (conversation memory)


class AnswerError(Exception):
    """kind: rate_limit | unavailable"""
    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


def answer(user_id, question_history: list, lang: L.Language, profile: dict, provider=None, max_tokens=800) -> str:
    """question_history: [{'role','content'}...] ending with the farmer's question."""
    if not ratelimit.allow(user_id, "llm"):
        raise AnswerError("rate_limit")
    provider = provider or S.get_provider()
    if not provider.is_configured():
        raise AnswerError("unavailable")
    msgs = [{"role": m["role"], "content": m["content"]} for m in question_history[-HISTORY_TURNS:]]
    while msgs and msgs[0]["role"] != "user":  # providers require the first turn to be the user's
        msgs.pop(0)
    try:
        return provider.generate(P.system_prompt(lang.name, P.profile_context(profile)), msgs, max_tokens=max_tokens)
    except S.LlmError as err:
        raise AnswerError("rate_limit" if err.kind == "rate_limit" else "unavailable")


def one_shot(user_id, request_text: str, lang: L.Language, profile: dict, image=None, provider=None, max_tokens=900):
    """Single-turn tasks (crop advice, disease check, scheme explanation)."""
    if not ratelimit.allow(user_id, "llm"):
        raise AnswerError("rate_limit")
    provider = provider or S.get_provider()
    if not provider.is_configured():
        raise AnswerError("unavailable")
    try:
        return provider.generate(P.system_prompt(lang.name, P.profile_context(profile)),
                                 [{"role": "user", "content": request_text}], max_tokens=max_tokens,
                                 image=image if provider.supports_images else None)
    except S.LlmError as err:
        raise AnswerError("rate_limit" if err.kind == "rate_limit" else "unavailable")
