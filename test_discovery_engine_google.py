import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scraper.discovery.engine import LeadDiscoveryEngine, DiscoveryRunSummary
from scraper.discovery.query import DiscoveryQuery
from scraper.discovery.registry import default_registry
from scraper.discovery.providers.google_search_provider import GoogleSearchDiscoveryProvider
from scraper.services.search.service import SearchService

def test_engine_google_flow():
    print("Testing End-to-End Discovery Engine flow with Google Search...")
    
    # 1. Verify Registration
    # The registry should already have it from the module-level registration
    assert "google_search" in default_registry.list()
    provider = default_registry.get("google_search")
    assert isinstance(provider, GoogleSearchDiscoveryProvider)
    print("Registration check PASSED")

    # 2. Setup Mock Search Service
    # We mock SearchService.search to avoid actual network calls and 403s
    mock_results = [
        {
            "title": "Lead A",
            "url": "https://lead-a.com",
            "snippet": "Snippet A",
            "source_engine": "ddgs",
            "query": "DevOps USA",
            "timestamp": datetime.now(UTC).isoformat()
        },
        {
            "title": "Lead B",
            "url": "https://lead-b.com",
            "snippet": "Snippet B",
            "source_engine": "ddgs",
            "query": "DevOps USA",
            "timestamp": datetime.now(UTC).isoformat()
        }
    ]

    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search:
        mock_search.return_value = mock_results
        
        # 3. Execute Engine
        engine = LeadDiscoveryEngine(registry=default_registry)
        query = DiscoveryQuery(
            industry="DevOps",
            location="USA",
            keywords=[],
            max_results=10
        )
        
        # Run engine restricted to just the google_search provider
        summary = engine.run(query, sources=["google_search"])
        
        # 4. Verify Summary
        assert isinstance(summary, DiscoveryRunSummary)
        assert "google_search" in summary.per_source
        
        source_summary = summary.per_source["google_search"]
        assert source_summary.found == 2
        assert summary.total_found == 2
        
        print("Engine execution check PASSED")
        print(f"Total leads discovered: {summary.total_found}")

def test_provider_isolation():
    print("Testing provider isolation...")
    # Ensure that running google_search doesn't accidentally trigger others 
    # if we specify the source explicitly.
    
    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search:
        mock_search.return_value = []
        
        engine = LeadDiscoveryEngine(registry=default_registry)
        query = DiscoveryQuery(industry="AI", location="London", keywords=[], max_results=5)
        
        # Run only google_search
        summary = engine.run(query, sources=["google_search"])
        
        # Check that only google_search is in the summary
        assert len(summary.per_source) == 1
        assert "google_search" in summary.per_source
        print("Isolation check PASSED")

if __name__ == "__main__":
    try:
        test_engine_google_flow()
        test_provider_isolation()
        print("\nALL DISCOVERY ENGINE INTEGRATION TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
