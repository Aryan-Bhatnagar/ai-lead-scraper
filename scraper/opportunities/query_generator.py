from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path

class Query:
    """Represents a search query for opportunity discovery."""

    def __init__(self, keywords: List[str], category: str = "",
                 skills: Optional[List[str]] = None,
                 experience_level: Optional[str] = None,
                 min_budget: Optional[float] = None,
                 max_budget: Optional[float] = None):
        self.keywords = keywords
        self.category = category
        self.skills = skills or []
        self.experience_level = experience_level
        self.min_budget = min_budget
        self.max_budget = max_budget

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keywords": self.keywords,
            "category": self.category,
            "skills": self.skills,
            "experience_level": self.experience_level,
            "min_budget": self.min_budget,
            "max_budget": self.max_budget
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Query':
        return cls(
            keywords=data.get("keywords", []),
            category=data.get("category", ""),
            skills=data.get("skills", []),
            experience_level=data.get("experience_level"),
            min_budget=data.get("min_budget"),
            max_budget=data.get("max_budget")
        )

    def to_search_string(self) -> str:
        """Convert query to a search string for providers."""
        parts = []
        if self.keywords:
            parts.extend(self.keywords)
        if self.skills:
            parts.extend(self.skills)
        if self.category:
            parts.append(self.category)
        if self.experience_level:
            parts.append(self.experience_level)
        return " ".join(parts)


