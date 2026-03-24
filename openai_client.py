import json
import os
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


class OpenAIServiceError(Exception):
    pass


def _extract_output_text(payload):
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "").strip()

    return ""


def generate_weather_summary(
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
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIServiceError("OpenAI API key is missing.")

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

    try:
        with urlopen(request, timeout=20, context=ssl_context) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OpenAIServiceError("Unable to generate an AI weather summary right now.") from exc

    output_text = _extract_output_text(payload)
    if not output_text:
        raise OpenAIServiceError("OpenAI returned an empty weather summary.")

    return output_text
