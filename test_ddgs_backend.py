import sys
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scraper.services.search.factory import default_factory
from scraper.services.search.service import SearchService
from scraper.services.search.backends.ddgs_backend import DDGSBackend
from scraper.services.search.schema import SearchResult

def test_backend_registration():
    print("Testing DDGS backend registration...")
    assert "ddgs" in default_factory.list_available()
    assert default_factory.get("ddgs") is not None
    print("Registration test PASSED")

def test_canonical_schema():
    print("Testing DDGS canonical schema...")
    backend = DDGSBackend()
    
    # Mock the DDGS text method to return predictable data
    with patch("duckduckgo_search.DDGS.text") as mock_text:
        mock_text.return_value = [
            {"title": "Test Title", "href": "https://test.com", "body": "Test snippet"}
        ]
        
        results = backend.search("test query", limit=1)
        res = results[0]
        
        assert "title" in res and res["title"] == "Test Title"
        assert "url" in res and res["url"] == "https://test.com"
        assert "snippet" in res and res["snippet"] == "Test snippet"
        assert res["source_engine"] == "ddgs"
        assert res["query"] == "test query"
        assert "timestamp" in res
    print("Schema test PASSED")

def test_search_service_integration():
    print("Testing SearchService integration with DDGS...")
    service = SearchService() # Uses default_factory
    
    with patch("duckduckgo_search.DDGS.text") as mock_text:
        mock_text.return_value = [
            {"title": "Integrated Title", "href": "https://integrated.com", "body": "Integrated snippet"}
        ]
        
        results = service.search(query="integrated query", limit=1, preferred_backend="ddgs")
        
        assert len(results) == 1
        assert results[0]["title"] == "Integrated Title"
        assert results[0]["source_engine"] == "ddgs"
    print("Integration test PASSED")

def test_empty_results_handling():
    print("Testing empty results handling...")
    backend = DDGSBackend()
    
    with patch("duckduckgo_search.DDGS.text") as mock_text:
        mock_text.return_value = [] # No results found
        
        results = backend.search("nothing", limit=10)
        assert results == []
    print("Empty results test PASSED")

if __name__ == "__main__":
    try:
        test_backend_registration()
        test_canonical_schema()
        test_search_service_integration()
        test_empty_results_handling()
        print("\nALL DDGS TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
