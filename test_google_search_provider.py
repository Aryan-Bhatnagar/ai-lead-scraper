import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scraper.discovery.providers.google_search_provider import GoogleSearchDiscoveryProvider
from scraper.discovery.query import DiscoveryQuery, DiscoveryBatch, RawCandidate
from scraper.discovery.registry import default_registry
from scraper.services.search.service import SearchService

def test_provider_registration():
    print("Testing GoogleSearchDiscoveryProvider registration...")
    assert "google_search" in default_registry.list()
    assert default_registry.get("google_search") is not None
    print("Registration test PASSED")

def test_search_service_integration():
    print("Testing SearchService integration...")
    provider = GoogleSearchDiscoveryProvider()
    
    # Mock SearchService.search to return a canonical result
    mock_result = {
        "title": "Test Company",
        "url": "https://testcompany.com",
        "snippet": "Test snippet description",
        "source_engine": "ddgs",
        "query": "DevOps company USA",
        "timestamp": datetime.now(UTC).isoformat()
    }
    
    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search:
        mock_search.return_value = [mock_result]
        
        query = DiscoveryQuery(
            industry="DevOps",
            location="USA",
            keywords=[],
            max_results=1
        )
        
        batch = provider.discover(query)
        
        # Verify SearchService was called with correct backend
        mock_search.assert_called()
        args, kwargs = mock_search.call_args
        assert kwargs["preferred_backend"] == "ddgs"
        
        # Verify RawCandidate generation
        assert len(batch.candidates) == 1
        candidate = batch.candidates[0]
        assert isinstance(candidate, RawCandidate)
        assert candidate.payload == mock_result
        assert candidate.source == "google_search"
        
        # Verify DiscoveryBatch
        assert batch.source == "google_search"
        assert batch.meta.source == "google_search"
        
    print("Integration test PASSED")

def test_provenance_preservation():
    print("Testing provenance preservation...")
    provider = GoogleSearchDiscoveryProvider()
    
    mock_result = {
        "title": "Prov Company",
        "url": "https://prov.com",
        "snippet": "Prov snippet",
        "source_engine": "ddgs",
        "query": "AI company London",
        "timestamp": "2026-08-01T12:00:00Z"
    }
    
    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search:
        mock_search.return_value = [mock_result]
        
        query = DiscoveryQuery(industry="AI", location="London", keywords=[], max_results=1)
        batch = provider.discover(query)
        
        payload = batch.candidates[0].payload
        assert payload["source_engine"] == "ddgs"
        assert payload["query"] == "AI company London"
        assert payload["url"] == "https://prov.com"
        
    print("Provenance test PASSED")

def test_empty_search_handling():
    print("Testing empty search handling...")
    provider = GoogleSearchDiscoveryProvider()
    
    with patch("scraper.discovery.providers.google_search_provider.SearchService.search") as mock_search:
        mock_search.return_value = []
        
        query = DiscoveryQuery(industry="NonExistent", location="Mars", keywords=[], max_results=10)
        batch = provider.discover(query)
        
        assert len(batch.candidates) == 0
        assert batch.source == "google_search"
        
    print("Empty search test PASSED")

if __name__ == "__main__":
    try:
        test_provider_registration()
        test_search_service_integration()
        test_provenance_preservation()
        test_empty_search_handling()
        print("\nALL GOOGLE SEARCH PROVIDER TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
