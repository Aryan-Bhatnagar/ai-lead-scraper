"""
AI Enrichment Pipeline for Imported Leads.

This module orchestrates the complete AI enrichment flow for leads imported
from various sources (Apollo, Upwork, Google Maps, etc.).

Flow:
1. Website Enrichment - Uses UnifiedEnrichmentEngine to scrape website and build Business Profile
2. AI Intelligence - Uses IntelligenceManager to generate business insights from Business Profile
3. AI Scoring - Calculates opportunity_score with full breakdown using enhanced weights
4. Persistence - Stores all results in leads table + ai_insights + business_profiles
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scraper.database import (
    get_connection,
    upsert_lead,
    upsert_ai_insights,
    get_lead_by_id,
    get_all_leads,
    utc_now,
)
from scraper.discovery.model import UnifiedLead
import importlib
orchestrator_module = importlib.import_module("scraper.import.orchestrator")
ImportOrchestrator = orchestrator_module.ImportOrchestrator
from scraper.scoring.feature_extractor import FeatureExtractor
from scraper.scoring.score_calculator import ScoreCalculator
from scraper.scoring.weight_provider import WeightProvider, default_weight_provider
from scraper.scoring.models import ScoreExplanation


def _safe_lower(value: Any) -> str:
    """Return a lowercase string for a value, guarding against None/dict/list.

    AI insights can contain None, dicts, or lists in string fields (the LLM
    is not always schema-faithful).  Never crash on those — coerce safely.
    """
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, (dict, list)):
        return ""
    if value is None:
        return ""
    return str(value).lower()


def _safe_float(value: Any) -> Optional[float]:
    """Return a float for a value, or None if it can't be parsed.

    Numeric columns (google_rating, maps_review_count, jobs_completed) are
    stored as TEXT in the DB and can arrive as '' or '12 reviews'.  Comparing
    those against ints raises ``'>' not supported between 'str' and 'int'``.
    Never crash on that — coerce safely.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        # '12 reviews' → 12 ; '4.8' → 4.8
        match = re.search(r"[-+]?\d*\.?\d+", stripped)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
    return None


def _safe_int(value: Any) -> Optional[int]:
    """Return an int for a value, or None if it can't be parsed."""
    f = _safe_float(value)
    return int(f) if f is not None else None


@dataclass
class EnrichmentResult:
    """Result of enriching a single lead."""
    lead_id: int
    company_name: str
    success: bool = False
    error: Optional[str] = None

    # Enrichment outputs
    ai_summary: Optional[str] = None
    industry: Optional[str] = None
    company_size_estimate: Optional[str] = None
    decision_maker_guess: Optional[str] = None
    pain_points: List[str] = field(default_factory=list)
    recommended_service: Optional[str] = None
    buying_signals: List[str] = field(default_factory=list)
    outreach_strategy: Optional[str] = None
    ai_confidence: float = 0.0
    opportunity_score: Optional[int] = None
    score_explanation_json: Optional[str] = None
    company_logo: Optional[str] = None

    # Business profile (from website enrichment)
    business_profile: Optional[Dict[str, Any]] = None

    # AI insights (from intelligence manager)
    ai_insights: Optional[Dict[str, Any]] = None


