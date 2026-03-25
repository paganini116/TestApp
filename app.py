import os
import uuid

from flask import Flask, jsonify, render_template, request

from logging_utils import configure_logging
from openai_client import OpenAIServiceError, generate_weather_summary


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
    app.config.from_mapping(TESTING=False)
    logger = configure_logging()

    if test_config is not None:
        app.config.update(test_config)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/weather-summary", methods=["POST"])
    def weather_summary():
        payload = request.get_json(silent=True) or {}
        request_id = str(uuid.uuid4())
        location = payload.get("location", "your area")
        summary = payload.get("summary")
        temperature_f = payload.get("temperature_f")
        feels_like_f = payload.get("feels_like_f")
        wind_mph = payload.get("wind_mph")
        high_f = payload.get("high_f")
        low_f = payload.get("low_f")
        precipitation_probability_max = payload.get("precipitation_probability_max")
        progression = payload.get("progression", [])
        base_log = {
            "request_id": request_id,
            "route": "/api/weather-summary",
            "location": location,
            "progression_count": len(progression),
        }

        logger.info("weather_summary_request_started", extra=base_log)

        required_values = [summary, temperature_f, feels_like_f, wind_mph]
        if any(value is None for value in required_values):
            logger.warning(
                "weather_summary_validation_failed",
                extra=base_log,
            )
            return (
                jsonify({"error": "Weather summary, temperature, feels like, and wind are required."}),
                400,
            )

        try:
            ai_summary = generate_weather_summary(
                request_id=request_id,
                location=location,
                summary=summary,
                temperature_f=float(temperature_f),
                feels_like_f=float(feels_like_f),
                wind_mph=float(wind_mph),
                high_f=float(high_f) if high_f is not None else None,
                low_f=float(low_f) if low_f is not None else None,
                precipitation_probability_max=(
                    float(precipitation_probability_max)
                    if precipitation_probability_max is not None
                    else None
                ),
                progression=progression,
            )
        except (TypeError, ValueError):
            logger.warning(
                "weather_summary_invalid_numeric_values",
                extra=base_log,
            )
            return jsonify({"error": "Weather values must be valid numbers."}), 400
        except OpenAIServiceError as exc:
            logger.error(
                "weather_summary_generation_failed",
                extra={
                    **base_log,
                    "exception_type": type(exc).__name__,
                },
            )
            return jsonify({"error": str(exc)}), 502

        logger.info(
            "weather_summary_generated",
            extra=base_log,
        )

        return jsonify({"ai_summary": ai_summary})

    return app


app = create_app()
