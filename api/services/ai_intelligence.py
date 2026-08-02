import os
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from scrapegraphai.graphs import SmartScraperGraph
from scraper.database import upsert_ai_insights, get_ai_insights_by_lead_id
from langchain_ollama import ChatOllama

class BaseAIProvider(ABC):
    """Abstract Base Class for AI Intelligence Providers."""

    REQUIRED_SCHEMA = {
        "company_summary": "",
        "services_offered": [],
        "target_customers": [],
        "business_model": "",
        "industry_category": "",
        "technologies_used": [],
        "pain_points": [],
        "sales_opportunities": []
    }

    @abstractmethod
    def generate_intelligence(self, business_profile: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Generate intelligence using the synthesized Business Profile instead of a raw URL."""
        pass

    def _ensure_schema(self, result: Any) -> Dict[str, Any]:
        """Ensures the result matches the required schema, handling strings and missing keys."""
        parsed_result = {}

        if isinstance(result, str):
            try:
                # Extract JSON from markdown code blocks if present
                json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
                if json_match:
                    parsed_result = json.loads(json_match.group(1))
                else:
                    parsed_result = json.loads(result)
            except (json.JSONDecodeError, ValueError):
                print(f"Failed to parse AI response as JSON: {result[:100]}...")
                parsed_result = {}
        elif isinstance(result, dict):
            parsed_result = result

        # Intelligent Mapping for common ScrapeGraphAI/LLM patterns
        mapping = {
            "description": "company_summary",
            "services": "services_offered",
            "products": "services_offered",
            "summary": "company_summary",
        }
        for src, dest in mapping.items():
            if src in parsed_result and dest not in parsed_result:
                parsed_result[dest] = parsed_result[src]
            elif src in parsed_result and isinstance(parsed_result[src], list) and isinstance(parsed_result.get(dest), list):
                # Merge lists if both exist
                parsed_result[dest] = list(set(parsed_result[dest] + parsed_result[src]))

        # Merge with REQUIRED_SCHEMA to ensure all keys exist
        final_result = self.REQUIRED_SCHEMA.copy()
        for key, default_value in self.REQUIRED_SCHEMA.items():
            if key in parsed_result:
                val = parsed_result[key]
                # Ensure list fields are actually lists
                if isinstance(default_value, list) and not isinstance(val, list):
                    final_result[key] = [val] if val else []
                else:
                    final_result[key] = val
            else:
                final_result[key] = default_value

        return final_result

class OllamaProvider(BaseAIProvider):
    """Ollama implementation of the AI Intelligence Provider."""

    def __init__(self):
        # Config for ScrapeGraphAI
        self.graph_config = {
            "llm": {
                "model": os.getenv("SCRAPEGRAPH_MODEL", "ollama/llama3.2"),
                "temperature": 0,
                "format": "json",
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            },
            "headless": True,
            "verbose": True
        }
        # Initialize ChatOllama client for the second stage
        self.llm = ChatOllama(
            model=self.graph_config["llm"]["model"].replace("ollama/", ""),
            base_url=self.graph_config["llm"]["base_url"],
            temperature=0,
            format="json"
        )

    def generate_intelligence(self, business_profile: Dict[str, Any], context: str) -> Dict[str, Any]:
        # Extract the core business details from the profile for the prompt
        company_name = business_profile.get("company_name", "the company")
        details = business_profile.get("business_details", {})
        description = details.get("description", "No description available")

        # Step 2 & 3: Pass the Business Profile content to the LLM with a dedicated Business Intelligence prompt
        bi_prompt = (
            f"You are a Senior Business Analyst. Based on the following Business Profile for {company_name}, "
            f"and this existing context: {context}, generate high-level business intelligence. "
            f"\n\nBusiness Profile:\n{json.dumps(business_profile, indent=2)}\n\n"
            "You MUST return a valid JSON object with exactly these keys:\n"
            "- company_summary: (2-sentence high-level pitch)\n"
            "- services_offered: (list of core products/services)\n"
            "- target_customers: (ideal customer profile)\n"
            "- business_model: (how they make money, e.g., SaaS, Agency)\n"
            "- industry_category: (primary industry)\n"
            "- technologies_used: (list of identified tech stack)\n"
            "- pain_points: (list of likely operational or growth struggles)\n"
            "- sales_opportunities: (specific ways Bilvaleaf can help them)\n"
            "\nEnsure the response is only the JSON object."
        )

        try:
            # Use the LangChain ChatOllama client
            import socket
            print("OLLAMA_BASE_URL =", os.getenv("OLLAMA_BASE_URL"))
            print("SCRAPEGRAPH_MODEL =", os.getenv("SCRAPEGRAPH_MODEL"))
            print("LLM OBJECT =", self.llm)
            print("LLM BASE URL =", getattr(self.llm, "base_url", "N/A"))
            print("LLM MODEL =", getattr(self.llm, "model", "N/A"))
            print(socket.getaddrinfo("localhost", 11434))
            response = self.llm.invoke(bi_prompt)
            # ChatOllama returns a BaseMessage; the content is in .content
            result = response.content
        except Exception as e:
            import traceback
            print("\n--- DEBUG: AI Intelligence Connection Failure ---")
            traceback.print_exc()
            print(f"TYPE: {type(e)}")
            print(f"REPR: {repr(e)}")
            print(f"CAUSE: {repr(e.__cause__)}")
            print(f"CONTEXT: {repr(e.__context__)}")
            print("--- END DEBUG ---\n")
            print(f"Error during BI analysis phase: {e}")
            # Fallback: if LLM call fails, use the description as is
            result = {"company_summary": description}

        return self._ensure_schema(result)

class OpenAIProvider(BaseAIProvider):
    """OpenAI implementation of the AI Intelligence Provider."""

    def __init__(self):
        self.graph_config = {
            "llm": {
                "model": "gpt-4o",
                "temperature": 0,
                "api_key": os.getenv("OPENAI_API_KEY"),
            },
            "headless": True,
        }

    def generate_intelligence(self, business_profile: Dict[str, Any], context: str) -> Dict[str, Any]:
        # Extract the core business details from the profile for the prompt
        company_name = business_profile.get("company_name", "the company")
        details = business_profile.get("business_details", {})
        description = details.get("description", "No description available")

        # Step 2 & 3: Dedicated BI analysis using the same LLM provider via ScrapeGraphAI
        bi_prompt = (
            f"You are a Senior Business Analyst. Based on the following Business Profile for {company_name}, "
            f"and this existing context: {context}, generate high-level business intelligence. "
            f"\n\nBusiness Profile:\n{json.dumps(business_profile, indent=2)}\n\n"
            "You MUST return a valid JSON object with exactly these keys:\n"
            "- company_summary: (2-sentence high-level pitch)\n"
            "- services_offered: (list of core products/services)\n"
            "- target_customers: (ideal customer profile)\n"
            "- business_model: (how they make money, e.g., SaaS, Agency)\n"
            "- industry_category: (primary industry)\n"
            "- technologies_used: (list of identified tech stack)\n"
            "- pain_points: (list of likely operational or growth struggles)\n"
            "- sales_opportunities: (specific ways Bilvaleaf can help them)\n"
            "\nEnsure the response is only the JSON object."
        )

        # Use the smart scraper again to process the synthesized profile
        bi_scraper = SmartScraperGraph(prompt=bi_prompt, source=business_profile.get("website", ""), config=self.graph_config)
        result = bi_scraper.run()

        return self._ensure_schema(result)

class IntelligenceManager:
    """Orchestrates AI Intelligence generation and caching."""

    def __init__(self):
        # Decide provider based on environment variable
        provider_type = os.getenv("AI_INTELLIGENCE_PROVIDER", "ollama").lower()
        if provider_type == "openai":
            self.provider = OpenAIProvider()
        elif provider_type == "ollama":
            self.provider = OllamaProvider()
        else:
            raise ValueError(f"Unsupported AI provider: {provider_type}")

    @staticmethod
    def _is_cache_valid(cached: Dict[str, Any]) -> bool:
        """Return True only if the cached insights contain meaningful data.

        A cache entry is considered INVALID when any of the core fields are
        NULL/empty, which indicates a previous generation failed (e.g. LLM
        connection error fell back to an empty schema and got persisted).
        """
        if not cached:
            return False

        def _has_text(value: Any) -> bool:
            return isinstance(value, str) and value.strip() != ""

        def _has_items(value: Any) -> bool:
            # Cached list columns may come back as real lists/deserialized
            # JSON or as raw JSON strings depending on the read path.
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return False
            return isinstance(value, list) and len(value) > 0

        return (
            _has_text(cached.get("company_summary"))
            and _has_items(cached.get("services_offered"))
            and _has_items(cached.get("pain_points"))
            and _has_items(cached.get("sales_opportunities"))
        )

    def get_or_generate_intelligence(self, lead_id: int, business_profile: Dict[str, Any], context: str) -> Dict[str, Any]:
        # 1. Check cache
        cached = get_ai_insights_by_lead_id(lead_id)
        if cached and self._is_cache_valid(cached):
            return dict(cached)

        if cached:
            print(f"AI Intelligence cache for lead {lead_id} is invalid; regenerating.")

        # 2. Generate via Provider
        try:
            insights = self.provider.generate_intelligence(business_profile, context)

            # 3. Persist to DB (upsert overwrites the existing invalid row)
            upsert_ai_insights(
                lead_id=lead_id,
                insights=insights,
                provider=self.provider.__class__.__name__.replace("Provider", "").lower()
            )

            return insights
        except Exception as e:
            # Log error and return empty/fallback structure
            print(f"AI Intelligence Error for lead {lead_id}: {str(e)}")
            raise e

# Singleton instance for the API to use
intelligence_manager = IntelligenceManager()
