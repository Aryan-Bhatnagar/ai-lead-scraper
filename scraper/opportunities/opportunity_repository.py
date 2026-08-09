from typing import List, Optional, Dict, Any
from datetime import datetime
from .opportunity_models import Opportunity

class OpportunityRepository:
    """Repository for storing and retrieving opportunities."""

    def __init__(self, storage_path: str = "data/opportunities.json"):
        self.storage_path = storage_path
        self.opportunities: Dict[str, Opportunity] = {}
        self._load()

    def _load(self):
        """Load opportunities from storage."""
        try:
            import json
            import os
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for opp_data in data:
                        opp = Opportunity.from_dict(opp_data)
                        self.opportunities[opp.id] = opp
        except Exception:
            self.opportunities = {}

    def _save(self):
        """Save opportunities to storage."""
        import json
        import os
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump([opp.to_dict() for opp in self.opportunities.values()], f, indent=2)

    def add(self, opportunity: Opportunity) -> bool:
        """Add an opportunity. Returns True if added (not duplicate)."""
        if opportunity.id in self.opportunities:
            return False  # Already exists
        self.opportunities[opportunity.id] = opportunity
        self._save()
        return True

    def get(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get an opportunity by ID."""
        return self.opportunities.get(opportunity_id)

    def update(self, opportunity: Opportunity) -> bool:
        """Update an opportunity. Returns True if updated."""
        if opportunity.id not in self.opportunities:
            return False
        self.opportunities[opportunity.id] = opportunity
        self._save()
        return True

    def delete(self, opportunity_id: str) -> bool:
        """Delete an opportunity. Returns True if deleted."""
        if opportunity_id not in self.opportunities:
            return False
        del self.opportunities[opportunity_id]
        self._save()
        return True

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Opportunity]:
        """List opportunities with pagination."""
        opportunities = list(self.opportunities.values())
        # Sort by posted_time descending (newest first)
        opportunities.sort(key=lambda x: x.posted_time or datetime.min, reverse=True)
        return opportunities[offset:offset + limit]

    def search(self,
               query: Optional[str] = None,
               provider: Optional[str] = None,
               category: Optional[str] = None,
               skills: Optional[List[str]] = None,
               min_budget: Optional[float] = None,
               max_budget: Optional[float] = None,
               country: Optional[str] = None,
               limit: int = 100,
               offset: int = 0) -> List[Opportunity]:
        """Search opportunities with filters."""
        opportunities = list(self.opportunities.values())

        # Apply filters
        if query:
            query_lower = query.lower()
            opportunities = [
                opp for opp in opportunities
                if query_lower in opp.project_title.lower() or
                   query_lower in opp.description.lower()
            ]

        if provider:
            opportunities = [opp for opp in opportunities if opp.provider.lower() == provider.lower()]

        if category:
            opportunities = [opp for opp in opportunities if opp.category.lower() == category.lower()]

        if skills:
            opportunities = [
                opp for opp in opportunities
                if any(skill.lower() in [s.lower() for s in opp.skills] for skill in skills)
            ]

        if min_budget is not None:
            opportunities = [
                opp for opp in opportunities
                if opp.budget_max is not None and opp.budget_max >= min_budget
            ]

        if max_budget is not None:
            opportunities = [
                opp for opp in opportunities
                if opp.budget_min is not None and opp.budget_min <= max_budget
            ]

        if country:
            opportunities = [opp for opp in opportunities if opp.client_country.lower() == country.lower()]

        # Sort by posted_time descending (newest first)
        opportunities.sort(key=lambda x: x.posted_time or datetime.min, reverse=True)

        return opportunities[offset:offset + limit]

    def get_opportunities(self,
                          query: Optional[str] = None,
                          provider: Optional[str] = None,
                          category: Optional[str] = None,
                          skills: Optional[List[str]] = None,
                          min_budget: Optional[float] = None,
                          max_budget: Optional[float] = None,
                          country: Optional[str] = None,
                          limit: int = 100,
                          offset: int = 0) -> List[Opportunity]:
        """Get opportunities with filtering (alias for search)."""
        return self.search(
            query=query,
            provider=provider,
            category=category,
            skills=skills,
            min_budget=min_budget,
            max_budget=max_budget,
            country=country,
            limit=limit,
            offset=offset
        )

    def count(self,
              query: Optional[str] = None,
              provider: Optional[str] = None,
              category: Optional[str] = None,
              skills: Optional[List[str]] = None,
              min_budget: Optional[float] = None,
              max_budget: Optional[float] = None,
              country: Optional[str] = None) -> int:
        """Count opportunities matching filters."""
        return len(self.search(
            query=query,
            provider=provider,
            category=category,
            skills=skills,
            min_budget=min_budget,
            max_budget=max_budget,
            country=country,
            limit=10000  # Large limit to get all
        ))

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about opportunities."""
        opportunities = list(self.opportunities.values())

        if not opportunities:
            return {
                "total_opportunities": 0,
                "providers": {},
                "categories": {},
                "countries": {},
                "skills_frequency": {},
                "budget_ranges": {},
                "posting_trends": {}
            }

        # Providers
        providers = {}
        for opp in opportunities:
            providers[opp.provider] = providers.get(opp.provider, 0) + 1

        # Categories
        categories = {}
        for opp in opportunities:
            categories[opp.category] = categories.get(opp.category, 0) + 1

        # Countries
        countries = {}
        for opp in opportunities:
            countries[opp.client_country] = countries.get(opp.client_country, 0) + 1

        # Skills frequency
        skills_frequency = {}
        for opp in opportunities:
            for skill in opp.skills:
                skills_frequency[skill] = skills_frequency.get(skill, 0) + 1

        # Budget ranges (simplified)
        budget_ranges = {
            "0-1000": 0,
            "1000-5000": 0,
            "5000-10000": 0,
            "10000+": 0
        }
        for opp in opportunities:
            if opp.budget_max is not None:
                budget = opp.budget_max
                if budget <= 1000:
                    budget_ranges["0-1000"] += 1
                elif budget <= 5000:
                    budget_ranges["1000-5000"] += 1
                elif budget <= 10000:
                    budget_ranges["5000-10000"] += 1
                else:
                    budget_ranges["10000+"] += 1

        # Posting trends (by month)
        posting_trends = {}
        for opp in opportunities:
            if opp.posted_time:
                month_key = opp.posted_time.strftime("%Y-%m")
                posting_trends[month_key] = posting_trends.get(month_key, 0) + 1

        return {
            "total_opportunities": len(opportunities),
            "providers": providers,
            "categories": categories,
            "countries": countries,
            "skills_frequency": skills_frequency,
            "budget_ranges": budget_ranges,
            "posting_trends": posting_trends
        }