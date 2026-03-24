const button = document.getElementById("weather-button");
const status = document.getElementById("status");
const result = document.getElementById("weather-result");
const locationLabel = document.getElementById("location");
const summary = document.getElementById("summary");
const temperature = document.getElementById("temperature");
const feelsLike = document.getElementById("feels-like");
const wind = document.getElementById("wind");
const aiSummary = document.getElementById("ai-summary");

const WEATHER_CODES = {
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
};

const US_STATE_ABBREVIATIONS = {
  Alabama: "AL",
  Alaska: "AK",
  Arizona: "AZ",
  Arkansas: "AR",
  California: "CA",
  Colorado: "CO",
  Connecticut: "CT",
  Delaware: "DE",
  Florida: "FL",
  Georgia: "GA",
  Hawaii: "HI",
  Idaho: "ID",
  Illinois: "IL",
  Indiana: "IN",
  Iowa: "IA",
  Kansas: "KS",
  Kentucky: "KY",
  Louisiana: "LA",
  Maine: "ME",
  Maryland: "MD",
  Massachusetts: "MA",
  Michigan: "MI",
  Minnesota: "MN",
  Mississippi: "MS",
  Missouri: "MO",
  Montana: "MT",
  Nebraska: "NE",
  Nevada: "NV",
  "New Hampshire": "NH",
  "New Jersey": "NJ",
  "New Mexico": "NM",
  "New York": "NY",
  "North Carolina": "NC",
  "North Dakota": "ND",
  Ohio: "OH",
  Oklahoma: "OK",
  Oregon: "OR",
  Pennsylvania: "PA",
  "Rhode Island": "RI",
  "South Carolina": "SC",
  "South Dakota": "SD",
  Tennessee: "TN",
  Texas: "TX",
  Utah: "UT",
  Vermont: "VT",
  Virginia: "VA",
  Washington: "WA",
  "West Virginia": "WV",
  Wisconsin: "WI",
  Wyoming: "WY",
  "District of Columbia": "DC",
};

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function showWeather(data) {
  locationLabel.textContent = data.location || "Location unavailable";
  summary.textContent = data.summary;
  temperature.textContent = `${data.temperature_f} F`;
  feelsLike.textContent = `${data.feels_like_f} F`;
  wind.textContent = `${data.wind_mph} mph`;
  aiSummary.hidden = true;
  aiSummary.textContent = "";
  result.hidden = false;
}

function showAiSummary(text) {
  aiSummary.textContent = text;
  aiSummary.hidden = false;
}

async function fetchWeatherFromOpenMeteo(latitude, longitude) {
  const params = new URLSearchParams({
    latitude,
    longitude,
    current: "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
    hourly: "temperature_2m,weather_code,precipitation_probability",
    daily: "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    temperature_unit: "fahrenheit",
    wind_speed_unit: "mph",
    timezone: "auto",
  });
  const response = await fetch(
    `https://api.open-meteo.com/v1/forecast?${params.toString()}`,
  );

  if (!response.ok) {
    throw new Error("Unable to fetch weather right now.");
  }

  const payload = await response.json();
  const current = payload.current;

  if (!current) {
    throw new Error("Weather data was unavailable for this location.");
  }

  const daily = payload.daily || {};
  const progression = buildProgression(payload, current.time);

  return {
    summary: WEATHER_CODES[current.weather_code] || "Current conditions unavailable",
    temperature_f: current.temperature_2m,
    feels_like_f: current.apparent_temperature,
    wind_mph: current.wind_speed_10m,
    high_f: daily.temperature_2m_max?.[0] ?? null,
    low_f: daily.temperature_2m_min?.[0] ?? null,
    precipitation_probability_max:
      daily.precipitation_probability_max?.[0] ?? null,
    progression,
  };
}

async function fetchAiSummary(weatherData) {
  const response = await fetch("/api/weather-summary", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(weatherData),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Unable to generate an AI weather summary.");
  }

  return data.ai_summary;
}

function buildProgression(payload, currentTime) {
  const hourly = payload.hourly || {};
  const times = hourly.time || [];
  const temperatures = hourly.temperature_2m || [];
  const weatherCodes = hourly.weather_code || [];
  const precipitationProbabilities = hourly.precipitation_probability || [];

  if (!times.length) {
    return [];
  }

  let startIndex = times.indexOf(currentTime);
  if (startIndex === -1) {
    startIndex = 0;
  }

  const progression = [];
  for (let index = startIndex; index < Math.min(startIndex + 6, times.length); index += 1) {
    progression.push({
      time: times[index].slice(-5),
      temperature_f: temperatures[index],
      summary: WEATHER_CODES[weatherCodes[index]] || "Current conditions unavailable",
      precipitation_probability: precipitationProbabilities[index],
    });
  }

  return progression;
}

function formatState(address) {
  const stateCode = address["ISO3166-2-lvl4"];
  if (stateCode && stateCode.startsWith("US-")) {
    return stateCode.split("-")[1];
  }

  if (address.country_code === "us" && address.state) {
    return US_STATE_ABBREVIATIONS[address.state] || address.state;
  }

  return address.state || address.region || address.county || "";
}

function formatLocation(address) {
  const city =
    address.city ||
    address.town ||
    address.village ||
    address.hamlet ||
    address.municipality ||
    address.county;
  const state = formatState(address);

  if (city && state) {
    return `${city}, ${state}`;
  }

  if (city) {
    return city;
  }

  if (state) {
    return state;
  }

  return "Location unavailable";
}

async function fetchLocationName(latitude, longitude) {
  const params = new URLSearchParams({
    lat: latitude,
    lon: longitude,
    format: "jsonv2",
    addressdetails: "1",
  });
  const response = await fetch(
    `https://nominatim.openstreetmap.org/reverse?${params.toString()}`,
  );

  if (!response.ok) {
    throw new Error("Unable to resolve your location.");
  }

  const payload = await response.json();
  const address = payload.address || {};

  return formatLocation(address);
}

button.addEventListener("click", () => {
  result.hidden = true;

  if (!navigator.geolocation) {
    setStatus("Geolocation is not supported in this browser.", true);
    return;
  }

  setStatus("Waiting for location permission...");

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        setStatus("Fetching current weather...");
        let data;
        let location;

        data = await fetchWeatherFromOpenMeteo(
          position.coords.latitude,
          position.coords.longitude,
        );

        try {
          location = await fetchLocationName(
            position.coords.latitude,
            position.coords.longitude,
          );
        } catch (_error) {
          location = "Location unavailable";
        }

        data.location = location;
        showWeather(data);
        setStatus("Weather loaded. Writing a quick summary...");

        try {
          const generatedSummary = await fetchAiSummary(data);
          showAiSummary(generatedSummary);
          setStatus("Weather loaded.");
        } catch (_error) {
          setStatus("Weather loaded.");
        }
      } catch (error) {
        setStatus(error.message, true);
      }
    },
    () => {
      setStatus("Location access was denied or unavailable.", true);
    },
  );
});
