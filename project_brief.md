# Project Brief: WeatherOutfitAdvisor (Weather & Outfit Advisor Agent)

## 1. Executive Summary
**WeatherOutfitAdvisor** (`weather-outfit-advisor`) is a friendly conversational AI assistant designed to help users prepare for their day. Given a location (e.g., city name), the agent looks up current weather conditions and temperature, and provides practical, personalized clothing and accessory recommendations (such as coats, umbrellas, sunglasses, or layers).

## 2. Core Capabilities
* **Weather Lookup**: Queries location-specific weather reports (temperature and conditions).
* **Outfit Recommendation**: Suggests clothing based on temperature thresholds and weather attributes (rain, snow, heat, wind).

## 3. Architecture & Tools
* **`get_weather(location)`**: Returns location weather metrics.
* **Agent Framework**: Built using Google Agent Development Kit (ADK) in Python.
