import requests
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
from requests_oauthlib import OAuth2Session

# Load environment variables
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
X_API_URL = "https://api.twitter.com/2/tweets"

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in .env. Using mock response.")

# Fetch weather data from OpenWeatherMap API
def get_weather(city):
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    try:
        response = requests.get(WEATHER_API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

# Query Gemini API for suggestion
def query_gemini(weather_data):
    if not weather_data:
        return "Unable to fetch weather data."
    
    city = weather_data["name"]
    temp = weather_data["main"]["temp"]
    condition = weather_data["weather"][0]["main"].lower()
    prompt = f"Given the weather in {city}: {temp}°C, {condition}, suggest an action for the user in natural language, under 50 words."
    
    # Mock response (fallback)
    mock_response = f"It’s {condition} in {city} at {temp}°C. "
    if "rain" in condition:
        mock_response += "Bring an umbrella and wear waterproof shoes."
    elif temp < 10:
        mock_response += "Wear a warm jacket to stay comfortable."
    else:
        mock_response += "Enjoy the pleasant weather!"
    
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error querying Gemini API: {e}")
            return mock_response
    return mock_response

# Post suggestion to X using OAuth2 Bearer Token
def post_to_x(suggestion):
    if not X_BEARER_TOKEN:
        print("Error: X_BEARER_TOKEN not found in .env. Cannot post to X.")
        return False
    
    headers = {
        "Authorization": f"Bearer {X_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": suggestion[:280]  # Ensure tweet is within 280-character limit
    }
    
    try:
        response = requests.post(X_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        print("Successfully posted to X:", response.json()["data"]["text"])
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("401 Error: Invalid X_BEARER_TOKEN. Verify at https://developer.x.com.")
        elif e.response.status_code == 429:
            print("429 Error: X API rate limit exceeded. Check https://developer.x.com.")
        elif e.response.status_code == 403:
            print("403 Error: Forbidden. Ensure your X account has API access (Premium+ may be required).")
        else:
            print(f"Error posting to X: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error posting to X: {e}")
        return False

# Log weather data and suggestion
def log_weather_data(weather_data, suggestion, posted_to_x):
    if not weather_data:
        return
    log_entry = {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "condition": weather_data["weather"][0]["main"],
        "suggestion": suggestion,
        "posted_to_x": posted_to_x,
        "timestamp": weather_data["dt"]
    }
    with open("weather_log.json", "a") as f:
        json.dump(log_entry, f)
        f.write("\n")

# Main function
def main():
    city = input("Enter a city name: ")
    weather_data = get_weather(city)
    suggestion = query_gemini(weather_data)
    print("Suggestion:", suggestion)
    
    if weather_data:
        posted = post_to_x(suggestion)
        log_weather_data(weather_data, suggestion, posted)

if __name__ == "__main__":
    main()