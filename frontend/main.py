import json
import logging
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import urllib.request
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Weather Outfit Advisor Chat UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_ENGINE_RESOURCE_NAME = os.getenv(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/1078992943174/locations/us-east1/reasoningEngines/5210442667518853120",
)
AGENT_DIRECTORY = os.getenv("AGENT_DIRECTORY", "app")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatMessageRequest(BaseModel):
    message: str


def extract_response_content(data: dict):
    text_chunks = []
    image_urls = []

    # 1. Regex scan whole raw JSON for GCS image URLs
    raw_str = json.dumps(data)
    gcs_images = re.findall(
        r"https://storage\.googleapis\.com/[^\s\"\'\>]+\.(?:jpg|png|jpeg|webp)",
        raw_str,
        flags=re.IGNORECASE,
    )
    image_urls.extend(gcs_images)

    # 2. Traverse structure
    result = data.get("result", {})
    message_parts = result.get("message", {}).get("parts", [])
    artifact_items = result.get("artifacts", [])
    items_to_process = message_parts + artifact_items

    def process_item(item):
        if not isinstance(item, dict):
            return
        if "text" in item and item["text"]:
            text_chunks.append(item["text"])
        if "uri" in item and item["uri"]:
            image_urls.append(item["uri"])
        elif "url" in item and item["url"]:
            image_urls.append(item["url"])
        if "image_url" in item and item["image_url"]:
            image_urls.append(item["image_url"])

        if "parts" in item and isinstance(item["parts"], list):
            for sub_part in item["parts"]:
                process_item(sub_part)
        if "data" in item and isinstance(item["data"], dict):
            process_item(item["data"])

    for item in items_to_process:
        process_item(item)

    clean_texts = []
    for text in text_chunks:
        # Extract image_url from <a2ui-json> before stripping
        a2ui_imgs = re.findall(r'\"image_url\":\s*\"(https?://[^\"]+)\"', text)
        image_urls.extend(a2ui_imgs)

        cleaned = re.sub(
            r"<a2ui-json>.*?</a2ui-json>", "", text, flags=re.DOTALL
        ).strip()
        if cleaned:
            clean_texts.append(cleaned)
        elif text.strip():
            clean_texts.append(text.strip())

    reply = (
        "\n\n".join(clean_texts)
        if clean_texts
        else "Response received from agent."
    )

    unique_images = []
    for img in image_urls:
        if img not in unique_images:
            unique_images.append(img)

    return reply, unique_images


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse(
        "<h1>Weather & Outfit Advisor UI</h1><p>Frontend running.</p>"
    )


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "agent_engine_resource_name": AGENT_ENGINE_RESOURCE_NAME,
        "agent_directory": AGENT_DIRECTORY,
    }


@app.post("/api/chat")
async def chat_endpoint(req: ChatMessageRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        credentials, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        token = credentials.token

        a2a_url = f"https://us-east1-aiplatform.googleapis.com/reasoningEngines/v1/{AGENT_ENGINE_RESOURCE_NAME}/api/a2a/{AGENT_DIRECTORY}"
        logger.info(f"Posting request to A2A URL: {a2a_url}")

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": req.message}],
                }
            },
        }

        http_req = urllib.request.Request(
            a2a_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(http_req, timeout=90) as resp:
            resp_bytes = resp.read()
            data = json.loads(resp_bytes.decode("utf-8"))

        if "error" in data:
            logger.error(f"A2A response error: {data['error']}")
            raise HTTPException(
                status_code=500, detail=f"Agent Error: {data['error']}"
            )

        reply, image_urls = extract_response_content(data)
        return {
            "response": reply,
            "image_urls": image_urls,
            "raw": data.get("result"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to query deployed agent via A2A")
        raise HTTPException(
            status_code=500, detail=f"Failed to query deployed agent: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
