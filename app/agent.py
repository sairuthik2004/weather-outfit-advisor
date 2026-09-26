import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import load_memory, preload_memory
from google.genai import types

from app.a2ui_utils import a2ui_after_model_callback, build_a2ui_system_prompt
from app.tools import (
    PROJECT_ID,
    fetch_live_weather,
    fetch_sun_and_daylight_times,
    generate_outfit_image,
    generate_outfit_video,
    get_user_allergies,
    get_user_outfit_preference,
    save_user_allergies,
    save_user_outfit_preference,
)

# Read deployment_metadata.json to resolve AgentEngine Sandbox & Memory Bank configuration
metadata_file = Path(__file__).parent.parent / "deployment_metadata.json"
sandbox_resource_name = None
agent_engine_resource_name = None
agent_engine_id = None

if metadata_file.exists():
    try:
        with open(metadata_file, "r") as f:
            meta = json.load(f)
            sandbox_resource_name = meta.get("sandbox_resource_name")
            agent_engine_resource_name = meta.get("remote_agent_runtime_id")
            if agent_engine_resource_name:
                agent_engine_id = agent_engine_resource_name.split("/")[-1]
    except Exception:
        pass

# Code Executor
if sandbox_resource_name:
    code_executor = AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=sandbox_resource_name
    )
elif agent_engine_resource_name:
    code_executor = AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=agent_engine_resource_name
    )
else:
    code_executor = AgentEngineSandboxCodeExecutor()

# Memory Bank Service for future redeployments
memory_service = None
if agent_engine_id:
    memory_service = VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id=agent_engine_id,
    )


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    elif "ny" in query.lower() or "new york" in query.lower():
        tz_identifier = "America/New_York"
    else:
        tz_identifier = "UTC"

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


base_role_description = (
    "You are the Weather & Outfit Advisor Agent. Your goal is to help users "
    "prepare for their day by offering real-time weather reports, daylight schedules, clothing recommendations, visual outfit previews, outfit videos, dynamic UI cards, and remembering user preferences & allergies.\n"
    "1. MEMORY & ALLERGIES: Always check remembered user allergies (`get_user_allergies` / `preload_memory` / `load_memory`) and preferences before suggesting outfit items. NEVER suggest materials the user is allergic to (e.g. avoid wool if the user has a wool allergy).\n"
    "2. When a user states an allergy (e.g. 'I am allergic to wool'), immediately call `save_user_allergies` to store it permanently in memory.\n"
    "3. Use `fetch_live_weather` for real-time weather metrics (temperature, feels-like, humidity, precipitation, wind).\n"
    "4. Use `fetch_sun_and_daylight_times` for sunrise, sunset, and daylight duration.\n"
    "5. Use `generate_outfit_image` to generate a visual preview image when appropriate.\n"
    "6. Use `generate_outfit_video` to generate a short video preview of an outfit item using Google's Omni model (gemini-omni-flash-preview) in global region.\n"
    "7. Use Python code execution to calculate outfit metrics or unit conversions when helpful.\n"
    "8. Use `get_user_outfit_preference` and `save_user_outfit_preference` for general style profiles."
)

# Build A2UI System Prompt (version 0.8 & Basic Catalog)
system_instruction = build_a2ui_system_prompt(
    role_description=base_role_description, version="0.8"
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=system_instruction,
    after_model_callback=a2ui_after_model_callback,
    code_executor=code_executor,
    tools=[
        fetch_live_weather,
        fetch_sun_and_daylight_times,
        generate_outfit_image,
        generate_outfit_video,
        get_user_allergies,
        save_user_allergies,
        get_user_outfit_preference,
        save_user_outfit_preference,
        preload_memory,
        load_memory,
        get_current_time,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
