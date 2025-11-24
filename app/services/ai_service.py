import httpx
import logging
import asyncio
import random
from app.core.config import settings

logger = logging.getLogger("nexa.ai_service")


async def generate_reply_suggestions(context: dict) -> list:
    """
    Wrapper to call LLM provider with retries/backoff on 429 rate-limit responses.
    Returns list of suggestion strings. On repeated failure returns an empty list
    (so caller tasks don't crash).
    """
    if not settings.openai_api_key:
        logger.debug("No OpenAI API key configured; skipping suggestions.")
        return []

    prompt = (
        f"User message: {context['text']}\n"
        f"Sender: {context.get('sender_name')}\n"
        "Give 3 short reply suggestions in different tones (direct, friendly, professional)."
    )

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    async def _fetch_available_models(client: httpx.AsyncClient) -> set:
        try:
            resp = await client.get("https://api.openai.com/v1/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            models = {m.get("id") for m in data.get("data", []) if m.get("id")}
            return models
        except httpx.HTTPStatusError as exc:
            logger.warning("Failed to list OpenAI models: %s %s", exc.response.status_code, exc.response.text)
            return set()
        except Exception as exc:
            logger.warning("Error listing OpenAI models: %s", exc)
            return set()

    # Decide which model to send: prefer configured, otherwise pick first available from priority list
    preferred = settings.openai_model
    priority = [preferred, "gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"]

    backoff_base = 1.0
    # We'll attempt per-model retries, and move to the next candidate if rate-limited repeatedly.
    per_model_attempts = 3

    async with httpx.AsyncClient(timeout=30.0) as client:
        available_models = await _fetch_available_models(client)

        candidates = []
        if available_models:
            # prefer configured then other priority models that are available
            for m in priority:
                if not m:
                    continue
                if m in available_models and m not in candidates:
                    candidates.append(m)
            # then any available GPT-like models
            for m in sorted(available_models):
                if m.startswith("gpt") and m not in candidates:
                    candidates.append(m)
            # final fallback: any model
            for m in sorted(available_models):
                if m not in candidates:
                    candidates.append(m)
        else:
            logger.warning("Could not determine available OpenAI models; proceeding with configured model or default.")
            # fall back to configured or common defaults
            candidates = [preferred or "gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]

        logger.info("OpenAI available models count=%d", len(available_models) if available_models else 0)
        logger.info("Model candidates: %s", candidates)

        # Try candidates in order. For each model, try `per_model_attempts` with backoff.
        for chosen_model in candidates:
            body = {
                "model": chosen_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
            }

            for attempt in range(1, per_model_attempts + 1):
                try:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=body,
                        headers=headers,
                    )

                    # If successful, parse and return suggestions
                    resp.raise_for_status()
                    data = resp.json()
                    # parse response to get suggestions (implementation depends on model shape)
                    text = data["choices"][0]["message"]["content"]
                    suggestions = [s.strip() for s in text.split("\n") if s.strip()]
                    return suggestions

                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    # Rate limited: check Retry-After header if present
                    if status == 429:
                        retry_after = None
                        try:
                            retry_after = int(exc.response.headers.get("Retry-After"))
                        except Exception:
                            retry_after = None

                        if retry_after is not None:
                            wait = retry_after
                        else:
                            # exponential backoff with jitter
                            wait = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1)

                        logger.warning(
                            "OpenAI rate-limited (429) for model %s. attempt=%d/%d - backing off %.2f seconds",
                            chosen_model,
                            attempt,
                            per_model_attempts,
                            wait,
                        )
                        await asyncio.sleep(wait)
                        # if this was the last attempt for this model, break to try next model
                        if attempt == per_model_attempts:
                            logger.info("Exhausted retries for model %s, trying next candidate.", chosen_model)
                            break
                        continue
                    else:
                        # Other HTTP errors should be logged and abort retries overall
                        logger.error("OpenAI HTTP error for model %s: %s %s", chosen_model, status, exc.response.text)
                        return []

                except Exception as exc:  # network errors, timeouts, etc.
                    # transient network error — back off and retry a few times for this model
                    wait = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    logger.warning(
                        "OpenAI request failed for model %s (attempt %d/%d): %s — retrying in %.1fs",
                        chosen_model,
                        attempt,
                        per_model_attempts,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    # if this was the last attempt for this model, break to next candidate
                    if attempt == per_model_attempts:
                        logger.info("Exhausted retries for model %s due to errors, trying next candidate.", chosen_model)
                        break
                    continue

    logger.error("OpenAI suggestions unavailable: exhausted all model candidates")
    return []