class QueryGenerator:
    """Generates search queries for opportunity discovery based on predefined categories."""

    # Predefined categories and their associated keywords
    CATEGORIES = {
        "DevOps": ["DevOps", "CI/CD", "Docker", "Kubernetes", "Jenkins", "GitLab CI", "AWS", "Azure", "GCP", "Terraform", "Ansible"],
        "AWS": ["AWS", "Amazon Web Services", "EC2", "S3", "Lambda", "CloudFormation", "ECS", "EKS", "RDS"],
        "Docker": ["Docker", "Containerization", "Docker Compose", "Kubernetes", "Microservices"],
        "Terraform": ["Terraform", "Infrastructure as Code", "IaC", "AWS", "Azure", "GCP"],
        "Kubernetes": ["Kubernetes", "K8s", "Container Orchestration", "Docker", "Helm", "Istio"],
        "CI/CD": ["CI/CD", "Continuous Integration", "Continuous Deployment", "Jenkins", "GitLab CI", "GitHub Actions", "CircleCI"],
        "Linux": ["Linux", "System Administration", "Bash", "Shell Scripting", "DevOps", "AWS", "Linux Server Administration"],
        "Python": ["Python", "Django", "Flask", "FastAPI", "Pandas", "NumPy", "Machine Learning", "Data Science", "API"],
        "Web Development": ["Web Development", "Full Stack", "Frontend", "Backend", "HTML", "CSS", "JavaScript", "React", "Vue", "Angular"],
        "React": ["React", "ReactJS", "React Native", "Redux", "Hooks", "Frontend", "JavaScript", "JSX"],
        "Next.js": ["Next.js", "React", "SSR", "Server-Side Rendering", "NextJS", "Frontend", "Web Development"],
        "Node.js": ["Node.js", "NodeJS", "Express", "MongoDB", "REST API", "GraphQL", "Backend", "JavaScript"],
        "Angular": ["Angular", "AngularJS", "TypeScript", "Frontend", "SPA", "RxJS", "NgRx"],
        "Vue": ["Vue.js", "VueJS", "Vue 3", "Frontend", "Vuex", "Vue Router", "JavaScript"],
        "Flutter": ["Flutter", "Dart", "Mobile App Development", "Cross-platform", "iOS", "Android"],
        "Mobile Development": ["Mobile Development", "iOS", "Android", "Swift", "Kotlin", "React Native", "Flutter", "Mobile App"],
        "UI/UX": ["UI/UX Design", "User Interface", "User Experience", "Figma", "Adobe XD", "Sketch", "Wireframing", "Prototyping"],
        "Figma": ["Figma", "UI Design", "UX Design", "Prototyping", "Wireframing", "Design System", "Collaborative Design"],
        "AI": ["Artificial Intelligence", "Machine Learning", "Deep Learning", "Neural Networks", "NLP", "Computer Vision", "TensorFlow", "PyTorch"],
        "LLM": ["Large Language Models", "LLM", "GPT", "LLama", "Claude", "BERT", "Transformers", "NLP", "Generative AI"],
        "OpenAI": ["OpenAI", "GPT", "ChatGPT", "DALL-E", "API", "LLM", "Prompt Engineering"],
        "Claude": ["Claude", "Anthropic", "LLM", "Claude 2", "Claude 3", "AI Assistant", "Conversational AI"],
        "Data Engineering": ["Data Engineering", "ETL", "Data Pipeline", "Data Warehouse", "SQL", "NoSQL", "Spark", "Kafka", "Big Data"],
        "Cloud": ["Cloud Computing", "AWS", "Azure", "Google Cloud", "Cloud Architecture", "DevOps", "Serverless", "Microservices"],
        "Azure": ["Microsoft Azure", "Azure Cloud", "Azure Functions", "Azure App Service", "Azure SQL", "DevOps", "Cloud Computing"],
        "GCP": ["Google Cloud Platform", "GCP", "Google Cloud", "Compute Engine", "Cloud Storage", "BigQuery", "Kubernetes Engine"],
        "Security": ["Cybersecurity", "Information Security", "Network Security", "Application Security", "Penetration Testing", "Ethical Hacking", "AWS Security"],
        "Networking": ["Networking", "Network Administration", "TCP/IP", "DNS", "DHCP", "VPN", "Firewall", "Routing", "Switching"],
        "WordPress": ["WordPress", "WP", "PHP", "Website Development", "Blogging", "WooCommerce", "Theme Development", "Plugin Development"],
        "Shopify": ["Shopify", "E-commerce", "Liquid", "Shopify Theme Development", "Shopify App Development", "Online Store"],
        "SEO": ["Search Engine Optimization", "SEO", "Google Analytics", "Keyword Research", "On-Page SEO", "Link Building", "Content Marketing"],
        "Marketing": ["Digital Marketing", "Marketing Strategy", "Social Media Marketing", "Content Marketing", "Email Marketing", "PPC", "Google Ads"],
        "Automation": ["Automation", "Robotic Process Automation", "RPA", "Workflow Automation", "Business Process Automation", "Zapier", "Integromat"]
    }

    def __init__(self):
        """Initialize the query generator with predefined categories."""
        pass

    def generate_queries(self, categories: Optional[List[str]] = None,
                        custom_keywords: Optional[List[str]] = None,
                        max_queries_per_category: int = 3) -> List[Query]:
        """
        Generate search queries based on categories and/or custom keywords.

        Args:
            categories: List of category names to generate queries for. If None, use all categories.
            custom_keywords: Additional keywords to include in queries.
            max_queries_per_category: Maximum number of queries to generate per category.

        Returns:
            List of Query objects.
        """
        queries = []

        # Determine which categories to use
        categories_to_use = categories if categories is not None else list(self.CATEGORIES.keys())

        for category in categories_to_use:
            if category not in self.CATEGORIES:
                continue

            keywords = self.CATEGORIES[category]

            # Add custom keywords if provided
            if custom_keywords:
                keywords = keywords + custom_keywords

            # Generate queries for this category
            # We'll create a few different query variations
            for i in range(min(max_queries_per_category, len(keywords))):
                # Take a subset of keywords for variety
                subset_size = min(3, len(keywords))  # Up to 3 keywords per query
                start_idx = (i * subset_size) % len(keywords)
                end_idx = min(start_idx + subset_size, len(keywords))
                query_keywords = keywords[start_idx:end_idx]

                # Wrap around if needed
                if len(query_keywords) < subset_size and len(keywords) > subset_size:
                    remaining = subset_size - len(query_keywords)
                    query_keywords.extend(keywords[:remaining])

                query = Query(
                    keywords=query_keywords,
                    category=category
                )
                queries.append(query)

        # If custom keywords were provided but no categories, create queries just for custom keywords
        if custom_keywords and not categories:
            for i in range(0, len(custom_keywords), 3):  # Groups of 3
                chunk = custom_keywords[i:i+3]
                query = Query(
                    keywords=chunk
                )
                queries.append(query)

        return queries

    def get_category_keywords(self, category: str) -> List[str]:
        """Get keywords for a specific category."""
        return self.CATEGORIES.get(category, [])

    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self.CATEGORIES.keys())