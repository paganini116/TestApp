from unittest.mock import patch

import logging
import json
from urllib.error import HTTPError

import pytest

from app import create_app
from logging_utils import configure_logging
from openai_client import OpenAIServiceError, generate_weather_summary


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Click here to see the weather where you are" in response.data


def test_weather_summary_requires_weather_fields(client):
    response = client.post("/api/weather-summary", json={"location": "San Francisco, CA"})

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "Weather summary, temperature, feels like, and wind are required."
    )


def test_weather_summary_returns_ai_text(client):
    with patch(
        "app.generate_weather_summary",
        return_value=(
            "It feels bright and easygoing in San Francisco, CA today, and "
            "conditions should stay clear and comfortable into the afternoon."
        ),
    ):
        response = client.post(
            "/api/weather-summary",
            json={
                "location": "San Francisco, CA",
                "summary": "Clear sky",
                "temperature_f": 72.3,
                "feels_like_f": 73.0,
                "wind_mph": 5.2,
                "high_f": 77.0,
                "low_f": 56.0,
                "precipitation_probability_max": 12,
                "progression": [
                    {
                        "time": "13:00",
                        "temperature_f": 72.0,
                        "summary": "Clear sky",
                        "precipitation_probability": 0,
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "ai_summary": (
            "It feels bright and easygoing in San Francisco, CA today, and "
            "conditions should stay clear and comfortable into the afternoon."
        )
    }


def test_weather_summary_returns_502_on_openai_failure(client):
    with patch(
        "app.generate_weather_summary",
        side_effect=OpenAIServiceError("Unable to generate an AI weather summary right now."),
    ):
        response = client.post(
            "/api/weather-summary",
            json={
                "location": "San Francisco, CA",
                "summary": "Clear sky",
                "temperature_f": 72.3,
                "feels_like_f": 73.0,
                "wind_mph": 5.2,
            },
        )

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "Unable to generate an AI weather summary right now."
    }


def test_weather_summary_logs_request_lifecycle(client, caplog):
    logger = configure_logging()
    original_propagate = logger.propagate
    logger.propagate = True

    with patch(
        "app.generate_weather_summary",
        return_value="A bright day continues into the afternoon.",
    ):
        with caplog.at_level(logging.INFO, logger=logger.name):
            response = client.post(
                "/api/weather-summary",
                json={
                    "location": "San Francisco, CA",
                    "summary": "Clear sky",
                    "temperature_f": 72.3,
                    "feels_like_f": 73.0,
                    "wind_mph": 5.2,
                    "progression": [],
                },
            )

    logger.propagate = original_propagate

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert "weather_summary_request_started" in messages
    assert "weather_summary_generated" in messages

    start_record = next(
        record
        for record in caplog.records
        if record.getMessage() == "weather_summary_request_started"
    )
    assert start_record.route == "/api/weather-summary"
    assert start_record.location == "San Francisco, CA"
    assert start_record.request_id


def test_openai_failure_logs_sanitized_metadata(capsys):
    with patch("openai_client.urlopen") as mocked_urlopen:
        mocked_urlopen.side_effect = HTTPError(
            url="https://api.openai.com/v1/responses",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-secret"}, clear=False):
            with pytest.raises(OpenAIServiceError):
                generate_weather_summary(
                    request_id="req-123",
                    location="San Francisco, CA",
                    summary="Clear sky",
                    temperature_f=72.3,
                    feels_like_f=73.0,
                    wind_mph=5.2,
                    high_f=77.0,
                    low_f=56.0,
                    precipitation_probability_max=12,
                    progression=[],
                )

    raw_output = capsys.readouterr().out
    log_lines = [
        json.loads(line)
        for line in raw_output.splitlines()
        if line.strip()
    ]
    events = [entry["event"] for entry in log_lines]
    assert "openai_weather_summary_request_started" in events
    assert "openai_weather_summary_request_failed" in events

    error_log = next(
        entry
        for entry in log_lines
        if entry["event"] == "openai_weather_summary_request_failed"
    )
    assert error_log["request_id"] == "req-123"
    assert error_log["status_code"] == 401
    assert error_log["exception_type"] == "HTTPError"
    assert "sk-test-secret" not in raw_output
