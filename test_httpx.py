import os
import httpx
import pytest


def test_httpx_chat():
    # Same values as the ChatOllama config used by OllamaProvider
    model = os.getenv("SCRAPEGRAPH_MODEL", "ollama/llama3.2").replace("ollama/", "")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Check whether the Ollama server is reachable before making the request
    try:
        with httpx.Client(timeout=5.0) as client:
            client.get(f"{base_url}/")
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        pytest.skip(
            "Ollama server not running",
            allow_module_level=False,
        )

    # Same payload structure ChatOllama sends to Ollama's /api/chat endpoint
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": 'Return a JSON object with exactly one key: "status" set to "ok". '
                           "Return only the JSON object.",
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
    }

    print("URL =", f"{base_url}/api/chat")
    print("MODEL =", model)
    print("PAYLOAD =", payload)

    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{base_url}/api/chat", json=payload)

    print("STATUS CODE =", response.status_code)
    print("RESPONSE BODY =", response.text)