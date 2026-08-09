"""
Recommendation engine for generating lead recommendations.
"""

from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime

from .priority_rules import determine_priority
from .next_action import determine_next_action
from .recommendation_models import Recommendation


class RecommendationEngine:
    """Engine for generating recommendations for leads."""

    def __init__(self):
        pass

    def generate_recommendation(self, lead: dict, analytics_data: dict = None) -> Recommendation:
        """
        Generate a recommendation for a single lead.

        Args:
            lead: Dictionary containing lead data from the database
            analytics_data: Optional pre-computed analytics data for context

        Returns:
            Recommendation object
        """
        lead_id = lead.get("id")
        score = lead.get("quality_score", 0) or 0
        lifecycle = lead.get("lead_status", "NEW")
        source = self._extract_source(lead.get("source_url", ""))
        has_website = bool(lead.get("website"))
        has_email = bool(lead.get("email"))
        company_size = self._estimate_company_size(lead)
        location = lead.get("country", "")
        days_since_created = self._days_since_created(lead)
        provider_confidence = self._get_provider_confidence(lead, analytics_data)

        # Determine priority
        priority = determine_priority(
            lead=lead,
            score=score,
            lifecycle=lifecycle,
            source=source,
            has_website=has_website,
            has_email=has_email,
            company_size=company_size,
            location=location,
            days_since_created=days_since_created,
            provider_confidence=provider_confidence
        )

        # Determine next action
        next_action = determine_next_action(
            lead=lead,
            priority=priority,
            score=score,
            lifecycle=lifecycle,
            has_website=has_website,
            has_email=has_email
        )

        # Calculate confidence (0.0 to 1.0)
        confidence = self._calculate_confidence(
            lead=lead,
            score=score,
            lifecycle=lifecycle,
            has_website=has_website,
            has_email=has_email,
            provider_confidence=provider_confidence
        )

        # Generate reasons
        reasons = self._generate_reasons(
            lead=lead,
            score=score,
            lifecycle=lifecycle,
            source=source,
            has_website=has_website,
            has_email=has_email,
            priority=priority,
            next_action=next_action
        )

        # Determine suggested outreach method
        suggested_outreach = self._determine_outreach_method(
            has_email=has_email,
            has_website=has_website,
            lead=lead
        )

        # Determine risk level
        risk_level = self._determine_risk_level(
            score=score,
            lifecycle=lifecycle,
            days_since_created=days_since_created
        )

        # Estimate conversion probability
        estimated_conversion = self._estimate_conversion(
            score=score,
            lifecycle=lifecycle,
            has_website=has_website,
            has_email=has_email,
            priority=priority
        )

        return Recommendation(
            lead_id=lead_id,
            priority=priority,
            next_action=next_action,
            confidence=round(confidence, 2),
            reasons=reasons,
            suggested_outreach=suggested_outreach,
            risk_level=risk_level,
            estimated_conversion=round(estimated_conversion, 2)
        )

    def _extract_source(self, source_url: str) -> str:
        """Extract domain/source from URL."""
        if not source_url:
            return "unknown"
        try:
            from urllib.parse import urlparse
            parsed = urlparse(source_url)
            domain = parsed.netloc
            if not domain:
                return "unknown"
            # Remove www.
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.split('.')[0]  # Return base domain name
        except Exception:
            return "unknown"

    def _estimate_company_size(self, lead: dict) -> str:
        """Estimate company size from available data."""
        # Simple heuristic based on employee count if available, else unknown
        # Since we don't have employee count, we'll return unknown
        # Could be enhanced with website scraping or other data sources
        return "Unknown"

    def _days_since_created(self, lead: dict) -> int:
        """Calculate days since lead was created."""
        created_at = lead.get("created_at")
        if not created_at:
            return 0
        try:
            from datetime import datetime
            if isinstance(created_at, str):
                # Try to parse ISO format
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                dt = created_at
            delta = datetime.utcnow() - dt
            return max(0, delta.days)
        except Exception:
            return 0

    def _get_provider_confidence(self, lead: dict, analytics_data: dict = None) -> float:
        """Get confidence score from the provider/source."""
        # We don't have direct provider confidence in the lead model
        # Could be derived from data_quality or source reliability
        # For now, return a default based on data_quality
        data_quality = lead.get("data_quality", "").upper()
        if data_quality == "HIGH":
            return 0.9
        elif data_quality == "MEDIUM":
            return 0.7
        elif data_quality == "LOW":
            return 0.4
        else:
            return 0.5

    def _calculate_confidence(self, lead: dict, score: int, lifecycle: str,
                            has_website: bool, has_email: bool,
                            provider_confidence: float) -> float:
        """Calculate confidence in the recommendation."""
        # Base confidence from data quality and completeness
        confidence = 0.5  # Start with medium

        # Adjust based on score
        if score >= 80:
            confidence += 0.2
        elif score >= 60:
            confidence += 0.1
        elif score < 40:
            confidence -= 0.1

        # Adjust based on data completeness
        if has_website and has_email:
            confidence += 0.15
        elif has_website or has_email:
            confidence += 0.05

        # Adjust based on lifecycle (more mature lifecycles = higher confidence)
        lifecycle_confidence = {
            "NEW": 0.0,
            "DISCOVERED": 0.05,
            "ENRICHED": 0.1,
            "SCORED": 0.15,
            "CONTACTED": 0.1,
            "RESPONDED": 0.15,
            "QUALIFIED": 0.2,
            "CUSTOMER": 0.25,
            "LOST": -0.1
        }
        confidence += lifecycle_confidence.get(lifecycle, 0.0)

        # Incorporate provider confidence
        confidence += (provider_confidence - 0.5) * 0.2  # Scale to -0.1 to +0.1

        # Clamp between 0.1 and 0.95
        return max(0.1, min(0.95, confidence))

    def _generate_reasons(self, lead: dict, score: int, lifecycle: str,
                        source: str, has_website: bool, has_email: bool,
                        priority: str, next_action: str) -> List[str]:
        """Generate human-readable reasons for the recommendation."""
        reasons = []

        # Score-based reasons
        if score >= 85:
            reasons.append(f"High lead score ({score}) indicates strong potential")
        elif score >= 65:
            reasons.append(f"Good lead score ({score}) shows moderate potential")
        elif score >= 50:
            reasons.append(f"Average lead score ({score}) suggests reasonable potential")
        else:
            reasons.append(f"Low lead score ({score}) indicates limited immediate potential")

        # Lifecycle-based reasons
        lifecycle_reasons = {
            "NEW": "Recently discovered lead requiring initial research",
            "DISCOVERED": "Lead has been discovered but not yet engaged",
            "ENRICHED": "Additional information available for better targeting",
            "SCORED": "Lead has been evaluated and scored",
            "CONTACTED": "Initial contact has been made",
            "RESPONDED": "Lead has shown engagement by responding",
            "QUALIFIED": "Lead meets qualification criteria for sales",
            "CUSTOMER": "Lead is already a customer - consider upsell/retention",
            "LOST": "Lead was previously lost but may warrant re-evaluation"
        }
        if lifecycle in lifecycle_reasons:
            reasons.append(lifecycle_reasons[lifecycle])

        # Source-based reasons
        if source and source != "unknown":
            reasons.append(f"Source '{source}' has demonstrated good lead quality")

        # Contact information reasons
        if has_website and has_email:
            reasons.append("Complete contact information (website and email) enables multi-channel outreach")
        elif has_website:
            reasons.append("Website available for research and potential contact forms")
        elif has_email:
            reasons.append("Email address available for direct outreach")
        else:
            reasons.append("Limited contact information available - may require additional research")

        # Priority-based reason
        reasons.append(f"Assigned {priority} priority based on overall assessment")

        # Next action reason
        if next_action != "Ignore":
            reasons.append(f"Recommended next action: {next_action}")

        return reasons

    def _determine_outreach_method(self, has_email: bool, has_website: bool,
                                 lead: dict) -> str:
        """Determine the suggested outreach method."""
        if has_email:
            return "Email"
        elif has_website:
            # Could also consider phone if available, but we don't have phone reliably
            return "Website Contact Form"
        else:
            # Fallback to LinkedIn or research
            return "Research Required"

    def _determine_risk_level(self, score: int, lifecycle: str,
                            days_since_created: int) -> str:
        """Determine risk level associated with pursuing this lead."""
        risk_score = 0

        # Lower score = higher risk
        if score < 50:
            risk_score += 3
        elif score < 70:
            risk_score += 1

        # Older leads = higher risk (stale)
        if days_since_created > 90:
            risk_score += 2
        elif days_since_created > 30:
            risk_score += 1

        # Certain lifecycles are riskier
        risky_lifecycles = ["LOST", "NEW"]
        if lifecycle in risky_lifecycles:
            risk_score += 1

        # Convert to risk level
        if risk_score >= 4:
            return "High"
        elif risk_score >= 2:
            return "Medium"
        else:
            return "Low"

    def _estimate_conversion(self, score: int, lifecycle: str,
                           has_website: bool, has_email: bool,
                           priority: str) -> float:
        """Estimate the probability of conversion."""
        # Base conversion rate
        conversion = 0.1  # 10% base

        # Score contribution (0-0.4)
        if score >= 90:
            conversion += 0.4
        elif score >= 80:
            conversion += 0.3
        elif score >= 70:
            conversion += 0.2
        elif score >= 60:
            conversion += 0.1

        # Lifecycle contribution (0-0.3)
        lifecycle_conversion = {
            "NEW": 0.05,
            "DISCOVERED": 0.08,
            "ENRICHED": 0.1,
            "SCORED": 0.12,
            "CONTACTED": 0.15,
            "RESPONDED": 0.2,
            "QUALIFIED": 0.25,
            "CUSTOMER": 0.0,  # Already converted
            "LOST": 0.02
        }
        conversion += lifecycle_conversion.get(lifecycle, 0.0)

        # Contact info contribution (0-0.1)
        if has_website and has_email:
            conversion += 0.1
        elif has_website or has_email:
            conversion += 0.05

        # Priority adjustment (already factored in above, but slight boost)
        priority_bonus = {
            "Critical": 0.1,
            "High": 0.05,
            "Medium": 0.0,
            "Low": -0.05
        }
        conversion += priority_bonus.get(priority, 0.0)

        # Cap between 0.01 and 0.95
        return max(0.01, min(0.95, conversion))