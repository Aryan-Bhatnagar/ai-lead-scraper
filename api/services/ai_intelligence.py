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
    def generate_intelligence(self, url: str, company_name: str, context: str) -> Dict[str, Any]:
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

    def generate_intelligence(self, url: str, company_name: str, context: str) -> Dict[str, Any]:
        # Step 1: Use ScrapeGraphAI only to extract website content
        extraction_prompt = (
            f"Extract all relevant business information from the website of {company_name}. "
            "Focus on what they do, who they serve, their products, services, and any visible tech stack."
        )

        smart_scraper = SmartScraperGraph(prompt=extraction_prompt, source=url, config=self.graph_config)
        extracted_content = smart_scraper.run()

        # Step 2 & 3: Pass extracted content to the LLM with a dedicated Business Intelligence prompt
        bi_prompt = (
            f"You are a Senior Business Analyst. Based on the following extracted website content for {company_name}, "
            f"and this existing context: {context}, generate high-level business intelligence. "
            f"\n\nExtracted Content:\n{json.dumps(extracted_content)}\n\n"
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
            response = self.llm.invoke(bi_prompt)
            # ChatOllama returns a BaseMessage; the content is in .content
            result = response.content
        except Exception as e:
            print(f"Error during BI analysis phase: {e}")
            # Fallback: if LLM call fails, try to use the extracted content as is
            result = extracted_content

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

    def generate_intelligence(self, url: str, company_name: str, context: str) -> Dict[str, Any]:
        # Step 1: Use ScrapeGraphAI only to extract website content
        extraction_prompt = (
            f"Extract all relevant business information from the website of {company_name}. "
            "Focus on what they do, who they serve, their products, services, and any visible tech stack."
        )
        smart_scraper = SmartScraperGraph(prompt=extraction_prompt, source=url, config=self.graph_config)
        extracted_content = smart_scraper.run()

        # Step 2 & 3: Dedicated BI analysis using the same LLM provider via ScrapeGraphAI
        # (since OpenAI doesn't have a local API endpoint like Ollama, we reuse the Graph)
        bi_prompt = (
            f"You are a Senior Business Analyst. Based on the following extracted website content for {company_name}, "
            f"and this existing context: {context}, generate high-level business intelligence. "
            f"\n\nExtracted Content:\n{json.dumps(extracted_content)}\n\n"
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

        # Use the smart scraper again to process the extracted content
        # In a real-world scenario we'd use the OpenAI SDK directly, but for consistency
        # with the provider's config, we use the Graph with the content as source if possible
        # or simply perform another run.
        bi_scraper = SmartScraperGraph(prompt=bi_prompt, source=url, config=self.graph_config)
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

    def get_or_generate_intelligence(self, lead_id: int, website: str, company_name: str, context: str) -> Dict[str, Any]:
        # 1. Check cache
        cached = get_ai_insights_by_lead_id(lead_id)
        if cached:
            return dict(cached)

        # 2. Generate via Provider
        try:
            insights = self.provider.generate_intelligence(website, company_name, context)

            # 3. Persist to DB
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
