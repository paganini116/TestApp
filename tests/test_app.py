from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    database_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database_path),
        }
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Click here to see the weather where you are" in response.data


def test_weather_requires_coordinates(client):
    response = client.post("/api/weather", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Latitude and longitude are required."


def test_weather_returns_forecast(client):
    mocked_weather = {
        "summary": "Clear sky",
        "temperature_f": 72.3,
        "feels_like_f": 73.0,
        "wind_mph": 5.2,
    }

    with patch("app.fetch_current_weather", return_value=mocked_weather):
        response = client.post(
            "/api/weather",
            json={"latitude": 37.7749, "longitude": -122.4194},
        )

    assert response.status_code == 200
    assert response.get_json() == mocked_weather
