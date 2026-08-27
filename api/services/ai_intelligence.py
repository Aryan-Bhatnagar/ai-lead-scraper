import os
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from scrapegraphai.graphs import SmartScraperGraph
from scraper.database import upsert_ai_insights, get_ai_insights_by_lead_id
from langchain_ollama import ChatOllama

from scraper.discovery.providers.google_search_provider import is_valid_client_url

def validate_lead_quality(lead_data: dict) -> bool:
    if not isinstance(lead_data, dict):
        return False
    email = lead_data.get('email')
    phone = lead_data.get('phone')
    website = lead_data.get('website', '') or lead_data.get('url', '')
    
    # Drop leads that have no contact info AND no valid website
    if not email and not phone and (not website or website == 'N/A'):
        return False
        
    # Drop directory portals or competitor URLs
    if website and website != 'N/A' and not is_valid_client_url(website):
        return False
        
    return True

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
        "sales_opportunities": [],
        "requirement_evidence": [],
        "is_buyer_client": True,
        "email": None,
        "phone": None
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

        # Ensure standard list fields are strictly lists of strings for n8n contract safety
        for str_list_key in ["services_offered", "pain_points", "sales_opportunities", "target_customers", "technologies_used"]:
            raw_list = final_result.get(str_list_key) or []
            clean_str_list = []
            if isinstance(raw_list, list):
                for item in raw_list:
                    if isinstance(item, str) and item.strip():
                        clean_str_list.append(item.strip())
                    elif isinstance(item, dict):
                        text = str(item.get("signal") or item.get("quote") or item.get("service") or item.get("pain_point") or "").strip()
                        if text:
                            clean_str_list.append(text)
            final_result[str_list_key] = clean_str_list

        # Strictly sanitize requirement_evidence schema shape & verify non-empty verbatim quotes
        raw_evidence = final_result.get("requirement_evidence") or []
        sanitized_evidence = []
        if isinstance(raw_evidence, list):
            for item in raw_evidence:
                if isinstance(item, dict):
                    sig = str(item.get("signal") or "").strip()
                    quot = str(item.get("quote") or "").strip()
                    src = str(item.get("source") or "Business Profile").strip()
                    
                    # Rule: Do not fabricate quotes! If quote is missing or empty, drop the item.
                    if not quot:
                        continue
                        
                    sanitized_evidence.append({
                        "signal": sig or "Buyer Intent Signal",
                        "quote": quot,
                        "source": src
                    })
                elif isinstance(item, str) and item.strip():
                    item_str = item.strip()
                    # A raw string from the LLM is the verbatim quote text itself
                    sanitized_evidence.append({
                        "signal": "Buyer Intent Signal",
                        "quote": item_str,
                        "source": "Business Profile"
                    })
        final_result["requirement_evidence"] = sanitized_evidence

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

        enable_intent = os.getenv("ENABLE_INTENT_DISCOVERY", "false").lower() in ("true", "1", "t", "yes")
        evidence_instruction = (
            "\n- requirement_evidence: (list of JSON objects strictly matching this exact schema: {\"signal\": \"short label\", \"quote\": \"verbatim quote from source text\", \"source\": \"URL or source\"}.\n"
            "   CRITICAL GROUNDING RULES FOR REQUIREMENT EVIDENCE:\n"
            "   1. Look for ANY explicit evidence indicating the business wants to hire, contract, outsource, or commission design/web/branding/UX work — e.g. 'hiring designer', 'seeking agency partner', 'accepting bids', 'contract search', 'in the market for', 'site needs an update', 'looking for vendor', 'RFP', 'website overhaul', 'logo redesign'.\n"
            "   2. DO NOT include restated business services or general facts (e.g. 'multispecialty dental clinic', 'provides implants', 'real estate broker') as evidence. What a company ALREADY DOES is NOT evidence of buyer intent!\n"
            "   3. Every item MUST be a JSON object with ALL 3 KEYS ('signal', 'quote', 'source'). The 'quote' field MUST contain the exact verbatim text snippet from the business profile. NEVER return plain strings or objects with empty quotes.\n"
            "   4. If there is no explicit hiring, contract, or vendor request in the text, return an empty list [])."
            if enable_intent else ""
        )

        # Step 2 & 3: Pass the Business Profile content to the LLM with a dedicated Business Intelligence prompt
        bi_prompt = (
            f"You are a Senior Business Analyst. Based on the following Business Profile for {company_name}, "
            f"and this existing context: {context}, generate high-level business intelligence. "
            f"\n\nBusiness Profile:\n{json.dumps(business_profile, indent=2)}\n\n"
            "You MUST return a valid JSON object with exactly these keys:\n"
            "- is_buyer_client: (true if this is a potential BUYER CLIENT business that might hire for services, false if a freelancer portfolio or competitor showcase)\n"
            "- email: (verified contact email address if found in text, else null)\n"
            "- phone: (verified contact phone or WhatsApp number if found in text, else null)\n"
            "- company_summary: (2-sentence high-level pitch of what the company does)\n"
            "- services_offered: (list of core products/services THAT THIS COMPANY SELLS OR PROVIDES TO THEIR CUSTOMERS. Example: A real estate broker sells real estate brokerage/property consulting, NOT web design. A dental clinic provides healthcare/dentistry, NOT logo design. NEVER list services they are seeking to hire or buy).\n"
            "- target_customers: (ideal customer profile)\n"
            "- business_model: (how they make money, e.g., SaaS, Agency)\n"
            "- industry_category: (primary industry)\n"
            "- technologies_used: (list of identified tech stack)\n"
            "- pain_points: (list of likely operational or growth struggles)\n"
            "- sales_opportunities: (specific ways Bilvaleaf can help them)\n"
            f"{evidence_instruction}\n"
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

        enable_intent = os.getenv("ENABLE_INTENT_DISCOVERY", "false").lower() in ("true", "1", "t", "yes")
        evidence_instruction = (
            "\n- requirement_evidence: (list of JSON objects strictly matching this exact schema: {\"signal\": \"short label\", \"quote\": \"verbatim quote from source text\", \"source\": \"URL or source\"}.\n"
            "   CRITICAL GROUNDING RULES FOR REQUIREMENT EVIDENCE:\n"
            "   1. Look for ANY explicit evidence indicating the business wants to hire, contract, outsource, or commission design/web/branding/UX work — e.g. 'hiring designer', 'seeking agency partner', 'accepting bids', 'contract search', 'in the market for', 'site needs an update', 'looking for vendor', 'RFP', 'website overhaul', 'logo redesign'.\n"
            "   2. DO NOT include restated business services or general facts (e.g. 'multispecialty dental clinic', 'provides implants', 'real estate broker') as evidence. What a company ALREADY DOES is NOT evidence of buyer intent!\n"
            "   3. Every item MUST be a JSON object with ALL 3 KEYS ('signal', 'quote', 'source'). The 'quote' field MUST contain the exact verbatim text snippet from the business profile. NEVER return plain strings or objects with empty quotes.\n"
            "   4. If there is no explicit hiring, contract, or vendor request in the text, return an empty list [])."
            if enable_intent else ""
        )

        # Step 2 & 3: Dedicated BI analysis using the same LLM provider via ScrapeGraphAI
        bi_prompt = (
            f"You are a Senior Business Analyst. Based on the following Business Profile for {company_name}, "
            f"and this existing context: {context}, generate high-level business intelligence. "
            f"\n\nBusiness Profile:\n{json.dumps(business_profile, indent=2)}\n\n"
            "You MUST return a valid JSON object with exactly these keys:\n"
            "- is_buyer_client: (true if this is a potential BUYER CLIENT business that might hire for services, false if a freelancer portfolio or competitor showcase)\n"
            "- email: (verified contact email address if found in text, else null)\n"
            "- phone: (verified contact phone or WhatsApp number if found in text, else null)\n"
            "- company_summary: (2-sentence high-level pitch of what the company does)\n"
            "- services_offered: (list of core products/services THAT THIS COMPANY SELLS OR PROVIDES TO THEIR CUSTOMERS. Example: A real estate broker sells real estate brokerage/property consulting, NOT web design. A dental clinic provides healthcare/dentistry, NOT logo design. NEVER list services they are seeking to hire or buy).\n"
            "- target_customers: (ideal customer profile)\n"
            "- business_model: (how they make money, e.g., SaaS, Agency)\n"
            "- industry_category: (primary industry)\n"
            "- technologies_used: (list of identified tech stack)\n"
            "- pain_points: (list of likely operational or growth struggles)\n"
            "- sales_opportunities: (specific ways Bilvaleaf can help them)\n"
            f"{evidence_instruction}\n"
            "\nEnsure the response is only the JSON object."
        )

        # Use the smart scraper again to process the synthesized profile
        bi_scraper = SmartScraperGraph(prompt=bi_prompt, source=business_profile.get("website", ""), config=self.graph_config)
        result = bi_scraper.run()

        return self._ensure_schema(result)

class GroqProvider(BaseAIProvider):
    """Groq Llama-3 sub-second implementation of AI Intelligence Provider."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def generate_intelligence(self, business_profile: Dict[str, Any], context: str) -> Dict[str, Any]:
        company_name = business_profile.get("company_name", "the company")
        enable_intent = os.getenv("ENABLE_INTENT_DISCOVERY", "false").lower() in ("true", "1", "t", "yes")
        evidence_instruction = (
            "\n- requirement_evidence: (list of JSON objects strictly matching this exact schema: {\"signal\": \"short label\", \"quote\": \"verbatim quote from source text\", \"source\": \"URL or source\"}.\n"
            "   CRITICAL GROUNDING RULES FOR REQUIREMENT EVIDENCE:\n"
            "   1. Look for ANY explicit evidence indicating the business wants to hire, contract, outsource, or commission design/web/branding/UX work — e.g. 'hiring designer', 'seeking agency partner', 'accepting bids', 'contract search', 'in the market for', 'site needs an update', 'looking for vendor', 'RFP', 'website overhaul', 'logo redesign'.\n"
            "   2. DO NOT include restated business services or general facts (e.g. 'multispecialty dental clinic', 'provides implants', 'real estate broker') as evidence. What a company ALREADY DOES is NOT evidence of buyer intent!\n"
            "   3. Every item MUST be a JSON object with ALL 3 KEYS ('signal', 'quote', 'source'). The 'quote' field MUST contain the exact verbatim text snippet from the business profile. NEVER return plain strings or objects with empty quotes.\n"
            "   4. If there is no explicit hiring, contract, or vendor request in the text, return an empty list [])."
            if enable_intent else ""
        )

        bi_prompt = (
            f"You are a Senior Business Analyst. Based on the following Business Profile for {company_name}, "
            f"and this existing context: {context}, generate high-level business intelligence. "
            f"\n\nBusiness Profile:\n{json.dumps(business_profile, indent=2)}\n\n"
            "You MUST return a valid JSON object with exactly these keys:\n"
            "- is_buyer_client: (true if this is a potential BUYER CLIENT business that might hire for services, false if a freelancer portfolio or competitor showcase)\n"
            "- email: (verified contact email address if found in text, else null)\n"
            "- phone: (verified contact phone or WhatsApp number if found in text, else null)\n"
            "- company_summary: (2-sentence high-level pitch of what the company does)\n"
            "- services_offered: (list of core products/services THAT THIS COMPANY SELLS OR PROVIDES TO THEIR CUSTOMERS).\n"
            "- target_customers: (ideal customer profile)\n"
            "- business_model: (how they make money, e.g., SaaS, Agency)\n"
            "- industry_category: (primary industry)\n"
            "- technologies_used: (list of identified tech stack)\n"
            "- pain_points: (list of likely operational or growth struggles)\n"
            "- sales_opportunities: (specific ways Bilvaleaf can help them)\n"
            f"{evidence_instruction}\n"
            "\nEnsure the response is only the JSON object."
        )

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing")

        import urllib.request
        req_data = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional business analyst. Output valid JSON only."},
                {"role": "user", "content": bi_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=req_data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                content = res_json["choices"][0]["message"]["content"]
                return self._ensure_schema(content)
        except Exception as e:
            print(f"[GroqProvider] API Error: {e}")
            raise e


class IntelligenceManager:
    """Orchestrates AI Intelligence generation and caching."""

    def __init__(self):
        # Decide provider based on environment variable or GROQ_API_KEY presence
        provider_type = os.getenv("AI_INTELLIGENCE_PROVIDER", "").lower()
        groq_key = os.getenv("GROQ_API_KEY")

        if provider_type == "groq" or (groq_key and not provider_type):
            self.provider = GroqProvider()
        elif provider_type == "openai":
            self.provider = OpenAIProvider()
        elif provider_type == "ollama":
            self.provider = OllamaProvider()
        elif groq_key:
            self.provider = GroqProvider()
        else:
            self.provider = OllamaProvider()

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
