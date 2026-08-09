"""
Opportunity provider package initialization.
"""
from .base_provider import BaseOpportunityProvider
from .provider_registry import provider_registry
from .upwork_provider import UpworkProvider
from .freelancer_provider import FreelancerProvider
from .guru_provider import GuruProvider
from .peopleperhour_provider import PeoplePerHourProvider

# Register providers
provider_registry.register(UpworkProvider())
provider_registry.register(FreelancerProvider())
provider_registry.register(GuruProvider())
provider_registry.register(PeoplePerHourProvider())

__all__ = [
    "BaseOpportunityProvider",
    "provider_registry",
    "UpworkProvider",
    "FreelancerProvider",
    "GuruProvider",
    "PeoplePerHourProvider"
]