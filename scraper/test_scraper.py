"""
Minimal ScrapeGraphAI test — single-URL lead extraction using a local Ollama model.

Requirements:
    - Ollama running locally at http://localhost:11434
    - Model pulled: `ollama pull llama3.2`
    - No API keys needed.
"""

import json
import sys

from scrapegraphai.graphs import SmartScraperGraph

# ---------------------------------------------------------------------------
# Configuration — change this URL to test a different website
# ---------------------------------------------------------------------------
TEST_URL = "https://scrapegraphai.com/"

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"

EXTRACTION_PROMPT = """
Extract business/lead information from this website.

Return a JSON object with exactly these keys:
- business_name
- contact_name
- email
- phone
- website
- city

Strict rules:
1. Do NOT invent, guess, or infer any information.
2. Only extract information that is actually present in the page content.
3. If a piece of information cannot be found on the page, set its value to null.
"""

# ScrapeGraphAI configuration for scrapegraphai 2.1.5 + langchain-ollama.
# The "ollama/<model>" prefix selects the Ollama provider; ScrapeGraphAI
# instantiates ChatOllama via langchain's init_chat_model under the hood.
GRAPH_CONFIG = {
    "llm": {
        "model": f"ollama/{OLLAMA_MODEL}",
        "base_url": OLLAMA_BASE_URL,
        "temperature": 0,
        "format": "json",       # force JSON output from Ollama
        "model_tokens": 8192,   # context window; consumed by ScrapeGraphAI
    },
    "verbose": True,
    "headless": True,           # Playwright runs without a visible browser
}


def main() -> int:
    print(f"Scraping: {TEST_URL}")
    print(f"Model:    ollama/{OLLAMA_MODEL} @ {OLLAMA_BASE_URL}\n")

    try:
        graph = SmartScraperGraph(
            prompt=EXTRACTION_PROMPT,
            source=TEST_URL,
            config=GRAPH_CONFIG,
        )
        result = graph.run()
    except Exception as exc:
        print("\n--- SCRAPING FAILED ---", file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "\nTroubleshooting:\n"
            "  - Is Ollama running?  Check: http://localhost:11434\n"
            f"  - Is the model pulled?  Run: ollama pull {OLLAMA_MODEL}\n"
            "  - Are Playwright browsers installed?  Run: playwright install chromium\n"
            "  - Is the TEST_URL reachable from this machine?",
            file=sys.stderr,
        )
        return 1

    print("\n--- EXTRACTED LEAD DATA ---")
    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Fallback: the model returned a raw string; try to parse it as JSON
        try:
            print(json.dumps(json.loads(result), indent=2, ensure_ascii=False))
        except (TypeError, json.JSONDecodeError):
            print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
