import requests
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime

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

# FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Simple in-memory user storage (for demo purposes)
current_user = {"username": None}

# Pydantic models
class LoginRequest(BaseModel):
    username: str

class WeatherRequest(BaseModel):
    city: str

class WeatherResponse(BaseModel):
    city: str
    temperature: float
    condition: str
    suggestion: str
    user: str

class WeatherLogEntry(BaseModel):
    city: str
    temperature: float
    condition: str
    suggestion: str
    timestamp: int
    units: str
    user: str

# Fetch weather data
def get_weather(city: str, units: str = "metric"):
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": units
    }
    try:
        print(f"Fetching weather for city: {city}, units: {units}")
        response = requests.get(WEATHER_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        data["units"] = units
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data for {city}: {e}")
        return None

# Query Gemini API
def query_gemini(weather_data):
    if not weather_data:
        return "Unable to fetch weather data."
    
    city = weather_data["name"]
    temp = weather_data["main"]["temp"]
    condition = weather_data["weather"][0]["main"].lower()
    units = "°C" if weather_data["units"] == "metric" else "°F"
    prompt = f"Given the weather in {city}: {temp}{units}, {condition}, suggest an action for the user in natural language, under 50 words."
    
    mock_response = f"It’s {condition} in {city} at {temp}{units}. "
    if "rain" in condition:
        mock_response += "Bring an umbrella and wear waterproof shoes."
    elif temp < (10 if units == "°C" else 50):
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

# Log weather data and suggestion
def log_weather_data(weather_data, suggestion, username: str):
    if not weather_data:
        return
    log_entry = {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "condition": weather_data["weather"][0]["main"],
        "suggestion": suggestion,
        "timestamp": weather_data["dt"],
        "units": weather_data["units"],
        "user": username or "anonymous"
    }
    try:
        with open("weather_log.json", "a") as f:
            json.dump(log_entry, f)
            f.write("\n")
    except Exception as e:
        print(f"Error logging data: {e}")

# Read weather log
def read_weather_log(limit: int = 100):
    try:
        with open("weather_log.json", "r") as f:
            lines = f.readlines()
            entries = [json.loads(line.strip()) for line in lines if line.strip()]
            print(f"Fetched {len(entries)} history entries, returning last {limit}")
            return entries[-limit:]
    except FileNotFoundError:
        print("Weather log file not found")
        return []
    except Exception as e:
        print(f"Error reading weather log: {e}")
        return []

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Root endpoint (serves index.html)
@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("index.html", "r") as f:
            return HTMLResponse(
                content=f.read(),
                headers={"Cache-Control": "max-age=3600"}
            )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")

# Login endpoint
@app.post("/login")
async def login(request: LoginRequest):
    if not request.username:
        raise HTTPException(status_code=400, detail="Username is required")
    current_user["username"] = request.username
    return {"username": request.username}

# Weather history endpoint (defined before /weather/{city})
@app.get("/weather/history", response_model=List[WeatherLogEntry])
async def get_weather_history(
    limit: int = Query(100, ge=1, le=1000)
):
    print(f"Accessing /weather/history with limit={limit}")
    entries = read_weather_log(limit)
    if not entries:
        raise HTTPException(status_code=404, detail="No weather history available")
    return entries

# Weather endpoint (GET)
@app.get("/weather/{city}", response_model=WeatherResponse)
async def get_weather_suggestion(
    city: str,
    units: str = Query("metric", enum=["metric", "imperial"])
):
    weather_data = get_weather(city, units)
    if not weather_data or "name" not in weather_data:
        raise HTTPException(status_code=400, detail=f"Failed to fetch weather data for {city}")
    suggestion = query_gemini(weather_data)
    username = current_user["username"] or "anonymous"
    log_weather_data(weather_data, suggestion, username)
    return {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "condition": weather_data["weather"][0]["main"],
        "suggestion": suggestion,
        "user": username
    }

# Weather endpoint (POST)
@app.post("/weather", response_model=WeatherResponse)
async def post_weather_suggestion(
    request: WeatherRequest,
    units: str = Query("metric", enum=["metric", "imperial"])
):
    weather_data = get_weather(request.city, units)
    if not weather_data or "name" not in weather_data:
        raise HTTPException(status_code=400, detail=f"Failed to fetch weather data for {request.city}")
    suggestion = query_gemini(weather_data)
    username = current_user["username"] or "anonymous"
    log_weather_data(weather_data, suggestion, username)
    return {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "condition": weather_data["weather"][0]["main"],
        "suggestion": suggestion,
        "user": username
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
