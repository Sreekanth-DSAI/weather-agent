import requests
import json
import os
import pandas as pd
from dotenv import load_dotenv
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# Simulated historical data for training
training_data = pd.DataFrame({
    "temperature": [5, 15, 25, 8, 12, 18, 30, 10, 20, 22],
    "condition": ["snow", "clear", "clear", "rain", "rain", "cloudy", "clear", "snow", "cloudy", "rain"],
    "action": ["wear_jacket", "enjoy_weather", "enjoy_weather", "bring_umbrella", "bring_umbrella", 
               "enjoy_weather", "enjoy_weather", "wear_jacket", "enjoy_weather", "bring_umbrella"]
})

# Train a simple ML model
def train_model():
    X = training_data[["temperature", "condition"]]
    y = training_data["action"]
    
    # Encode categorical data (condition)
    le_condition = LabelEncoder()
    le_action = LabelEncoder()
    X["condition"] = le_condition.fit_transform(X["condition"])
    y = le_action.fit_transform(y)
    
    # Train decision tree
    model = DecisionTreeClassifier(random_state=42)
    model.fit(X, y)
    
    return model, le_condition, le_action

# Fetch weather data
def get_weather(city):
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

# Predict action using ML model
def predict_action(weather_data, model, le_condition, le_action):
    if not weather_data:
        return "Unable to fetch weather data."
    
    city = weather_data["name"]
    temp = weather_data["main"]["temp"]
    condition = weather_data["weather"][0]["main"].lower()
    
    # Prepare input for model
    try:
        condition_encoded = le_condition.transform([condition])[0]
    except ValueError:
        return f"Unknown weather condition: {condition}"
    
    X_new = [[temp, condition_encoded]]
    action_encoded = model.predict(X_new)[0]
    action = le_action.inverse_transform([action_encoded])[0]
    
    return f"Weather in {city}: {temp}°C, {condition}. Suggested action: {action}"

# Log weather data and user action
def log_weather_data(weather_data, action):
    if not weather_data:
        return
    log_entry = {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "condition": weather_data["weather"][0]["main"],
        "action": action,
        "timestamp": weather_data["dt"]
    }
    with open("weather_log.json", "a") as f:
        json.dump(log_entry, f)
        f.write("\n")

# Main function
def main():
    # Train the model
    model, le_condition, le_action = train_model()
    
    # Get user input
    city = input("Enter a city name: ")
    weather_data = get_weather(city)
    suggestion = predict_action(weather_data, model, le_condition, le_action)
    print(suggestion)
    
    # Log data (assuming user accepts the suggestion)
    if weather_data and "Suggested action" in suggestion:
        action = suggestion.split("Suggested action: ")[1]
        log_weather_data(weather_data, action)

if __name__ == "__main__":
    main()