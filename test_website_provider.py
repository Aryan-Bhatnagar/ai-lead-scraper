import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scraper.discovery.providers.website_provider import WebsiteDiscoveryProvider
from scraper.discovery.query import DiscoveryQuery, DiscoveryBatch, RawCandidate

def test_provider_basic():
    print("Testing WebsiteDiscoveryProvider basic functionality...")
    provider = WebsiteDiscoveryProvider()
    
    # We use a known site that is likely to be up and have content
    # In a real test environment, we'd use a mock or a dedicated test site.
    target_urls = ["https://www.google.com"] 
    query = DiscoveryQuery(
        industry="Search Engines",
        location="USA",
        filters={"target_websites": target_urls}
    )
    
    print(f"Running discovery for: {target_urls}")
    batch = provider.discover(query)
    
    print(f"Batch source: {batch.source}")
    print(f"Candidates found: {len(batch.candidates)}")
    
    if len(batch.candidates) > 0:
        candidate = batch.candidates[0]
        print(f"Candidate payload keys: {list(candidate.payload.keys())}")
        assert isinstance(candidate.payload, dict)
        assert candidate.source == provider.name
    
    print("Basic test completed.")

if __name__ == "__main__":
    try:
        test_provider_basic()
        print("\nTEST PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
