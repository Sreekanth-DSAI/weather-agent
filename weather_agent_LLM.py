import requests
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"

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
        "units": "metric"  # Use Celsius
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
    
    # Craft prompt for Gemini
    prompt = f"Given the weather in {city}: {temp}°C, {condition}, suggest an action for the user in natural language, under 50 words."
    
    # Mock response (fallback if Gemini API fails)
    mock_response = f"It’s {condition} in {city} at {temp}°C. "
    if "rain" in condition:
        mock_response += "Bring an umbrella and wear waterproof shoes."
    elif temp < 10:
        mock_response += "Wear a warm jacket to stay comfortable."
    else:
        mock_response += "Enjoy the pleasant weather!"
    
    # Gemini API call
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error querying Gemini API: {e}")
            if "Quota exceeded" in str(e):
                print("Rate limit reached. Check https://ai.google.dev/pricing for free tier limits.")
            elif "API key not valid" in str(e):
                print("Invalid GEMINI_API_KEY. Verify at https://aistudio.google.com.")
            return mock_response
    else:
        return mock_response

# Log weather data and suggestion
def log_weather_data(weather_data, suggestion):
    if not weather_data:
        return
    log_entry = {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "condition": weather_data["weather"][0]["main"],
        "suggestion": suggestion,
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
    print(suggestion)
    
    if weather_data:
        log_weather_data(weather_data, suggestion)

if __name__ == "__main__":
    main()