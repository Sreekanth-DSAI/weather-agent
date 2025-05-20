import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# Function to fetch weather data
def get_weather(city):
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"  # Use Celsius
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raise exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

# Function to analyze weather and suggest actions
def analyze_weather(weather_data):
    if not weather_data:
        return "Unable to fetch weather data."
    
    city = weather_data["name"]
    temp = weather_data["main"]["temp"]
    weather_condition = weather_data["weather"][0]["main"].lower()
    
    # Simple rule-based AI logic
    if "rain" in weather_condition:
        suggestion = "Bring an umbrella!"
    elif temp < 10:
        suggestion = "Wear a warm jacket!"
    else:
        suggestion = "Enjoy the weather!"
    
    return f"Weather in {city}: {temp}°C, {weather_condition}. {suggestion}"

# Function to log weather data to a file
def log_weather_data(weather_data):
    if not weather_data:
        return
    log_entry = {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "condition": weather_data["weather"][0]["main"],
        "timestamp": weather_data["dt"]
    }
    with open("weather_log.json", "a") as f:
        json.dump(log_entry, f)
        f.write("\n")  # Add newline for readability

# Main function to run the AI agent
def main():
    city = input("Enter a city name: ")
    weather_data = get_weather(city)
    suggestion = analyze_weather(weather_data)
    print(suggestion)
    log_weather_data(weather_data)

if __name__ == "__main__":
    main()