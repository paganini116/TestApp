# Local Weather Flask App

This project is a minimal Flask web app that asks the user for browser
location access and shows current local weather from Open-Meteo.

## Goals

- Keep the stack minimal and easy to understand.
- Use Flask, SQLite, and plain JavaScript.
- Optimize for speed of setup over extra features.

## Project Structure

- `app.py`: Flask app entry point and routes.
- `db.py`: Minimal SQLite connection and initialization helpers.
- `weather.py`: Open-Meteo integration and weather formatting.
- `templates/index.html`: Single-page UI with one button.
- `static/app.js`: Browser geolocation and fetch logic.
- `static/styles.css`: Minimal styling.
- `tests/test_app.py`: Basic route and API coverage.
- `AGENTS.md`: Repository-specific working instructions.

## Milestones

1. Scaffold the Flask app and single-page UI.
2. Add browser geolocation permission flow with one button.
3. Connect the Flask backend to Open-Meteo.
4. Add minimal SQLite scaffolding for request history.
5. Add tests for the page and weather endpoint.
6. Document setup, run steps, and future improvements.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment file:

```bash
cp .env.example .env
```

The app reads `.env` directly and uses `WEATHER_DB_PATH` for the SQLite file.

## Run the App

```bash
flask --app app --debug run
```

Then open the local Flask URL in your browser and click `Get My Weather`.

## Run Tests

```bash
pytest tests/
```

## Future Improvements

- Persist and display recent weather lookups from SQLite.
- Add reverse geocoding to show the city name.
- Add better loading and error states.
- Add deployment instructions.
