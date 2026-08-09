from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class Opportunity:
    """Model representing a freelance opportunity/project."""
    id: str
    provider: str
    project_title: str
    description: str
    budget_min: Optional[float]
    budget_max: Optional[float]
    currency: str
    client_country: str
    category: str
    skills: List[str]
    experience_level: str
    posted_time: datetime
    deadline: Optional[datetime]
    proposal_count: int
    estimated_value: Optional[float]
    url: str
    provider_metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert opportunity to dictionary for storage."""
        return {
            'id': self.id,
            'provider': self.provider,
            'project_title': self.project_title,
            'description': self.description,
            'budget_min': self.budget_min,
            'budget_max': self.budget_max,
            'currency': self.currency,
            'client_country': self.client_country,
            'category': self.category,
            'skills': self.skills,
            'experience_level': self.experience_level,
            'posted_time': self.posted_time.isoformat() if self.posted_time else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'proposal_count': self.proposal_count,
            'estimated_value': self.estimated_value,
            'url': self.url,
            'provider_metadata': self.provider_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Opportunity':
        """Create opportunity from dictionary."""
        # Handle datetime fields
        posted_time = None
        if data.get('posted_time'):
            posted_time = datetime.fromisoformat(data['posted_time'])

        deadline = None
        if data.get('deadline'):
            deadline = datetime.fromisoformat(data['deadline'])

        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        else:
            created_at = datetime.now()

        return cls(
            id=data['id'],
            provider=data['provider'],
            project_title=data['project_title'],
            description=data['description'],
            budget_min=data.get('budget_min'),
            budget_max=data.get('budget_max'),
            currency=data.get('currency', 'USD'),
            client_country=data.get('client_country', ''),
            category=data.get('category', ''),
            skills=data.get('skills', []),
            experience_level=data.get('experience_level', ''),
            posted_time=posted_time,
            deadline=deadline,
            proposal_count=data.get('proposal_count', 0),
            estimated_value=data.get('estimated_value'),
            url=data.get('url', ''),
            provider_metadata=data.get('provider_metadata', {}),
            created_at=created_at
        )