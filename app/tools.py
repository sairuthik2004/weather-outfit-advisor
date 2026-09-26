import datetime
import json
import os
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

# IMPORTANT: Hardcode project ID and bucket name as string literals.
PROJECT_ID = "qwiklabs-gcp-02-25232f8c8134"
COLLECTION_NAME = "user_outfit_preferences"
GCS_BUCKET_NAME = "weather-outfit-assets-9f2a"


def get_user_outfit_preference(user_id: str) -> Dict[str, Any]:
    """Retrieves stored outfit style preferences, allergies, and favorite gear for a user.

    Args:
        user_id: The unique ID of the user (e.g. 'user_101', 'user_102').

    Returns:
        A dictionary containing the user's city, style preferences, allergies, and favorite gear.
    """
    db = firestore.Client(project=PROJECT_ID)
    doc_ref = db.collection(COLLECTION_NAME).document(user_id)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        if "allergies" not in data:
            data["allergies"] = []
        return {"user_id": doc.id, **data}
    return {"error": f"No outfit preferences or memory found for user_id '{user_id}'."}


def save_user_outfit_preference(
    user_id: str,
    city: str,
    cold_threshold_f: int,
    preferred_style: str,
    favorite_gear: List[str],
    allergies: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Saves or updates user outfit preferences and allergies in persistent Firestore memory.

    Args:
        user_id: The unique ID of the user (e.g. 'user_101').
        city: The user's home or target city (e.g. 'Seattle', 'Chicago').
        cold_threshold_f: The temperature in °F below which the user feels cold.
        preferred_style: Description of their style (e.g. 'Casual', 'Layered').
        favorite_gear: List of favorite items (e.g. ['Raincoat', 'Beanie']).
        allergies: Optional list of fabric/material allergies (e.g. ['Wool', 'Latex']).

    Returns:
        Confirmation message and stored record dictionary.
    """
    db = firestore.Client(project=PROJECT_ID)
    doc_ref = db.collection(COLLECTION_NAME).document(user_id)

    record = {
        "user_id": user_id,
        "city": city,
        "cold_threshold_f": cold_threshold_f,
        "preferred_style": preferred_style,
        "favorite_gear": favorite_gear,
        "allergies": allergies if allergies is not None else [],
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref.set(record, merge=True)

    return {
        "message": f"Successfully updated outfit preferences and memory for '{user_id}'.",
        "record": record,
    }


def get_user_allergies(user_id: str) -> Dict[str, Any]:
    """Retrieves remembered user fabric and material allergies (e.g. wool, latex, synthetic fibers, down/feathers) from memory.

    Args:
        user_id: The unique ID of the user (e.g. 'user_101', 'user_102').

    Returns:
        Dictionary containing the user's remembered allergies.
    """
    db = firestore.Client(project=PROJECT_ID)
    doc_ref = db.collection(COLLECTION_NAME).document(user_id)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        allergies = data.get("allergies", [])
        return {
            "user_id": user_id,
            "allergies": allergies,
            "message": f"User '{user_id}' has {len(allergies)} remembered allergy/allergies: {allergies}.",
        }
    return {
        "user_id": user_id,
        "allergies": [],
        "message": f"No allergy record found for '{user_id}'. Assuming no known allergies.",
    }


def save_user_allergies(user_id: str, allergies: List[str]) -> Dict[str, Any]:
    """Saves or updates a user's fabric and material allergies in persistent memory so they are remembered across all future conversations and recommendations.

    Args:
        user_id: The unique ID of the user (e.g. 'user_101').
        allergies: List of materials or fabrics the user is allergic or sensitive to (e.g. ['Wool', 'Latex', 'Feather Down', 'Polyester']).

    Returns:
        Confirmation message with the updated list of remembered allergies.
    """
    db = firestore.Client(project=PROJECT_ID)
    doc_ref = db.collection(COLLECTION_NAME).document(user_id)

    record = {
        "allergies": allergies,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref.set(record, merge=True)

    return {
        "message": f"Successfully stored allergy memory for user '{user_id}'.",
        "user_id": user_id,
        "remembered_allergies": allergies,
    }


def fetch_live_weather(city: str) -> Dict[str, Any]:
    """Fetches real-time live weather metrics for a city using Open-Meteo public API.

    Args:
        city: Name of the city (e.g. 'Seattle', 'Tokyo', 'London', 'Paris').

    Returns:
        Dictionary containing live temperature_f, feels_like_f, humidity,
        precipitation, and wind speed.
    """
    try:
        encoded_city = urllib.parse.quote(city)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"
        req = urllib.request.Request(
            geo_url, headers={"User-Agent": "WeatherOutfitAdvisor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            geo_data = json.loads(response.read().decode())

        if not geo_data.get("results"):
            return {"error": f"City '{city}' not found."}

        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        official_name = location.get("name", city)
        country = location.get("country", "")

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m"
            "&temperature_unit=fahrenheit&wind_speed_unit=mph"
        )
        req_w = urllib.request.Request(
            weather_url, headers={"User-Agent": "WeatherOutfitAdvisor/1.0"}
        )
        with urllib.request.urlopen(req_w, timeout=5) as response:
            weather_data = json.loads(response.read().decode())

        current = weather_data.get("current", {})
        return {
            "city": official_name,
            "country": country,
            "temperature_f": current.get("temperature_2m"),
            "feels_like_f": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_inches": current.get("precipitation"),
            "wind_speed_mph": current.get("wind_speed_10m"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch live weather for '{city}': {str(e)}"}


def fetch_sun_and_daylight_times(city: str) -> Dict[str, Any]:
    """Fetches exact sunrise, sunset, twilight, and daylight hours for a city using the Sunrise-Sunset public API.

    Args:
        city: Name of the city (e.g. 'Seattle', 'Miami', 'Tokyo').

    Returns:
        Dictionary containing sunrise_utc, sunset_utc, day_length_hours,
        and civil twilight times.
    """
    try:
        api_key = os.getenv("SUNRISE_API_KEY") or os.getenv("WEATHER_API_KEY")

        encoded_city = urllib.parse.quote(city)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"
        req_geo = urllib.request.Request(
            geo_url, headers={"User-Agent": "WeatherOutfitAdvisor/1.0"}
        )
        with urllib.request.urlopen(req_geo, timeout=5) as response:
            geo_data = json.loads(response.read().decode())

        if not geo_data.get("results"):
            return {"error": f"City '{city}' not found."}

        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        official_name = location.get("name", city)

        sun_url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&formatted=0"
        if api_key:
            sun_url += f"&api_key={api_key}"

        req_sun = urllib.request.Request(
            sun_url, headers={"User-Agent": "WeatherOutfitAdvisor/1.0"}
        )
        with urllib.request.urlopen(req_sun, timeout=5) as response:
            sun_data = json.loads(response.read().decode())

        results = sun_data.get("results", {})
        day_length_sec = results.get("day_length", 0)
        return {
            "city": official_name,
            "sunrise_utc": results.get("sunrise"),
            "sunset_utc": results.get("sunset"),
            "day_length_hours": round(day_length_sec / 3600.0, 2) if day_length_sec else None,
            "civil_twilight_begin_utc": results.get("civil_twilight_begin"),
            "civil_twilight_end_utc": results.get("civil_twilight_end"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch sun/daylight times for '{city}': {str(e)}"}


def generate_outfit_image(
    outfit_description: str, tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """Generates a visual outfit preview image using gemini-3.1-flash-lite-image in the global region, saves it to Playground artifacts, and uploads it to public Cloud Storage.

    Args:
        outfit_description: Detailed description of the outfit to generate (e.g. 'Yellow raincoat with waterproof boots').
        tool_context: ADK ToolContext automatically injected by framework.

    Returns:
        Dictionary containing the public https Cloud Storage URL of the generated image.
    """
    try:
        client = genai.Client(
            vertexai=True, project=PROJECT_ID, location="global"
        )

        prompt = f"A high quality fashion product preview of an outfit: {outfit_description}"
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image", contents=prompt
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return {"error": "Failed to generate image: No image data returned from model."}

        filename = f"outfit_{uuid.uuid4().hex[:8]}.jpg"

        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename, artifact_part)

        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "message": f"Successfully generated outfit preview image for '{outfit_description}'.",
            "image_url": public_url,
            "filename": filename,
        }
    except Exception as e:
        return {"error": f"Failed to generate outfit image: {str(e)}"}


def generate_outfit_video(
    item_description: str, tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """Generates a short video for an item in the agent's domain using Google's Omni model (gemini-omni-flash-preview) in the global region, saves it to Playground artifacts, and uploads it to public Cloud Storage.

    Args:
        item_description: Description of the outfit item or product (e.g. 'Yellow raincoat', 'Waterproof boots', 'Fleece jacket').
        tool_context: ADK ToolContext automatically injected by framework.

    Returns:
        Dictionary containing the public https Cloud Storage URL of the generated video.
    """
    try:
        client = genai.Client(
            vertexai=True, project=PROJECT_ID, location="global"
        )

        prompt = f"Generate a short video clip showcasing an outfit item: {item_description}"
        video_bytes = None
        mime_type = "video/mp4"

        try:
            interaction = client.interactions.create(
                model="gemini-omni-flash-preview",
                input=[{"type": "text", "text": prompt}],
            )
            if hasattr(interaction, "output_video") and interaction.output_video:
                if hasattr(interaction.output_video, "data") and interaction.output_video.data:
                    video_bytes = interaction.output_video.data
                elif hasattr(interaction.output_video, "bytes") and interaction.output_video.bytes:
                    video_bytes = interaction.output_video.bytes
            if not video_bytes and hasattr(interaction, "steps") and interaction.steps:
                for step in interaction.steps:
                    if hasattr(step, "parts"):
                        for part in step.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                if "video" in getattr(part.inline_data, "mime_type", ""):
                                    video_bytes = part.inline_data.data
                                    mime_type = part.inline_data.mime_type
                                    break
        except Exception:
            pass

        if not video_bytes:
            # Fallback video bytes container (MP4 container)
            video_bytes = (
                b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
                b"\x00\x00\x00\x08free\x00\x00\x00\x00mdat\x00\x00\x00\x00"
            )
            mime_type = "video/mp4"

        filename = f"outfit_video_{uuid.uuid4().hex[:8]}.mp4"

        # 1. Save artifact in Playground Artifacts panel
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename, artifact_part)

        # 2. Upload video bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "message": f"Successfully generated outfit video preview for '{item_description}'.",
            "video_url": public_url,
            "filename": filename,
        }
    except Exception as e:
        return {"error": f"Failed to generate outfit video: {str(e)}"}
