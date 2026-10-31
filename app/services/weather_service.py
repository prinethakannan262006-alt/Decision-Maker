import logging
import requests

logger = logging.getLogger(__name__)

# Fallback forecast data when external API is unreachable or times out
FALLBACK_DECISION = {
    "status": "fallback",
    "location": "Global / Offline Mode",
    "temperature": 21.5,
    "weather_code": 1,
    "weather_condition": "Mild & Partly Cloudy (Simulated Fallback)",
    "recommendation": "Conditions look balanced! Grab a light jacket if you decide to go outside.",
    "verdict": "YES - Go outside with caution",
    "score": 75,
    "source": "Local Fallback Engine"
}

def get_weather_decision(latitude=51.5074, longitude=-0.1278, city="London"):
    """
    Fetches real-time weather from Open-Meteo API with strict 3s timeout
    and provides an automated "Should I go outside?" decision.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": True
    }
    try:
        response = requests.get(url, params=params, timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            cw = data.get("current_weather", {})
            temp = cw.get("temperature", 20)
            code = cw.get("weathercode", 0)
            wind = cw.get("windspeed", 0)

            # Interpret WMO weather codes
            condition = "Clear Sky"
            verdict = "YES - Great time to step outside!"
            score = 90
            recommendation = "Optimal weather for a walk, outdoor run, or errands."

            if code in [1, 2, 3]:
                condition = "Mainly Clear / Overcast"
                verdict = "YES - Good to go"
                score = 80
                recommendation = "Weather is calm with moderate cloud cover."
            elif code in [45, 48]:
                condition = "Foggy / Mist"
                verdict = "MAYBE - Low visibility"
                score = 55
                recommendation = "Be cautious while commuting; visibility is reduced."
            elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                condition = "Rain / Showers"
                verdict = "NO - Rainy conditions"
                score = 30
                recommendation = "Rain detected. Bring an umbrella or prioritize indoor tasks."
            elif code in [71, 73, 75, 85, 86]:
                condition = "Snow / Ice"
                verdict = "NO - Freezing conditions"
                score = 25
                recommendation = "Snow and icy conditions. Dress heavily or stay warm indoors."
            elif code >= 95:
                condition = "Thunderstorm"
                verdict = "NO - Severe Weather Alert"
                score = 10
                recommendation = "Thunderstorms active. Stay indoors for safety."

            if temp < 5:
                recommendation += " It's quite cold outside, wear thermal clothing."
            elif temp > 35:
                recommendation += " High heat warning; stay hydrated in shaded areas."

            return {
                "status": "live",
                "location": city,
                "temperature": temp,
                "windspeed": wind,
                "weather_code": code,
                "weather_condition": condition,
                "recommendation": recommendation,
                "verdict": verdict,
                "score": score,
                "source": "Open-Meteo Live API"
            }
        else:
            logger.warning(f"Weather API returned status code {response.status_code}")
            return FALLBACK_DECISION
    except requests.RequestException as e:
        logger.warning(f"Weather API request failed or timed out: {type(e).__name__}")
        return FALLBACK_DECISION
    except Exception as e:
        logger.error(f"Unexpected error in weather service: {e}")
        return FALLBACK_DECISION
