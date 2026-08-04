"""
Guru opportunity provider adapter.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..services.guru_scraper_service import GuruScraperService
from .base_provider import BaseOpportunityProvider
from .opportunity_models import Opportunity

class GuruProvider(BaseOpportunityProvider):
    """Guru opportunity provider."""

    def __init__(self, config: dict = None):
        super().__init__("guru", config)
        self.scraper_service = GuruScraperService()

    async def search_opportunities(self, query: str, limit: int = 100) -> List[Opportunity]:
        """Search for opportunities on Guru."""
        # Run the scraper in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        raw_jobs = await loop.run_in_executor(
            None,
            lambda: self.scraper_service.scrape_jobs(
                keywords=[query] if query else ["software development"],
                max_results=limit
            )
        )

        opportunities = []
        for i, job_data in enumerate(raw_jobs):
            try:
                opportunity = self._normalize_guru_job(job_data, f"guru-{i}")
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                # Log error but continue processing other jobs
                print(f"Error normalizing Guru job {i}: {e}")
                continue

        return opportunities

    async def get_opportunity_details(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get detailed information about a specific Guru opportunity."""
        # For now, we'll search again with a more specific query
        # In a real implementation, you might have a separate endpoint for details
        try:
            # Extract numeric ID if possible
            numeric_id = opportunity_id.split('-')[-1] if '-' in opportunity_id else opportunity_id

            # Search for jobs that might match this ID
            loop = asyncio.get_event_loop()
            raw_jobs = await loop.run_in_executor(
                None,
                lambda: self.scraper_service.scrape_jobs(
                    keywords=["software development"],
                    max_results=50  # Get more to increase chance of match
                )
            )

            # Look for a job with matching ID in metadata or URL
            for job_data in raw_jobs:
                job_id = str(job_data.get('id', ''))
                job_url = job_data.get('url', '')
                if numeric_id in job_id or numeric_id in job_url:
                    return self._normalize_guru_job(job_data, opportunity_id)

            # If no exact match, return the first job as fallback
            if raw_jobs:
                return self._normalize_guru_job(raw_jobs[0], opportunity_id)

        except Exception as e:
            print(f"Error fetching Guru opportunity details: {e}")

        return None

    def get_supported_categories(self) -> List[str]:
        """Return list of categories supported by Guru."""
        return [
            "Programming & Development", "Design & Creative", "Writing & Translation",
            "Administrative Support", "Business Services", "Sales & Marketing",
            "Engineering & Architecture", "Legal & Financial", "Customer Service",
            "IT & Networking", "Finance & Management", "Healthcare & Science",
            "Education & Training", "Hospitality & Travel", "Agriculture"
        ]

    def _normalize_guru_job(self, job_data: Dict[str, Any], opp_id: str) -> Optional[Opportunity]:
        """Normalize raw Guru job data into Opportunity model."""
        try:
            # Extract basic fields
            title = job_data.get('title', f'Guru Job {opp_id}')
            description = job_data.get('description', '')

            # Extract budget information
            budget_min = job_data.get('budget_min', 0.0)
            budget_max = job_data.get('budget_max', 0.0)
            # If only one budget value is provided, use it for both min and max
            if budget_max == 0 and budget_min > 0:
                budget_max = budget_min
            elif budget_min == 0 and budget_max > 0:
                budget_min = budget_max * 0.8  # Assume min is 80% of max

            # Extract other fields
            currency = job_data.get('currency', 'USD')
            category = job_data.get('category', 'Programming & Development')
            skills = job_data.get('skills', ['Software Development'])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(',')]

            experience_level = job_data.get('experience_level', 'Intermediate')
            proposal_count = job_data.get('proposal_count', 0)

            # Parse dates
            from dateutil import parser
            posted_time = parser.parse(job_data.get('posted_time')) if job_data.get('posted_time') else datetime.now()
            deadline = parser.parse(job_data.get('deadline')) if job_data.get('deadline') else None

            # Generate estimated value
            estimated_value = job_data.get('estimated_value', budget_max * 0.8 if budget_max > 0 else 0.0)

            # Build URL
            url = job_data.get('url', f"https://www.guru.com/job/{opp_id}")

            return Opportunity(
                id=opp_id,
                provider="guru",
                project_title=title,
                description=description,
                budget_min=float(budget_min),
                budget_max=float(budget_max),
                currency=currency,
                client_country=job_data.get('client_country', 'United States'),
                category=category,
                skills=skills,
                experience_level=experience_level,
                posted_time=posted_time,
                deadline=deadline,
                proposal_count=int(proposal_count),
                estimated_value=float(estimated_value),
                url=url,
                provider_metadata={
                    **job_data.get('provider_metadata', {}),
                    'budget_min': float(budget_min),
                    'budget_max': float(budget_max)
                },
                created_at=datetime.now()
            )
        except Exception as e:
            print(f"Error normalizing Guru job data: {e}")
            return None