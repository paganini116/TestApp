from unittest.mock import patch

import pytest

from app import create_app


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
