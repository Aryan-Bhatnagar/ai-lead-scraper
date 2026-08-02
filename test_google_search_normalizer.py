import sys
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scraper.discovery.normalizers.google_search import GoogleSearchNormalizer
from scraper.discovery.normalizers.registry import default_registry
from scraper.discovery.query import RawCandidate, DiscoveryQuery
from scraper.discovery.model import UnifiedLead

def test_normalization_logic():
    print("Testing GoogleSearchNormalizer logic...")
    normalizer = GoogleSearchNormalizer()
    
    payload = {
        "title": "Example DevOps Agency",
        "url": "https://example-devops.com",
        "snippet": "Leading DevOps consultancy in NYC",
        "source_engine": "ddgs",
        "query": "DevOps company NYC",
        "timestamp": "2026-08-01T10:00:00"
    }
    
    candidate = RawCandidate(payload=payload, source="google_search")
    query = DiscoveryQuery(industry="DevOps", location="NYC", keywords=[])
    
    lead = normalizer.normalize(candidate, query)
    
    assert isinstance(lead, UnifiedLead)
    assert lead.company_name == "Example DevOps Agency"
    assert lead.website == "https://example-devops.com"
    assert lead.description == "Leading DevOps consultancy in NYC"
    assert lead.location.country == "NYC" # Based on query.location in implementation
    assert lead.provenance.source == "google_search"
    assert lead.provenance.source_url == "https://example-devops.com"
    print("Normalization logic test PASSED")

def test_registry_lookup():
    print("Testing NormalizerRegistry lookup...")
    normalizer = default_registry.get("google_search")
    assert isinstance(normalizer, GoogleSearchNormalizer)
    print("Registry lookup test PASSED")

def test_engine_integration():
    print("Testing LeadDiscoveryEngine integration...")
    from scraper.discovery.engine import LeadDiscoveryEngine
    from scraper.discovery.registry import default_registry as provider_registry
    from scraper.discovery.providers.google_search_provider import GoogleSearchDiscoveryProvider
    from scraper.services.search.service import SearchService

    # Setup: Register provider if not present
    provider_registry.register(GoogleSearchDiscoveryProvider())
    
    # Mock SearchService to return a canonical result
    mock_result = {
        "title": "Engine Lead",
        "url": "https://engine-lead.com",
        "snippet": "Engine snippet",
        "source_engine": "ddgs",
        "query": "DevOps USA",
        "timestamp": datetime.now(UTC).isoformat()
    }

    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search:
        mock_search.return_value = [mock_result]
        
        engine = LeadDiscoveryEngine()
        query = DiscoveryQuery(industry="DevOps", location="USA", keywords=[], max_results=1)
        
        summary = engine.run(query, sources=["google_search"])
        
        assert len(summary.leads) == 1
        lead = summary.leads[0]
        assert isinstance(lead, UnifiedLead)
        assert lead.company_name == "Engine Lead"
        assert lead.website == "https://engine-lead.com"
        assert summary.total_found == 1
        print("Engine integration test PASSED")

if __name__ == "__main__":
    # Since we are using patch in the engine test, we need to import it here
    from unittest.mock import patch
    
    try:
        test_normalization_logic()
        test_registry_lookup()
        test_engine_integration()
        print("\nALL GOOGLE SEARCH NORMALIZER TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
