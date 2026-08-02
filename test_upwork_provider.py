import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scraper.discovery.providers.upwork_provider import UpworkDiscoveryProvider
from scraper.discovery.query import DiscoveryQuery, DiscoveryBatch, RawCandidate

def test_upwork_provider_basic():
    print("Testing UpworkDiscoveryProvider basic functionality...")
    provider = UpworkDiscoveryProvider()
    
    # Test with specific keywords as requested in requirements
    keywords = ["DevOps", "AI", "React"]
    query = DiscoveryQuery(
        industry="Software Development",
        location="USA",
        keywords=keywords,
        max_results=10
    )
    
    print(f"Running discovery with keywords: {keywords}")
    batch = provider.discover(query)
    
    print(f"Batch source: {batch.source}")
    print(f"Candidates found: {len(batch.candidates)}")
    
    # Since the implementation uses a placeholder for scraping, 
    # we verify the framework plumbing (batch return, source name, etc.)
    assert batch.source == "upwork"
    assert isinstance(batch.candidates, list)
    
    print("Basic framework test completed.")

if __name__ == "__main__":
    try:
        test_upwork_provider_basic()
        print("\nTEST PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
