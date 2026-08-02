import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scraper.services.search.interface import SearchBackend
from scraper.services.search.factory import BackendFactory
from scraper.services.search.service import SearchService
from scraper.services.search.schema import SearchResult

# --- Mock Backend for Testing ---
class MockBackend(SearchBackend):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        # Return dummy data matching canonical schema
        return [
            {
                "title": f"Result 1 for {query}",
                "url": "https://example.com/1",
                "snippet": "Snippet 1",
                "source_engine": self.name,
                "query": query,
                "timestamp": "2026-08-01T00:00:00Z"
            }
        ][:limit]

def test_backend_registration():
    print("Testing backend registration...")
    factory = BackendFactory()
    backend = MockBackend("test_engine")
    factory.register(backend)
    assert factory.get("test_engine") == backend
    assert "test_engine" in factory.list_available()
    print("Registration test PASSED")

def test_backend_lookup():
    print("Testing backend lookup...")
    factory = BackendFactory()
    assert factory.get("non_existent") is None
    print("Lookup test PASSED")

def test_search_service_execution():
    print("Testing SearchService execution...")
    factory = BackendFactory()
    backend = MockBackend("test_engine")
    factory.register(backend)
    
    service = SearchService(factory=factory)
    results = service.search(query="test query", limit=1, preferred_backend="test_engine")
    
    assert len(results) == 1
    assert results[0]["title"] == "Result 1 for test query"
    assert results[0]["source_engine"] == "test_engine"
    print("Execution test PASSED")

def test_empty_backend_behavior():
    print("Testing empty backend behavior...")
    factory = BackendFactory() # No backends registered
    service = SearchService(factory=factory)
    
    results = service.search(query="test query")
    assert results == []
    print("Empty backend test PASSED")

if __name__ == "__main__":
    try:
        test_backend_registration()
        test_backend_lookup()
        test_search_service_execution()
        test_empty_backend_behavior()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
