from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
import json


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherServiceError(Exception):
    pass


def _build_progression(payload, current_time):
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temperatures = hourly.get("temperature_2m") or []
    weather_codes = hourly.get("weather_code") or []
    precipitation_probabilities = hourly.get("precipitation_probability") or []

    if not times:
        return []

    try:
        start_index = times.index(current_time)
    except ValueError:
        start_index = 0

    progression = []
    for index in range(start_index, min(start_index + 6, len(times))):
        time_value = times[index]
        progression.append(
            {
                "time": time_value[-5:],
                "temperature_f": temperatures[index],
                "summary": WEATHER_CODES.get(
                    weather_codes[index],
                    "Current conditions unavailable",
                ),
                "precipitation_probability": precipitation_probabilities[index],
            }
        )

    return progression


def fetch_current_weather(latitude, longitude):
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{query}"

    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise WeatherServiceError(
            "Unable to fetch weather right now. The server could not reach "
            "Open-Meteo."
        ) from exc

    current = payload.get("current")
    daily = payload.get("daily") or {}
    if not current:
        raise WeatherServiceError("Weather data was unavailable for this location.")

    weather_code = current.get("weather_code")
    summary = WEATHER_CODES.get(weather_code, "Current conditions unavailable")
    progression = _build_progression(payload, current.get("time"))

    return {
        "summary": summary,
        "temperature_f": current.get("temperature_2m"),
        "feels_like_f": current.get("apparent_temperature"),
        "wind_mph": current.get("wind_speed_10m"),
        "high_f": (daily.get("temperature_2m_max") or [None])[0],
        "low_f": (daily.get("temperature_2m_min") or [None])[0],
        "precipitation_probability_max": (
            daily.get("precipitation_probability_max") or [None]
        )[0],
        "progression": progression,
    }
