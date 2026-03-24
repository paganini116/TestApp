import os

from flask import Flask, jsonify, render_template, request

from db import close_db, get_db, init_db
from openai_client import OpenAIServiceError, generate_weather_summary
from weather import WeatherServiceError, fetch_current_weather


def load_env_file(root_path):
    env_path = os.path.join(root_path, ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def create_app(test_config=None):
    app = Flask(__name__)
    load_env_file(app.root_path)

    default_database_path = os.path.join(app.instance_path, "weather.db")
    database_path = os.environ.get("WEATHER_DB_PATH", default_database_path)

    app.config.from_mapping(
        DATABASE=database_path,
        TESTING=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/weather", methods=["POST"])
    def weather():
        payload = request.get_json(silent=True) or {}
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")

        if latitude is None or longitude is None:
            return jsonify({"error": "Latitude and longitude are required."}), 400

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return jsonify({"error": "Latitude and longitude must be numbers."}), 400

        try:
            weather_data = fetch_current_weather(latitude, longitude)
        except WeatherServiceError as exc:
            return jsonify({"error": str(exc)}), 502

        db = get_db()
        db.execute(
            """
            INSERT INTO weather_requests (latitude, longitude, summary)
            VALUES (?, ?, ?)
            """,
            (
                latitude,
                longitude,
                weather_data["summary"],
            ),
        )
        db.commit()

        return jsonify(weather_data)

    @app.route("/api/weather-summary", methods=["POST"])
    def weather_summary():
        payload = request.get_json(silent=True) or {}
        location = payload.get("location", "your area")
        summary = payload.get("summary")
        temperature_f = payload.get("temperature_f")
        feels_like_f = payload.get("feels_like_f")
        wind_mph = payload.get("wind_mph")

        required_values = [summary, temperature_f, feels_like_f, wind_mph]
        if any(value is None for value in required_values):
            return (
                jsonify({"error": "Weather summary, temperature, feels like, and wind are required."}),
                400,
            )

        try:
            ai_summary = generate_weather_summary(
                location=location,
                summary=summary,
                temperature_f=float(temperature_f),
                feels_like_f=float(feels_like_f),
                wind_mph=float(wind_mph),
            )
        except (TypeError, ValueError):
            return jsonify({"error": "Weather values must be valid numbers."}), 400
        except OpenAIServiceError as exc:
            return jsonify({"error": str(exc)}), 502

        return jsonify({"ai_summary": ai_summary})

    return app


app = create_app()
