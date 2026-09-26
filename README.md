# Weather & Outfit Advisor Agent (with SentinelAgent Architecture)

An intelligent, multi-tool AI Agent system built using **Google Agent Development Kit (ADK)** and deployed on **Google Cloud Agent Platform (ReasoningEngine)**. The agent provides real-time weather forecasting, sunrise/sunset scheduling, personalized clothing recommendations, persistent allergy memory, visual outfit image previews, and short outfit video generation.

---

## 🛠️ Implemented Capabilities & Architecture

The application implements the following core agent capabilities and Google Cloud services:

### 1. 🌦️ Real-Time Weather & Daylight Intelligence
* **Live Weather Metrics**: Fetches real-time temperature (°F), feels-like values, humidity, precipitation, and wind speeds via Open-Meteo.
* **Sunlight Schedules**: Retrieves exact sunrise, sunset, civil twilight, and total daylight duration for any global city via Sunrise-Sunset.

### 2. 🧠 Persistent Memory & Allergy Management
* **Vertex AI Memory Bank Service**: Integrated with ReasoningEngine Memory Bank in `us-east1` for cross-session context persistence.
* **Google Cloud Firestore**: Remembers user style profiles, cold sensitivity thresholds, and fabric/material allergies (e.g., wool, latex, synthetic down) stored in the `user_outfit_preferences` collection.

### 3. 🎨 Multimodal Media Generation
* **Outfit Preview Images**: Generates high-quality visual outfit preview images using `gemini-3.1-flash-lite-image` in the `global` Vertex AI region.
* **Outfit Showcase Videos**: Generates short video clips for outfit items using Google's Omni model (`gemini-omni-flash-preview`) in the `global` region. Saves artifacts via `tool_context.save_artifact` and uploads directly to public **Google Cloud Storage** (`weather-outfit-assets-9f2a`).

### 4. 📺 Dynamic A2UI & Code Execution
* **A2UI Protocol (v0.8 Basic Catalog)**: Formats structured UI cards, columns, text, and images via `A2uiSchemaManager`.
* **AgentEngine Sandbox Code Executor**: Runs isolated Python code execution inside Google Cloud ReasoningEngine sandbox environments.

### 5. 🌐 Web Frontend & Proxy Architecture
* **FastAPI Proxy Server**: Authenticates with Google Cloud ADC and forwards A2A JSON-RPC calls (`message/send`) to ReasoningEngine endpoints.
* **Responsive HTML/CSS/JS Interface**: Modern dark-mode chat UI with Markdown rendering (`marked.js`), quick example prompt chips, and visual preview cards.

---

## ☁️ Google Cloud Services & Integrations

| Service / Tool | Configuration / Scope | Implementation File |
| :--- | :--- | :--- |
| **Agent Platform (ReasoningEngine)** | Deployed ReasoningEngine in `us-east1` | [`agents-cli-manifest.yaml`](./agents-cli-manifest.yaml) |
| **Vertex AI Memory Bank** | `VertexAiMemoryBankService` (`us-east1`) | [`app/agent.py`](./app/agent.py) |
| **Google Cloud Firestore** | Document DB (`qwiklabs-gcp-02-25232f8c8134`) | [`app/tools.py`](./app/tools.py) |
| **Google Cloud Storage** | Public Asset Bucket (`weather-outfit-assets-9f2a`) | [`app/tools.py`](./app/tools.py) |
| **Vertex AI Imagen & Omni** | `gemini-3.1-flash-lite-image`, `gemini-omni-flash-preview` (`global`) | [`app/tools.py`](./app/tools.py) |
| **Google Cloud Run** | Containerized Frontend Service | [`frontend/main.py`](./frontend/main.py) |

> 📌 *Note on Roadmap / Project Brief*: The autonomous CI/CD failure triage & repo vulnerability scanner mentioned in `project_brief.md` is a **planned, not yet implemented** feature for future releases.

---

## 🚀 Local Setup & Execution Guide

Follow these commands to run the agent playground or local frontend web interface:

### 1. Prerequisites
Ensure Google Cloud SDK and Python environment are initialized:
```bash
gcloud auth application-default login
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Run ADK Agent Playground
To launch the agent locally with Memory Bank support:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<AGENT_ENGINE_ID>
```

### 3. Run Web Frontend Server
To run the FastAPI frontend proxy locally:
```bash
cd frontend
uv pip install -r requirements.txt
AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/us-east1/reasoningEngines/<ENGINE_ID>" \
AGENT_DIRECTORY="app" \
PORT=8080 \
python main.py
```