class AIEnrichmentPipeline:
    """
    Orchestrates the complete AI enrichment pipeline for leads.

    This pipeline:
    1. Runs website enrichment via UnifiedEnrichmentEngine
    2. Generates AI intelligence via IntelligenceManager
    3. Computes opportunity_score with full breakdown
    4. Persists all results to database
    """

    def __init__(
        self,
        weight_provider: Optional[WeightProvider] = None,
        enrichment_engine=None,
        intelligence_manager=None,
    ):
        self.wp = weight_provider or default_weight_provider()
        self.extractor = FeatureExtractor()
        self.calculator = ScoreCalculator(self.wp)

        # Lazy-loaded providers (to avoid import cycles)
        self._enrichment_engine = enrichment_engine
        self._intelligence_manager = intelligence_manager

    @property
    def enrichment_engine(self):
        """Lazy load UnifiedEnrichmentEngine."""
        if self._enrichment_engine is None:
            from api.services.enrichment.engine import uee_engine
            self._enrichment_engine = uee_engine
        return self._enrichment_engine

    @property
    def intelligence_manager(self):
        """Lazy load IntelligenceManager."""
        if self._intelligence_manager is None:
            from api.services.ai_intelligence import intelligence_manager
            self._intelligence_manager = intelligence_manager
        return self._intelligence_manager

    def enrich_lead(self, lead_id: int) -> EnrichmentResult:
        """
        Enrich a single lead by ID.

        Args:
            lead_id: The database ID of the lead to enrich

        Returns:
            EnrichmentResult with all enrichment outputs
        """
        # Get lead from database
        lead_row = get_lead_by_id(lead_id)
        if not lead_row:
            return EnrichmentResult(
                lead_id=lead_id,
                company_name="Unknown",
                success=False,
                error=f"Lead {lead_id} not found"
            )

        # Convert to UnifiedLead for processing
        lead = self._row_to_unified_lead(lead_row)

        return self._enrich_unified_lead(lead, lead_id)

    def _enrich_unified_lead(self, lead: UnifiedLead, lead_id: int) -> EnrichmentResult:
        """Run the full enrichment pipeline on a UnifiedLead."""
        result = EnrichmentResult(
            lead_id=lead_id,
            company_name=lead.company_name or "Unknown"
        )

        try:
            # Step 1: Website Enrichment (if website available)
            website = lead.website
            if website:
                print(f"  [Enrichment] Running website enrichment for {lead.company_name} ({website})")
                profile = self.enrichment_engine.enrich_lead(lead_id, website, lead.company_name)
                result.business_profile = profile

                # Extract logo/favicon from profile
                favicon = profile.get("website_metadata", {}).get("favicon")
                if favicon:
                    result.company_logo = favicon
            else:
                print(f"  [Enrichment] No website for {lead.company_name}, skipping website enrichment")
                result.business_profile = self._create_minimal_profile(lead)

            # Step 2: AI Intelligence Generation
            print(f"  [Enrichment] Generating AI intelligence for {lead.company_name}")
            context = self._build_context(lead)
            insights = self.intelligence_manager.get_or_generate_intelligence(
                lead_id=lead_id,
                business_profile=result.business_profile,
                context=context
            )
            result.ai_insights = insights

            # Extract key fields from AI insights
            result.ai_summary = insights.get("company_summary")
            result.industry = insights.get("industry_category")
            result.pain_points = insights.get("pain_points", []) or []
            result.recommended_service = self._derive_recommended_service(insights)
            result.decision_maker_guess = self._guess_decision_maker(insights, lead)
            result.company_size_estimate = self._estimate_company_size(insights, lead, result.business_profile)
            result.buying_signals = insights.get("sales_opportunities", []) or []
            result.outreach_strategy = self._derive_outreach_strategy(
                insights, result.recommended_service, result.decision_maker_guess
            )

            # Step 3: Calculate AI Confidence
            result.ai_confidence = self._calculate_ai_confidence(insights, result.business_profile)

            # Step 4: Calculate Opportunity Score with full breakdown
            result.opportunity_score, result.score_explanation_json = self._calculate_opportunity_score(
                lead, result.business_profile, insights
            )

            # Step 5: Persist all results
            self._persist_enrichment_results(lead_id, result)

            result.success = True
            print(f"  [Enrichment] Completed for {lead.company_name}: opportunity_score={result.opportunity_score}, ai_confidence={result.ai_confidence:.2f}")

        except Exception as e:
            result.success = False
            result.error = str(e)
            print(f"  [Enrichment] FAILED for {lead.company_name}: {e}")

        return result

    def _create_minimal_profile(self, lead: UnifiedLead) -> Dict[str, Any]:
        """Create a minimal business profile from lead data when no website."""
        return {
            # `source_id` does not exist on Provenance — use the lead's own id.
            "lead_id": getattr(lead, "id", None) or 0,
            "company_name": lead.company_name,
            "website": lead.website,
            "industry": lead.industry,
            "location": {
                "city": lead.location.city if lead.location else None,
                "state": lead.location.region if lead.location else None,
                "country": lead.location.country if lead.location else None,
                "address": lead.address,
            },
            "contact_info": {
                "emails": list(lead.emails),
                "phones": list(lead.phones),
                "social_links": [],
                "contact_page": None,
            },
            "business_details": {
                "description": lead.description,
                "size": None,
                "founding_year": None,
                "category": lead.industry,
                "tagline": None,
                "services": [],
                "products": [],
                "technologies_used": [],
                "business_hours": None,
            },
            "website_metadata": {
                "title": None,
                "meta_description": None,
                "favicon": None,
                "language": None,
            },
            "technical_signals": {
                "cms": None,
                "analytics": [],
                "framework": None,
            },
            "raw_sources": {},
            "updated_at": utc_now(),
        }

    def _build_context(self, lead: UnifiedLead) -> str:
        """Build context string for AI intelligence generation."""
        parts = []
        if lead.company_name:
            parts.append(f"Company: {lead.company_name}")
        if lead.industry:
            parts.append(f"Industry: {lead.industry}")
        if lead.location and (lead.location.city or lead.location.country):
            loc_parts = []
            if lead.location.city:
                loc_parts.append(lead.location.city)
            if lead.location.country:
                loc_parts.append(lead.location.country)
            parts.append(f"Location: {', '.join(loc_parts)}")
        if lead.description:
            parts.append(f"Description: {lead.description[:500]}")
        if lead.skills:
            parts.append(f"Skills: {', '.join(lead.skills[:10])}")
        if lead.categories:
            parts.append(f"Categories: {', '.join(lead.categories[:10])}")
        if lead.provenance and lead.provenance.source:
            parts.append(f"Source: {lead.provenance.source}")

        return " | ".join(parts) if parts else "Limited information available"

    def _derive_recommended_service(self, insights: Dict[str, Any]) -> Optional[str]:
        """Derive BilvaLeaf service recommendation from AI insights."""
        services_offered = insights.get("services_offered", []) or []
        pain_points = insights.get("pain_points", []) or []
        sales_opps = insights.get("sales_opportunities", []) or []
        business_model = _safe_lower(insights.get("business_model"))

        # Service mapping based on insights
        service_keywords = {
            "AI/ML Development": ["ai", "machine learning", "ml", "artificial intelligence", "data science"],
            "Custom Software Development": ["software", "development", "application", "app", "platform", "saas"],
            "Web Development": ["web", "website", "frontend", "backend", "full stack", "react", "vue", "angular"],
            "Mobile App Development": ["mobile", "ios", "android", "app", "flutter", "react native"],
            "Cloud/DevOps": ["cloud", "aws", "azure", "gcp", "devops", "kubernetes", "docker", "infrastructure"],
            "Data Engineering": ["data", "analytics", "etl", "pipeline", "warehouse", "big data"],
            "UI/UX Design": ["design", "ux", "ui", "user experience", "interface", "figma"],
            "QA/Testing": ["testing", "qa", "quality assurance", "automation", "test"],
        }

        # Check sales opportunities first (most specific)
        for opp in sales_opps:
            opp_lower = _safe_lower(opp)
            if not opp_lower:
                continue
            for service, keywords in service_keywords.items():
                if any(kw in opp_lower for kw in keywords):
                    return service

        # Check pain points
        for pain in pain_points:
            pain_lower = _safe_lower(pain)
            if not pain_lower:
                continue
            for service, keywords in service_keywords.items():
                if any(kw in pain_lower for kw in keywords):
                    return service

        # Check services offered
        for svc in services_offered:
            svc_lower = _safe_lower(svc)
            if not svc_lower:
                continue
            for service, keywords in service_keywords.items():
                if any(kw in svc_lower for kw in keywords):
                    return service

        # Check business model
        if "saas" in business_model:
            return "Custom Software Development"
        if "agency" in business_model or "consulting" in business_model:
            return "Custom Software Development"
        if "ecommerce" in business_model or "e-commerce" in business_model:
            return "Web Development"

        return "Custom Software Development"  # Default

    def _derive_outreach_strategy(
        self,
        insights: Dict[str, Any],
        recommended_service: Optional[str],
        decision_maker: Optional[str],
    ) -> Optional[str]:
        """Build a concise outreach strategy from AI insights."""
        pain_points = insights.get("pain_points", []) or []
        sales_opps = insights.get("sales_opportunities", []) or []
        target_customers = insights.get("target_customers", []) or []

        def _first_text(items):
            for item in items:
                if isinstance(item, str) and item.strip():
                    return item.strip()
            return None

        parts = []
        if decision_maker:
            parts.append(f"Target decision maker: {decision_maker}")
        if recommended_service:
            parts.append(f"Lead with BilvaLeaf {recommended_service}")
        pain = _first_text(pain_points)
        if pain:
            parts.append(f"Address pain point: {pain}")
        angle = _first_text(sales_opps)
        if angle:
            parts.append(f"Angle: {angle}")
        icp = _first_text(target_customers)
        if icp:
            parts.append(f"ICP signal: {icp}")

        if parts:
            return ". ".join(parts) + "."
        return "Standard sequence: connect → qualify → propose a pilot."

    def _guess_decision_maker(self, insights: Dict[str, Any], lead: UnifiedLead) -> Optional[str]:
        """Guess the likely decision maker based on company info."""
        target_customers = insights.get("target_customers", [])
        business_model = _safe_lower(insights.get("business_model"))
        company_size = insights.get("company_size") or lead.metadata.get("company_size_estimate")

        # If we have a contact from the lead, use that
        if lead.contact_name:
            return f"{lead.contact_name} ({lead.contact_role or 'Decision Maker'})"

        # Guess based on company size and model
        if company_size:
            size_lower = str(company_size).lower()
            if any(s in size_lower for s in ["1-10", "1-50", "startup", "small"]):
                return "Founder/CEO"
            elif "50-200" in size_lower or "medium" in size_lower:
                return "VP Engineering / CTO"
            elif "200" in size_lower or "large" in size_lower or "enterprise" in size_lower:
                return "VP Engineering / Director of Engineering"

        # Based on business model
        if "saas" in business_model:
            return "VP Engineering / CTO"
        if "agency" in business_model:
            return "Founder / Creative Director"

        return "CTO / VP Engineering"

    def _estimate_company_size(
        self,
        insights: Dict[str, Any],
        lead: UnifiedLead,
        profile: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Estimate company size from various signals."""
        # Check AI insights first
        if insights.get("company_size"):
            return insights["company_size"]

        # Check business profile
        if profile and profile.get("business_details", {}).get("size"):
            return profile["business_details"]["size"]

        # Check lead fields
        if lead.metadata.get("company_size_estimate"):
            return lead.metadata["company_size_estimate"]

        # Estimate from review count, jobs, etc.  (Safe coerce — these fields
        # can arrive as strings from discovery or the DB.)
        signals = []

        review_count = _safe_int(lead.maps_review_count)
        if review_count is not None:
            if review_count > 100:
                signals.append("100+ reviews")
            elif review_count > 20:
                signals.append("20-100 reviews")
            elif review_count > 0:
                signals.append("few reviews")

        jobs = _safe_int(lead.jobs_completed)
        if jobs is not None:
            if jobs > 50:
                signals.append(f"{jobs} jobs completed")
            elif jobs > 10:
                signals.append(f"{jobs} jobs completed")

        if lead.categories:
            signals.append(f"{len(lead.categories)} categories")

        if lead.skills:
            signals.append(f"{len(lead.skills)} skills")

        if signals:
            return f"Estimated: {', '.join(signals)}"

        return None

    def _calculate_ai_confidence(
        self,
        insights: Dict[str, Any],
        profile: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate confidence in AI enrichment (0.0-1.0)."""
        score = 0.0

        # Check insights completeness
        if insights.get("company_summary") and len(insights["company_summary"]) > 50:
            score += 0.2
        if insights.get("services_offered"):
            score += 0.15
        if insights.get("pain_points"):
            score += 0.15
        if insights.get("sales_opportunities"):
            score += 0.15
        if insights.get("industry_category"):
            score += 0.1
        if insights.get("business_model"):
            score += 0.1
        if insights.get("technologies_used"):
            score += 0.1

        # Check profile completeness
        if profile:
            biz_details = profile.get("business_details", {})
            if biz_details.get("description"):
                score += 0.05
            if biz_details.get("services"):
                score += 0.05

        return min(score, 1.0)

    def _calculate_opportunity_score(
        self,
        lead: UnifiedLead,
        profile: Optional[Dict[str, Any]],
        insights: Dict[str, Any]
    ) -> tuple[int, str]:
        """
        Calculate opportunity score with full breakdown.

        This uses an extended feature set that includes:
        - All base features from FeatureExtractor
        - google_rating (from Maps data)
        - review_count (from Maps data)
        - company_size (estimated)
        - ai_enrichment_quality (from AI confidence)
        """
        # Get base quality ratios
        base_ratios = self.extractor.extract_all(lead)

        # Add extended features for opportunity scoring
        extended_ratios = dict(base_ratios)

        # google_rating
        rating_f = _safe_float(lead.google_rating)
        if rating_f is not None and rating_f > 0:
            extended_ratios["google_rating"] = min(rating_f / 5.0, 1.0)
        else:
            extended_ratios["google_rating"] = 0.0

        # review_count
        review_count = _safe_int(lead.maps_review_count)
        if review_count is not None and review_count > 0:
            extended_ratios["review_count"] = min(review_count / 100.0, 1.0)
        else:
            extended_ratios["review_count"] = 0.0

        # company_size
        extended_ratios["company_size"] = self._extract_company_size_ratio(lead, profile, insights)

        # ai_enrichment_quality
        extended_ratios["ai_enrichment_quality"] = self._extract_ai_enrichment_quality(insights, profile)

        # Calculate using weight provider (which has extended weights from YAML)
        overall, breakdowns = self.calculator.calculate(extended_ratios)

        # Build explanation JSON
        explanation = ScoreExplanation(
            overall_score=overall,
            breakdowns=breakdowns,
            quality_tier=self.wp.quality_tier(overall),
        )

        explanation_json = json.dumps({
            "overall_score": explanation.overall_score,
            "quality_tier": explanation.quality_tier,
            "breakdowns": [
                {
                    "feature": b.feature,
                    "label": b.label,
                    "weight": b.weight,
                    "quality_ratio": b.quality_ratio,
                    "contribution": b.contribution,
                    "detail": b.detail,
                }
                for b in explanation.breakdowns
            ]
        })

        return overall, explanation_json

    def _extract_company_size_ratio(
        self,
        lead: UnifiedLead,
        profile: Optional[Dict[str, Any]],
        insights: Dict[str, Any]
    ) -> float:
        """Extract company size quality ratio (0.0-1.0)."""
        # Check explicit size from profile/insights
        size_str = None
        if profile:
            size_str = profile.get("business_details", {}).get("size")
        if not size_str:
            size_str = insights.get("company_size")
        if not size_str and lead.metadata.get("company_size_estimate"):
            size_str = lead.metadata["company_size_estimate"]

        if size_str:
            size_lower = str(size_str).lower()
            # Numeric sizes first — the DB stores things like '5' or '10001',
            # and substring matching missed small values ('5' matches no band).
            size_num = _safe_int(size_str)
            if size_num is not None:
                if size_num >= 1000:
                    return 1.0
                if size_num >= 500:
                    return 0.8
                if size_num >= 100:
                    return 0.6
                if size_num >= 10:
                    return 0.4
                if size_num >= 1:
                    return 0.3
            if any(s in size_lower for s in ["enterprise", "large"]):
                return 1.0
            elif any(s in size_lower for s in ["medium"]):
                return 0.7
            elif any(s in size_lower for s in ["small"]):
                return 0.5
            elif any(s in size_lower for s in ["startup"]):
                return 0.3

        # Fallback to signals
        signals = 0
        review_count = _safe_int(lead.maps_review_count)
        if review_count is not None and review_count > 0:
            signals += min(review_count / 100.0, 1.0) * 0.5
        jobs = _safe_int(lead.jobs_completed)
        if jobs is not None and jobs > 0:
            signals += min(jobs / 50.0, 1.0) * 0.5
        if lead.categories:
            signals += min(len(lead.categories) / 10.0, 1.0) * 0.2
        if lead.skills:
            signals += min(len(lead.skills) / 20.0, 1.0) * 0.2

        return min(signals, 1.0)

    def _extract_ai_enrichment_quality(
        self,
        insights: Dict[str, Any],
        profile: Optional[Dict[str, Any]]
    ) -> float:
        """Extract AI enrichment quality ratio (0.0-1.0)."""
        score = 0.0

        if insights.get("company_summary") and len(insights["company_summary"]) > 50:
            score += 0.3
        if insights.get("services_offered"):
            score += 0.15
        if insights.get("pain_points"):
            score += 0.15
        if insights.get("sales_opportunities"):
            score += 0.15
        if insights.get("industry_category"):
            score += 0.1
        if insights.get("technologies_used"):
            score += 0.1
        if insights.get("business_model"):
            score += 0.05

        # Profile adds confidence
        if profile and profile.get("business_details", {}).get("description"):
            score += 0.1

        return min(score, 1.0)

    def _persist_enrichment_results(self, lead_id: int, result: EnrichmentResult):
        """Persist all enrichment results to database."""
        with get_connection() as conn:
            # Update leads table with enrichment fields
            update_fields = []
            params = []

            if result.ai_summary is not None:
                update_fields.append("ai_summary = ?")
                params.append(result.ai_summary)
            if result.industry is not None:
                update_fields.append("industry = ?")
                params.append(result.industry)
            if result.company_size_estimate is not None:
                update_fields.append("company_size_estimate = ?")
                params.append(result.company_size_estimate)
            if result.decision_maker_guess is not None:
                update_fields.append("decision_maker_guess = ?")
                params.append(result.decision_maker_guess)
            if result.pain_points is not None:
                update_fields.append("pain_points = ?")
                params.append(json.dumps(result.pain_points))
            if result.recommended_service is not None:
                update_fields.append("recommended_service = ?")
                params.append(result.recommended_service)
            if result.buying_signals:
                update_fields.append("buying_signals = ?")
                params.append(json.dumps(result.buying_signals))
            if result.outreach_strategy is not None:
                update_fields.append("outreach_strategy = ?")
                params.append(result.outreach_strategy)
            if result.ai_confidence > 0:
                update_fields.append("ai_confidence = ?")
                params.append(result.ai_confidence)
            if result.opportunity_score is not None:
                update_fields.append("opportunity_score = ?")
                params.append(result.opportunity_score)
            if result.score_explanation_json is not None:
                update_fields.append("score_explanation_json = ?")
                params.append(result.score_explanation_json)
            if result.company_logo is not None:
                update_fields.append("company_logo = ?")
                params.append(result.company_logo)

            # Always update ai_score (use opportunity_score as ai_score)
            if result.opportunity_score is not None:
                update_fields.append("ai_score = ?")
                params.append(result.opportunity_score)

            update_fields.append("updated_at = ?")
            params.append(utc_now())

            if update_fields:
                params.append(lead_id)
                conn.execute(
                    f"UPDATE leads SET {', '.join(update_fields)} WHERE id = ?",
                    params
                )

            # AI insights are already persisted by IntelligenceManager
            # Business profile is already persisted by UnifiedEnrichmentEngine

    def _row_to_unified_lead(self, row: Dict[str, Any]) -> UnifiedLead:
        """Convert database row to UnifiedLead for processing."""
        # Parse JSON fields
        emails = []
        if row.get("email"):
            emails = [e.strip() for e in row["email"].split(",") if e.strip()]

        phones = []
        if row.get("phone"):
            phones = [p.strip() for p in row["phone"].split(",") if p.strip()]

        socials = {}
        if row.get("socials_json"):
            try:
                socials = json.loads(row["socials_json"])
            except json.JSONDecodeError:
                pass

        categories = []
        if row.get("categories"):
            try:
                categories = json.loads(row["categories"])
            except json.JSONDecodeError:
                categories = [c.strip() for c in row["categories"].split(",") if c.strip()]

        skills = []
        if row.get("skills"):
            try:
                skills = json.loads(row["skills"])
            except json.JSONDecodeError:
                skills = [s.strip() for s in row["skills"].split(",") if s.strip()]

        location = None
        if row.get("city") or row.get("country"):
            from scraper.discovery.model import LocationData
            location = LocationData(
                city=row.get("city"),
                region=row.get("region") or row.get("state"),
                country=row.get("country"),
            )

        provenance = None
        if row.get("source") or row.get("source_url"):
            from scraper.discovery.model import Provenance
            provenance = Provenance(
                source=row.get("source", "Unknown"),
                source_url=row.get("source_url"),
                confidence=0.8,  # Default for imported leads
            )

        # Parse pain_points
        pain_points = []
        if row.get("pain_points"):
            try:
                pain_points = json.loads(row["pain_points"])
            except json.JSONDecodeError:
                pass

        # Parse buying_signals
        buying_signals = []
        if row.get("buying_signals"):
            try:
                buying_signals = json.loads(row["buying_signals"])
            except json.JSONDecodeError:
                buying_signals = [row["buying_signals"]]

        from scraper.discovery.model import UnifiedLead
        return UnifiedLead(
            id=row.get("id"),
            company_name=row.get("company_name") or "",
            company_name_norm=(row.get("company_name") or "").lower().strip(),
            industry=row.get("industry"),
            description=row.get("company_description") or row.get("description"),
            emails=emails,
            phones=phones,
            website=row.get("website"),
            location=location,
            categories=categories,
            skills=skills,
            socials=socials,
            # Coerce numeric columns — the DB stores them as TEXT and they can
            # be '' or '12 reviews'.  Comparisons later would otherwise crash.
            maps_rating=_safe_float(row.get("google_rating")),
            maps_review_count=_safe_int(row.get("maps_review_count")),
            rating=_safe_float(row.get("rating")),
            jobs_completed=_safe_int(row.get("jobs_completed")),
            provenance=provenance,
            # Extended fields stored in metadata
            metadata={
                "company_size_estimate": row.get("company_size_estimate"),
                "ai_summary": row.get("ai_summary"),
                "pain_points": pain_points,
                "recommended_service": row.get("recommended_service"),
                "decision_maker_guess": row.get("decision_maker_guess"),
                "buying_signals": buying_signals,
                "outreach_strategy": row.get("outreach_strategy"),
            },
        )

    def enrich_all_unenriched(self, limit: Optional[int] = None) -> List[EnrichmentResult]:
        """
        Enrich all leads that don't have AI enrichment yet.

        Args:
            limit: Maximum number of leads to enrich (None for all)

        Returns:
            List of EnrichmentResult for each lead
        """
        with get_connection() as conn:
            query = """
                SELECT id, company_name FROM leads
                WHERE (ai_summary IS NULL OR ai_summary = '')
                AND (website IS NOT NULL AND website != '')
                ORDER BY id
            """
            if limit:
                query += f" LIMIT {limit}"

            rows = conn.execute(query).fetchall()

        results = []
        for row in rows:
            result = self.enrich_lead(row["id"])
            results.append(result)

        return results


def run_enrichment_pipeline(lead_ids: Optional[List[int]] = None, limit: Optional[int] = None) -> List[EnrichmentResult]:
    """
    Convenience function to run the enrichment pipeline.

    Args:
        lead_ids: Specific lead IDs to enrich (None = all unenriched)
        limit: Maximum number to process

    Returns:
        List of EnrichmentResult
    """
    pipeline = AIEnrichmentPipeline()

    if lead_ids:
        results = []
        for lead_id in lead_ids:
            result = pipeline.enrich_lead(lead_id)
            results.append(result)
        return results
    else:
        return pipeline.enrich_all_unenriched(limit=limit)


if __name__ == "__main__":
    # Test run
    print("Running AI Enrichment Pipeline test...")
    results = run_enrichment_pipeline(limit=5)
    print(f"\nCompleted {len(results)} enrichments")
    for r in results:
        status = "✓" if r.success else "✗"
        print(f"  {status} {r.company_name}: score={r.opportunity_score}, confidence={r.ai_confidence:.2f}")
        if r.error:
            print(f"    Error: {r.error}")