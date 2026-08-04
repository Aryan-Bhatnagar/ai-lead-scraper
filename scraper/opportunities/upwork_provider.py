"""
Upwork opportunity provider adapter.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..services.upwork_scraper_service import UpworkScraperService
from .base_provider import BaseOpportunityProvider
from .opportunity_models import Opportunity

class UpworkProvider(BaseOpportunityProvider):
    """Upwork opportunity provider."""

    def __init__(self, config: dict = None):
        super().__init__("upwork", config)
        self.scraper_service = UpworkScraperService()

    async def search_opportunities(self, query: str, limit: int = 100) -> List[Opportunity]:
        """Search for opportunities on Upwork."""
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
                opportunity = self._normalize_upwork_job(job_data, f"upwork-{i}")
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                # Log error but continue processing other jobs
                print(f"Error normalizing Upwork job {i}: {e}")
                continue

        return opportunities

    async def get_opportunity_details(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get detailed information about a specific Upwork opportunity."""
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
                    return self._normalize_upwork_job(job_data, opportunity_id)

            # If no exact match, return the first job as fallback
            if raw_jobs:
                return self._normalize_upwork_job(raw_jobs[0], opportunity_id)

        except Exception as e:
            print(f"Error fetching Upwork opportunity details: {e}")

        return None

    def get_supported_categories(self) -> List[str]:
        """Return list of categories supported by Upwork."""
        return [
            "Web Development", "Mobile Development", "UI/UX", "Data Science & Analytics",
            "AI & Machine Learning", "DevOps & Sysadmin", "Cloud Computing", "Network & Infrastructure",
            "Security", "Database Administration", "QA & Testing", "Technical Support",
            "WordPress", "Shopify", "Web Design", "Graphic Design", "Video & Animation",
            "Writing & Translation", "Marketing", "Sales & Marketing", "Admin Support",
            "Customer Service", "Accounting & Consulting", "Legal", "Writing", "Translation",
            "Administrative Support", "Data Entry", "Accounting & Finance", "Engineering & Architecture",
            "Talent & Modeling", "Business", "Finance & Accounting", "Legal"
        ]

    def _normalize_upwork_job(self, job_data: dict, opp_id: str) -> Optional[Opportunity]:
        """Normalize raw Upwork job data into Opportunity model."""
        try:
            # Extract basic fields with fallbacks
            title = job_data.get('title', job_data.get('job_title', f'Opportunity {opp_id}'))
            description = job_data.get('description', job_data.get('description_html', ''))

            # Clean up description if it's HTML
            if description and '<' in description and '>' in description:
                # Simple HTML tag removal - in production you'd use BeautifulSoup
                import re
                description = re.sub('<[^<]+?>', '', description)
                description = description.replace('&nbsp;', ' ').strip()

            # Budget extraction
            budget_min = None
            budget_max = None
            budget_text = job_data.get('budget', job_data.get('budget_range', ''))
            if budget_text:
                # Try to extract numbers from budget string like "$500-$1,000" or "$20/hr"
                import re
                numbers = re.findall(r'\$?(\d+(?:,\d{3})*(?:\.\d+)?)', budget_text.replace(',', ''))
                if len(numbers) >= 2:
                    budget_min = float(numbers[0])
                    budget_max = float(numbers[1])
                elif len(numbers) == 1:
                    budget_min = float(numbers[0])
                    budget_max = float(numbers[0]) * 1.5  # Estimate max as 1.5x min

            # If no budget found, set reasonable defaults
            if budget_min is None:
                budget_min = 500.0
            if budget_max is None:
                budget_max = budget_min * 2 if budget_min else 1000.0

            # Extract other fields
            category = job_data.get('category', job_data.get('category_name', 'Web Development'))
            skills_str = job_data.get('skills', job_data.get('required_skills', ''))
            skills = [s.strip() for s in skills_str.split(',') if s.strip()] if isinstance(skills_str, str) else []
            if not skills:
                skills = ["Web Development", "Programming"]  # Default skills

            experience_level = job_data.get('experience_level', job_data.get('experience_level_required', 'Intermediate'))
            client_country = job_data.get('client_country', job_data.get('client_location', 'United States'))

            # Dates
            posted_time_str = job_data.get('posted_time', job_data.get('publish_time', ''))
            try:
                from dateutil import parser
                posted_time = parser.parse(posted_time_str) if posted_time_str else datetime.now()
            except:
                posted_time = datetime.now()

            deadline_str = job_data.get('deadline', job_data.get('end_time', ''))
            try:
                from dateutil import parser
                deadline = parser.parse(deadline_str) if deadline_str else None
            except:
                deadline = None

            # Proposal count
            proposal_count = job_data.get('proposal_count', job_data.get('applicants', 0))
            try:
                proposal_count = int(proposal_count) if proposal_count else 0
            except:
                proposal_count = 5  # Default

            # Estimated value
            estimated_value = job_data.get('estimated_value', job_data.get('budget_max', budget_max))
            try:
                estimated_value = float(estimated_value) if estimated_value else budget_max
            except:
                estimated_value = budget_max

            # URL
            url = job_data.get('url', job_data.get('job_url', f'https://www.upwork.com/jobs/{opp_id}'))

            return Opportunity(
                id=opp_id,
                provider="upwork",
                project_title=title,
                description=description,
                budget_min=float(budget_min),
                budget_max=float(budget_max),
                currency="USD",
                client_country=str(client_country),
                category=str(category),
                skills=skills,
                experience_level=str(experience_level),
                posted_time=posted_time,
                deadline=deadline,
                proposal_count=proposal_count,
                estimated_value=float(estimated_value),
                url=str(url),
                provider_metadata={
                    "job_type": job_data.get('job_type', job_data.get('contract_type', 'unknown')),
                    "experience_level": experience_level,
                    "duration": job_data.get('duration', job_data.get('contract_length', 'unknown')),
                    "payment_verified": job_data.get('payment_verified', job_data.get('client_payment_verified', False))
                },
                created_at=datetime.now()
            )
        except Exception as e:
            print(f"Error normalizing Upwork job data: {e}")
            print(f"Job data: {job_data}")
            return None