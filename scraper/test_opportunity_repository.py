import tempfile
import os
from datetime import datetime
from scraper.opportunities.opportunity_repository import OpportunityRepository
from scraper.opportunities.opportunity_models import Opportunity

def test_opportunity_repository_crud():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        repo = OpportunityRepository(storage_path=temp_path)

        # Test adding an opportunity
        opp = Opportunity(
            id="test1",
            provider="test",
            project_title="Test Project",
            description="A test project",
            budget_min=100.0,
            budget_max=200.0,
            currency="USD",
            client_country="US",
            category="Web Development",
            skills=["HTML", "CSS"],
            experience_level="Entry",
            posted_time=datetime.now(),
            deadline=None,
            proposal_count=5,
            estimated_value=150.0,
            url="http://example.com",
            provider_metadata={}
        )
        added = repo.add(opp)
        assert added == True

        # Test adding duplicate -> should return False
        added_again = repo.add(opp)
        assert added_again == False

        # Test getting
        retrieved = repo.get("test1")
        assert retrieved is not None
        assert retrieved.project_title == "Test Project"
        assert retrieved.id == "test1"

        # Test updating
        opp.project_title = "Updated Project"
        updated = repo.update(opp)
        assert updated == True
        retrieved_updated = repo.get("test1")
        assert retrieved_updated.project_title == "Updated Project"

        # Test deleting
        deleted = repo.delete("test1")
        assert deleted == True
        deleted_again = repo.delete("test1")
        assert deleted_again == False

        # Test listing
        opps = repo.list_all()
        assert len(opps) == 0

        # Test search
        repo.add(opp)
        results = repo.search(query="Test")
        assert len(results) == 1
        assert results[0].id == "test1"

        # Test search with no results
        results = repo.search(query="Nonexistent")
        assert len(results) == 0

        # Test count
        count = repo.count()
        assert count == 1

        # Test statistics
        stats = repo.get_statistics()
        assert stats["total_opportunities"] == 1
        assert stats["providers"]["test"] == 1

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)