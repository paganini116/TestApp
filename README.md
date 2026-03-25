# Local Weather Flask App

This project is a minimal Flask web app that asks the user for browser
location access, fetches weather directly in the browser from Open-Meteo,
and uses OpenAI to generate a short weather summary.

## Goals

- Keep the stack minimal and easy to understand.
- Use Flask and plain JavaScript with minimal backend surface area.
- Optimize for speed of setup over extra features.

## Project Structure

- `app.py`: Flask app entry point and routes.
- `openai_client.py`: OpenAI Responses API integration for summary text.
- `templates/index.html`: Single-page UI with one button.
- `static/app.js`: Browser geolocation, Open-Meteo fetch, and summary logic.
- `static/styles.css`: Minimal styling.
- `tests/test_app.py`: Basic route and API coverage.
- `AGENTS.md`: Repository-specific working instructions.

## Milestones

1. Scaffold the Flask app and single-page UI.
2. Add browser geolocation permission flow with one button.
3. Fetch weather directly from Open-Meteo in the browser.
4. Add OpenAI-generated weather summaries.
5. Add tests for the page and summary endpoint.
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

The app reads `.env` directly for the OpenAI API key used by the summary route.

## Run the App

```bash
flask --app app --debug run
```

Then open the local Flask URL in your browser and click the main button.

## Run Tests

```bash
pytest tests/
```

## Future Improvements

- Add reverse geocoding to show the city name.
- Add better loading and error states.
- Add deployment instructions.
