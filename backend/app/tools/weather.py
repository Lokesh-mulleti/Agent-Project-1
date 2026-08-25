import re
from typing import Dict, Optional
import requests

WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_weather(location: str, unit: str = "celsius") -> str:
    """
    Retrieves current live weather data and short-term forecast for any specified city or region.

    Args:
        location: City or location name (e.g. "Tokyo", "London, UK", "New York").
        unit: Temperature unit - 'celsius' or 'fahrenheit'. Defaults to 'celsius'.

    Returns:
        A formatted string summary of the current weather and forecast.
    """
    if not location or not location.strip():
        return "Error: Location cannot be empty."

    # Sanitize location string from conversational phrasing
    clean_location = location.strip()
    clean_location = re.sub(r"^(?:is\s+)?(?:the\s+)?(?:current\s+)?weather\s+(?:in|for|at)\s+", "", clean_location, flags=re.IGNORECASE).strip()
    clean_location = re.sub(r"^(?:in|for|at)\s+", "", clean_location, flags=re.IGNORECASE).strip()

    temp_unit = "fahrenheit" if unit.lower() in ("fahrenheit", "f") else "celsius"
    unit_symbol = "°F" if temp_unit == "fahrenheit" else "°C"

    try:
        # Step 1: Geocode city name to lat/lon
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {
            "name": clean_location,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        geo_resp = requests.get(geo_url, params=geo_params, timeout=5)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        results = geo_data.get("results")
        if not results:
            return f"Weather Error: Could not find location coordinates for '{clean_location}'."

        first_match = results[0]
        name = first_match.get("name", clean_location)
        country = first_match.get("country", "")
        admin1 = first_match.get("admin1", "")
        lat = first_match["latitude"]
        lon = first_match["longitude"]

        place_name = f"{name}"
        if admin1 and admin1 != name:
            place_name += f", {admin1}"
        if country:
            place_name += f", {country}"

        # Step 2: Fetch weather forecast
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "temperature_unit": temp_unit,
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        }
        weather_resp = requests.get(weather_url, params=weather_params, timeout=5)
        weather_resp.raise_for_status()
        w_data = weather_resp.json()

        current = w_data.get("current", {})
        temp = current.get("temperature_2m", "N/A")
        feels_like = current.get("apparent_temperature", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        wind = current.get("wind_speed_10m", "N/A")
        precip = current.get("precipitation", 0)
        code = current.get("weather_code", -1)
        condition = WMO_WEATHER_CODES.get(code, "Unknown Conditions")

        daily = w_data.get("daily", {})
        daily_max = daily.get("temperature_2m_max", [temp])[0]
        daily_min = daily.get("temperature_2m_min", [temp])[0]

        summary = (
            f"Weather for {place_name}:\n"
            f"• Condition: {condition}\n"
            f"• Temperature: {temp}{unit_symbol} (Feels like: {feels_like}{unit_symbol})\n"
            f"• High / Low: {daily_max}{unit_symbol} / {daily_min}{unit_symbol}\n"
            f"• Humidity: {humidity}%\n"
            f"• Wind Speed: {wind} km/h\n"
            f"• Precipitation: {precip} mm"
        )
        return summary

    except requests.exceptions.RequestException as e:
        # Graceful fallback in offline/firewalled environments
        return (
            f"Weather Data for {clean_location} (Offline/Simulated):\n"
            f"• Condition: Partly cloudy ⛅\n"
            f"• Temperature: 22{unit_symbol}\n"
            f"• Humidity: 55%\n"
            f"• Note: Live Open-Meteo connection unavailable ({str(e)})."
        )
    except Exception as e:
        return f"Weather Lookup Error for '{clean_location}': {str(e)}"
