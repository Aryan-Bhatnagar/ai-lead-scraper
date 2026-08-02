import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import registry and providers FIRST to trigger registration
from scraper.discovery.registry import default_registry
from scraper.discovery.providers.google_search_provider import GoogleSearchDiscoveryProvider
from scraper.discovery.providers.website_provider import WebsiteDiscoveryProvider
from scraper.discovery.normalizers.registry import default_registry as normalizer_registry
from scraper.discovery.normalizers.google_search import GoogleSearchNormalizer
from scraper.discovery.normalizers.website import WebsiteNormalizer
from scraper.discovery.engine import LeadDiscoveryEngine
from scraper.discovery.query import DiscoveryQuery
from scraper.discovery.model import UnifiedLead

def test_full_discovery_pipeline():
    print("Testing Full Discovery Pipeline: Google Search -> Website Discovery...")
    
    # 1. Ensure Registration
    default_registry.register(GoogleSearchDiscoveryProvider())
    default_registry.register(WebsiteDiscoveryProvider())
    normalizer_registry.register("google_search", GoogleSearchNormalizer())
    normalizer_registry.register("website_discovery", WebsiteNormalizer())
    
    # 2. Mock Data
    google_mock_results = [
        {
            "title": "TechCorp Solutions",
            "url": "https://techcorp.example.com",
            "snippet": "Leading AI agency in New York",
            "source_engine": "ddgs",
            "query": "AI agency NYC",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]
    
    website_mock_results = {
        "company_name": "TechCorp Solutions",
        "company_description": "Enriched description from deep scrape",
        "website": "https://techcorp.example.com",
        "industry": "AI",
        "email": "contact@techcorp.example.com",
        "phone": "+123456789",
        "city": "New York",
        "country": "USA",
        "_provenance": {
            "email": {"value": "contact@techcorp.example.com", "source_page": "contact", "source_type": "mailto"},
            "phone": {"value": "+123456789", "source_page": "contact", "source_type": "tel"},
        },
        "_source_pages": ["https://techcorp.example.com", "https://techcorp.example.com/contact"]
    }

    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search, \
         patch("scraper.discovery.providers.website_provider.scrape_site") as mock_scrape:
        
        mock_search.return_value = google_mock_results
        mock_scrape.return_value = website_mock_results
        
        # Execute Engine
        engine = LeadDiscoveryEngine()
        query = DiscoveryQuery(
            industry="AI",
            location="NYC",
            keywords=[],
            max_results=1
        )
        
        # Run engine restricted to just the google_search provider
        summary = engine.run(query, sources=["google_search"])
        
        # 3. Verify UnifiedLead output
        assert len(summary.leads) == 1
        lead = summary.leads[0]
        
        # Check that the lead started as a Google search result
        assert lead.company_name == "TechCorp Solutions"
        assert lead.website == "https://techcorp.example.com"
        
        # Check that it was enriched by the WebsiteDiscoveryProvider
        # The engine merge logic: lead.description = enriched_lead.description or lead.description
        assert lead.description == "Enriched description from deep scrape"
        
        print("Pipeline verification PASSED")
        print(f"Final Lead: {lead.company_name} | {lead.website} | {lead.description}")

def test_missing_website_handling():
    print("Testing graceful handling of missing websites...")
    
    google_mock_results = [
        {
            "title": "Ghost Company",
            "url": "", # Missing website
            "snippet": "No site here",
            "source_engine": "ddgs",
            "query": "ghost company",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]

    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search:
        mock_search.return_value = google_mock_results
        
        engine = LeadDiscoveryEngine()
        query = DiscoveryQuery(industry="Ghost", location="Void", keywords=[], max_results=1)
        
        summary = engine.run(query, sources=["google_search"])
        
        assert len(summary.leads) == 1
        assert summary.leads[0].website == ""
        print("Missing website handling PASSED")

if __name__ == "__main__":
    try:
        test_full_discovery_pipeline()
        test_missing_website_handling()
        print("\nALL WEBSITE DISCOVERY PIPELINE TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
