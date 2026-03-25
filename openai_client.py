import json
import os
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi

from logging_utils import configure_logging


class OpenAIServiceError(Exception):
    pass


MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 0.75


def _http_error_message(status_code):
    if status_code in {401, 403}:
        return "The server could not authenticate with OpenAI. Check the API key configuration."
    if status_code == 429:
        return "OpenAI rate limits were reached. Please try again in a moment."
    if 500 <= status_code <= 599:
        return "OpenAI is temporarily unavailable. Please try again shortly."

    return "OpenAI returned an unexpected error while generating the summary."


def _is_retryable_exception(exc):
    if isinstance(exc, HTTPError):
        return exc.code == 429 or 500 <= exc.code <= 599
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, URLError):
        return True

    return False


def _log_request_failure(logger, log_context, exc):
    extra = {
        **log_context,
        "exception_type": type(exc).__name__,
    }
    if isinstance(exc, HTTPError):
        extra["status_code"] = exc.code

    logger.error("openai_weather_summary_request_failed", extra=extra)


def _raise_mapped_openai_error(logger, log_context, exc):
    if isinstance(exc, HTTPError):
        raise OpenAIServiceError(_http_error_message(exc.code)) from exc
    if isinstance(exc, TimeoutError):
        raise OpenAIServiceError("OpenAI took too long to respond. Please try again.") from exc
    if isinstance(exc, URLError):
        raise OpenAIServiceError(
            "The server could not reach OpenAI. Check network connectivity and try again."
        ) from exc
    if isinstance(exc, json.JSONDecodeError):
        raise OpenAIServiceError("OpenAI returned an invalid or empty summary response.") from exc

    logger.error(
        "openai_weather_summary_request_failed",
        extra={
            **log_context,
            "exception_type": type(exc).__name__,
        },
    )
    raise OpenAIServiceError("OpenAI returned an unexpected error while generating the summary.") from exc


def _extract_output_text(payload):
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "").strip()

    return ""


def generate_weather_summary(
    request_id,
    location,
    summary,
    temperature_f,
    feels_like_f,
    wind_mph,
    high_f=None,
    low_f=None,
    precipitation_probability_max=None,
    progression=None,
):
    logger = configure_logging()
    log_context = {
        "request_id": request_id,
        "location": location,
        "progression_count": len(progression or []),
        "temperature_f": temperature_f,
        "feels_like_f": feels_like_f,
        "wind_mph": wind_mph,
        "high_f": high_f,
        "low_f": low_f,
        "precipitation_probability_max": precipitation_probability_max,
    }
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error(
            "openai_api_key_missing",
            extra=log_context,
        )
        raise OpenAIServiceError("OpenAI API key is not configured on the server.")

    progression_lines = []
    for point in progression or []:
        progression_lines.append(
            (
                f"{point['time']}: {point['summary']}, "
                f"{point['temperature_f']} F, "
                f"{point['precipitation_probability']}% rain chance"
            )
        )

    prompt = (
        "You are writing a short, friendly weather note for a simple web app. "
        "Keep it to two sentences max. Mention the location naturally and explain "
        "how the weather is likely to progress through the rest of the day based "
        "on the forecast details.\n\n"
        f"Location: {location}\n"
        f"Condition: {summary}\n"
        f"Temperature (F): {temperature_f}\n"
        f"Feels like (F): {feels_like_f}\n"
        f"Wind (mph): {wind_mph}\n"
        f"High today (F): {high_f}\n"
        f"Low today (F): {low_f}\n"
        f"Max precipitation probability today (%): {precipitation_probability_max}\n"
        "Upcoming hourly progression:\n"
        + "\n".join(progression_lines)
    )

    body = json.dumps(
        {
            "model": "gpt-5",
            "input": prompt,
            "text": {"verbosity": "low"},
        }
    ).encode("utf-8")
    request = Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    logger.info(
        "openai_weather_summary_request_started",
        extra=log_context,
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urlopen(request, timeout=20, context=ssl_context) as response:
                payload = json.load(response)
            break
        except (HTTPError, TimeoutError, URLError, json.JSONDecodeError) as exc:
            _log_request_failure(logger, log_context, exc)
            if not _is_retryable_exception(exc) or attempt == MAX_ATTEMPTS:
                _raise_mapped_openai_error(logger, log_context, exc)

            logger.warning(
                "openai_weather_summary_retry_scheduled",
                extra={
                    **log_context,
                    "attempt": attempt,
                    "max_attempts": MAX_ATTEMPTS,
                    "exception_type": type(exc).__name__,
                    **({"status_code": exc.code} if isinstance(exc, HTTPError) else {}),
                },
            )
            time.sleep(RETRY_DELAY_SECONDS)

    output_text = _extract_output_text(payload)
    if not output_text:
        logger.error(
            "openai_weather_summary_empty_response",
            extra=log_context,
        )
        raise OpenAIServiceError("OpenAI returned an invalid or empty summary response.")

    logger.info(
        "openai_weather_summary_request_completed",
        extra=log_context,
    )
    return output_text
