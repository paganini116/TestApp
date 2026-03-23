import os

from flask import Flask, jsonify, render_template, request

from db import close_db, get_db, init_db
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

    return app


app = create_app()
