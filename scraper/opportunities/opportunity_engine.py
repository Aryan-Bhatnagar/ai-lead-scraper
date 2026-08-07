import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from .query_generator import QueryGenerator, Query
from .provider_registry import provider_registry, BaseOpportunityProvider
from .opportunity_models import Opportunity
from .opportunity_repository import OpportunityRepository

logger = logging.getLogger(__name__)

class OpportunityEngine:
    """Engine for discovering and processing freelance opportunities."""

    def __init__(self, repository: Optional[OpportunityRepository] = None):
        self.repository = repository or OpportunityRepository()
        self.query_generator = QueryGenerator()
        self.provider_registry = provider_registry
        self._enabled_providers: Set[str] = set()

    def enable_provider(self, provider_name: str):
        """Enable a provider for opportunity discovery."""
        self._enabled_providers.add(provider_name.lower())
        logger.info(f"Enabled provider: {provider_name}")

    def disable_provider(self, provider_name: str):
        """Disable a provider for opportunity discovery."""
        self._enabled_providers.discard(provider_name.lower())
        logger.info(f"Disabled provider: {provider_name}")

    def get_enabled_providers(self) -> List[BaseOpportunityProvider]:
        """Get list of enabled provider instances."""
        # Debug prints
        print("Enabled providers:", self._enabled_providers)
        print("Registered providers:", self.provider_registry.get_provider_names())
        """Get list of enabled provider instances."""
        # Debug prints
        print("Enabled providers:", self._enabled_providers)
        print("Registered providers:", self.provider_registry.get_provider_names())
        """Get list of enabled provider instances."""
        providers = []
        for name in self._enabled_providers:
            provider = self.provider_registry.get_provider(name)
            if provider:
                providers.append(provider)
            else:
                logger.warning(f"Provider '{name}' is not registered")
        return providers

    async def discover_opportunities(self,
                                   categories: Optional[List[str]] = None,
                                   custom_keywords: Optional[List[str]] = None,
                                   max_queries_per_category: int = 3,
                                   max_opportunities_per_query: int = 50,
                                   queries: Optional[List[Query]] = None,
                                   providers: Optional[List[BaseOpportunityProvider]] = None,
                                   limit_per_provider: Optional[int] = None) -> List[Opportunity]:
        """
        Discover opportunities from enabled providers.

        Args:
            categories: List of categories to search for. If None, use all categories.
            custom_keywords: Additional keywords to include in queries.
            max_queries_per_category: Maximum number of queries to generate per category.
            max_opportunities_per_query: Maximum opportunities to fetch per query per provider.
            queries: Pre-generated list of Query objects. If provided, categories/custom_keywords/max_queries_per_category are ignored.
            providers: List of provider instances to use. If None, use all enabled providers.
            limit_per_provider: Override max_opportunities_per_query for this call.

        Returns:
            List of discovered opportunities.
        """
        # Use provided queries or generate them
        if queries is not None:
            query_list = queries
        else:
            query_list = self.query_generator.generate_queries(
                categories=categories,
                custom_keywords=custom_keywords,
                max_queries_per_category=max_queries_per_category
            )
        logger.info(f"Generated {len(query_list)} search queries")
        print(f"[ENGINE] Generated {len(query_list)} search queries: {[q.to_search_string() for q in query_list[:3]]}")

        # Determine providers to use
        if providers is not None:
            provider_list = providers
        else:
            provider_list = self.get_enabled_providers()
        if not provider_list:
            logger.warning("No providers enabled for opportunity discovery")
            return []

        logger.info(f"Discovering opportunities using {len(provider_list)} providers: {[p.name for p in provider_list]}")
        print(f"[ENGINE] Providers: {[p.name for p in provider_list]}")

        # Determine limit per provider
        limit = limit_per_provider if limit_per_provider is not None else max_opportunities_per_query

        # Discover opportunities from each provider
        all_opportunities = []
        for provider in provider_list:
            try:
                provider_opportunities = await self._discover_from_provider(
                    provider, query_list, limit
                )
                print(f"[ENGINE] Provider {provider.name} returned {len(provider_opportunities)} raw opportunities")
                all_opportunities.extend(provider_opportunities)
                logger.info(f"Provider {provider.name} yielded {len(provider_opportunities)} opportunities")
            except Exception as e:
                logger.error(f"Error discovering opportunities from provider {provider.name}: {e}")
                print(f"[ENGINE] Error from provider {provider.name}: {e}")

        # Deduplicate opportunities
        unique_opportunities = self._deduplicate_opportunities(all_opportunities)
        print(f"[ENGINE] After deduplication: {len(unique_opportunities)} unique opportunities (from {len(all_opportunities)} raw)")
        logger.info(f"After deduplication: {len(unique_opportunities)} unique opportunities")

        # Persist opportunities
        saved_count = 0
        for opp in unique_opportunities:
            if self.repository.add(opp):
                saved_count += 1

        print(f"[ENGINE] Saved {saved_count} new opportunities to repository")
        logger.info(f"Saved {saved_count} new opportunities to repository")
        return unique_opportunities

    async def _discover_from_provider(self,
                                    provider: BaseOpportunityProvider,
                                    queries: List[Query],
                                    max_opportunities_per_query: int) -> List[Opportunity]:
        """Discover opportunities from a single provider."""
        opportunities = []
        for query in queries:
            try:
                # Search for opportunities using the query
                results = await provider.search_opportunities(
                    query=query.to_search_string(),
                    limit=max_opportunities_per_query
                )
                opportunities.extend(results)
            except Exception as e:
                logger.error(f"Error searching provider {provider.name} with query '{query.to_search_string()}': {e}")
        return opportunities

    def _deduplicate_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
        """Remove duplicate opportunities based on ID and URL."""
        seen_ids: Set[str] = set()
        seen_urls: Set[str] = set()
        unique_opportunities = []

        for opp in opportunities:
            # Check by ID first
            if opp.id in seen_ids:
                continue
            # Check by URL if ID is not available or empty
            if opp.url and opp.url in seen_urls:
                continue

            seen_ids.add(opp.id)
            if opp.url:
                seen_urls.add(opp.url)
            unique_opportunities.append(opp)

        return unique_opportunities

    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get an opportunity by ID."""
        return self.repository.get_opportunity(opportunity_id)

    def get_opportunities(self, **kwargs) -> List[Opportunity]:
        """Get opportunities with optional filtering."""
        return self.repository.get_opportunities(**kwargs)

    def search_opportunities(self, query: str, limit: int = 50) -> List[Opportunity]:
        """Search opportunities by text query."""
        return self.repository.search_opportunities(query, limit)

    def get_opportunity_statistics(self) -> Dict[str, Any]:
        """Get statistics about opportunities."""
        return self.repository.get_statistics()

    async def get_opportunity_details(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get detailed information about a specific opportunity."""
        # First try to get from repository
        opportunity = self.repository.get_opportunity(opportunity_id)
        if opportunity:
            return opportunity

        # If not in repository, try to fetch from providers
        for provider in self.get_enabled_providers():
            try:
                opportunity = await provider.get_opportunity_details(opportunity_id)
                if opportunity:
                    # Save to repository for future use
                    self.repository.add_opportunity(opportunity)
                    return opportunity
            except Exception as e:
                logger.error(f"Error fetching opportunity {opportunity_id} from provider {provider.name}: {e}")

        return None

    def generate_recommendations(self, opportunities: List[Opportunity]) -> List[Dict[str, Any]]:
        """
        Generate recommendations for opportunities.

        Returns a list of dictionaries with recommendation details.
        """
        recommendations = []
        for opp in opportunities:
            # Simple recommendation logic - can be enhanced
            priority = self._calculate_priority(opp)
            win_probability = self._estimate_win_probability(opp)
            suggested_action = self._suggest_action(opp, priority, win_probability)
            estimated_quality = self._estimate_proposal_quality(opp)

            recommendations.append({
                "opportunity_id": opp.id,
                "priority": priority,  # 1-5 scale
                "estimated_win_probability": win_probability,  # 0-1 scale
                "suggested_action": suggested_action,
                "estimated_proposal_quality": estimated_quality,  # 1-5 scale
                "reasoning": self._generate_reasoning(opp, priority, win_probability, suggested_action, estimated_quality)
            })

        # Sort by priority and win probability
        recommendations.sort(key=lambda x: (x['priority'], x['estimated_win_probability']), reverse=True)
        return recommendations

    def _calculate_priority(self, opportunity: Opportunity) -> int:
        """Calculate priority score (1-5) for an opportunity."""
        score = 1

        # Budget factor
        if opportunity.budget_max is not None:
            if opportunity.budget_max >= 5000:
                score += 2
            elif opportunity.budget_max >= 1000:
                score += 1

        # Experience level factor (prefer intermediate/expert)
        if opportunity.experience_level.lower() in ['expert', 'advanced']:
            score += 1
        elif opportunity.experience_level.lower() == 'intermediate':
            score += 0.5

        # Proposal count factor (fewer proposals = higher priority)
        if opportunity.proposal_count < 5:
            score += 1
        elif opportunity.proposal_count < 15:
            score += 0.5

        # Recency factor (newer = higher priority)
        if opportunity.posted_time:
            hours_old = (datetime.now() - opportunity.posted_time).total_seconds() / 3600
            if hours_old < 24:
                score += 1
            elif hours_old < 168:  # less than a week
                score += 0.5

        return min(5, max(1, round(score)))

    def _estimate_win_probability(self, opportunity: Opportunity) -> float:
        """Estimate win probability (0-1) for an opportunity."""
        # Base probability
        probability = 0.5

        # Adjust based on proposal count (fewer proposals = higher chance)
        if opportunity.proposal_count == 0:
            probability += 0.3
        elif opportunity.proposal_count < 5:
            probability += 0.2
        elif opportunity.proposal_count < 15:
            probability += 0.1
        elif opportunity.proposal_count > 50:
            probability -= 0.2

        # Adjust based on budget (higher budget = more competition, but also better pay)
        if opportunity.budget_max is not None:
            if opportunity.budget_max > 10000:
                probability -= 0.1  # High competition
            elif opportunity.budget_max < 500:
                probability -= 0.1  # Low quality clients

        # Adjust based on experience level match (simplified)
        # In a real system, this would match against freelancer skills

        return max(0.1, min(0.9, probability))

    def _suggest_action(self, opportunity: Opportunity, priority: int, win_probability: float) -> str:
        """Suggest an action for the opportunity."""
        if priority >= 4 and win_probability > 0.6:
            return "High priority - Submit proposal soon"
        elif priority >= 3:
            return "Medium priority - Consider submitting proposal"
        elif opportunity.proposal_count < 3:
            return "Low competition - Worth considering"
        else:
            return "Low priority - Skip or low effort proposal"

    def _estimate_proposal_quality(self, opportunity: Opportunity) -> int:
        """Estimate the quality of proposal we could submit (1-5)."""
        # This would be based on skill match in a real system
        # For now, return a moderate score
        return 3

    def _generate_reasoning(self, opportunity: Opportunity, priority: int, win_probability: float,
                          suggested_action: str, estimated_quality: int) -> str:
        """Generate human-readable reasoning for the recommendation."""
        reasons = []

        if opportunity.budget_max and opportunity.budget_max >= 5000:
            reasons.append(f"High budget (${opportunity.budget_max:,.0f})")
        elif opportunity.budget_max and opportunity.budget_max >= 1000:
            reasons.append(f"Decent budget (${opportunity.budget_max:,.0f})")

        if opportunity.proposal_count < 5:
            reasons.append(f"Low competition ({opportunity.proposal_count} proposals)")
        elif opportunity.proposal_count < 15:
            reasons.append(f"Moderate competition ({opportunity.proposal_count} proposals)")
        else:
            reasons.append(f"High competition ({opportunity.proposal_count} proposals)")

        if opportunity.experience_level:
            reasons.append(f"Experience level: {opportunity.experience_level}")

        if opportunity.posted_time:
            hours_old = (datetime.now() - opportunity.posted_time).total_seconds() / 3600
            if hours_old < 24:
                reasons.append("Posted recently (<24h)")
            elif hours_old < 168:
                reasons.append("Posted within the week")

        reasons.append(f"Priority: {priority}/5")
        reasons.append(f"Win probability: {win_probability:.0%}")
        reasons.append(f"Suggested action: {suggested_action}")

        return "; ".join(reasons)