import os
import pytest

# Skip this test module if an Ollama server is not reachable (default points to localhost).
if "localhost" in os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"):
    pytest.skip(
        "Ollama server not available – skipping external LLM integration tests.",
        allow_module_level=True,
    )

from langchain_ollama import ChatOllama

# Same config as OllamaProvider.__init__()
graph_config = {
    "llm": {
        "model": os.getenv("SCRAPEGRAPH_MODEL", "ollama/llama3.2"),
        "temperature": 0,
        "format": "json",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    },
    "headless": True,
    "verbose": True,
}

# Same ChatOllama constructor as OllamaProvider
llm = ChatOllama(
    model=graph_config["llm"]["model"].replace("ollama/", ""),
    base_url=graph_config["llm"]["base_url"],
    temperature=0,
    format="json",
)

print("MODEL =", graph_config["llm"]["model"].replace("ollama/", ""))
print("BASE_URL =", graph_config["llm"]["base_url"])

response = llm.invoke(
    'Return a JSON object with exactly one key: "status" set to "ok". '
    "Return only the JSON object."
)

print("INVOKE RESULT =", response.content)
