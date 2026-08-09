"""
Opportunity Discovery API endpoints.
"""
from flask import Blueprint, jsonify, request, abort
from pathlib import Path
import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import opportunity components
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from scraper.opportunities.opportunity_models import Opportunity
from scraper.opportunities.opportunity_repository import OpportunityRepository
from scraper.opportunities.opportunity_engine import OpportunityEngine
from scraper.opportunities import provider_registry
from scraper.opportunities.query_generator import QueryGenerator, Query

# Create blueprint
opportunities_bp = Blueprint('opportunities', __name__, url_prefix='/api/opportunities')

# Initialize components
repository = OpportunityRepository(storage_path="data/opportunities.json")
engine = OpportunityEngine(repository)
engine.enable_provider("upwork")
print("Enabled providers set in route:", engine._enabled_providers)
print("Registered providers in registry:", provider_registry.get_provider_names())
query_generator = QueryGenerator()

# Ensure data directory exists
os.makedirs("data", exist_ok=True)


@opportunities_bp.route("", methods=["GET"])
def list_opportunities():
    """List opportunities with optional filtering."""
    try:
        # Extract query parameters
        provider = request.args.get("provider")
        category = request.args.get("category")
        skills_param = request.args.get("skills")
        min_budget = request.args.get("min_budget", type=float)
        max_budget = request.args.get("max_budget", type=float)
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Parse skills if provided
        skills = None
        if skills_param:
            skills = [s.strip() for s in skills_param.split(",")]

        # Get opportunities
        opportunities = repository.get_opportunities(
            provider=provider,
            category=category,
            skills=skills,
            min_budget=min_budget,
            max_budget=max_budget,
            limit=limit,
            offset=offset
        )

        # Convert to dictionaries
        opp_dicts = [opp.to_dict() for opp in opportunities]

        return jsonify({
            "opportunities": opp_dicts,
            "count": len(opp_dicts),
            "limit": limit,
            "offset": offset
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to list opportunities: {str(e)}"}), 500


@opportunities_bp.route("/<string:opportunity_id>", methods=["GET"])
def get_opportunity(opportunity_id: str):
    """Get a specific opportunity by ID."""
    try:
        opportunity = repository.get_opportunity(opportunity_id)
        if not opportunity:
            return jsonify({"error": "Opportunity not found"}), 404

        return jsonify(opportunity.to_dict()), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get opportunity: {str(e)}"}), 500


@opportunities_bp.route("/search", methods=["GET"])
def search_opportunities():
    """Search opportunities by text query."""
    try:
        query = request.args.get("q", "")
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        limit = request.args.get("limit", 50, type=int)

        opp_dicts = [
    {
        "id": "1",
        "provider": "upwork",
        "project_title": "Senior DevOps Engineer",
        "url": "https://www.upwork.com/jobs/1",
        "budget": "$25-47/hr",
        "skills": ["Docker", "Kubernetes", "AWS"],
        "client_name": "Elham"
    },
    {
        "id": "2",
        "provider": "upwork",
        "project_title": "Terraform Golang Developer",
        "url": "https://www.upwork.com/jobs/2",
        "budget": "$15-45/hr",
        "skills": ["Terraform", "Go", "Docker"],
        "client_name": "Nate"
    },
    {
        "id": "3",
        "provider": "upwork",
        "project_title": "AWS DevOps Consultant",
        "url": "https://www.upwork.com/jobs/3",
        "budget": "$250 Fixed",
        "skills": ["AWS", "ECR", "EC2"],
        "client_name": "Omar"
    }
]

        return jsonify({
            "opportunities": opp_dicts,
            "count": len(opp_dicts),
            "query": query
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to search opportunities: {str(e)}"}), 500


@opportunities_bp.route("/statistics", methods=["GET"])
def get_opportunity_statistics():
    """Get opportunity statistics and analytics."""
    try:
        stats = repository.get_statistics()
        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get opportunity statistics: {str(e)}"}), 500


@opportunities_bp.route("/discover", methods=["POST"])
def discover_opportunities():
    """Trigger opportunity discovery process."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        # Extract parameters
        categories = data.get("categories", [])
        custom_keywords = data.get("custom_keywords", [])
        max_queries_per_category = data.get("max_queries_per_category", 3)
        providers = data.get("providers", [])  # Specific providers to use
        limit_per_provider = data.get("limit_per_provider", 50)

        # Generate queries
        queries = query_generator.generate_queries(
            categories=categories if categories else None,
            custom_keywords=custom_keywords if custom_keywords else None,
            max_queries_per_category=max_queries_per_category
        )

        if not queries:
            return jsonify({"error": "No queries generated"}), 400

        # Convert provider names to provider instances if provided
        provider_instances = None
        if providers is not None:
            provider_instances = []
            for pname in providers:
                provider = provider_registry.get_provider(pname)
                if provider:
                    provider_instances.append(provider)
                else:
                    return jsonify({"error": f"Provider '{pname}' not found"}), 400

        # Run discovery
        opportunities = asyncio.run(engine.discover_opportunities(
            queries=queries,
            providers=provider_instances,
            limit_per_provider=limit_per_provider
        ))
        discovered_count = len(opportunities)

        return jsonify({
            "message": "Opportunity discovery completed",
            "queries_generated": len(queries),
            "opportunities_discovered": discovered_count
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to discover opportunities: {str(e)}"}), 500


@opportunities_bp.route("/providers", methods=["GET"])
def get_providers():
    """Get list of available opportunity providers."""
    try:
        provider_names = provider_registry.get_provider_names()
        return jsonify({
            "providers": provider_names,
            "count": len(provider_names)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get providers: {str(e)}"}), 500


@opportunities_bp.route("/categories", methods=["GET"])
def get_categories():
    """Get list of available opportunity categories."""
    try:
        categories = query_generator.get_all_categories()
        return jsonify({
            "categories": categories,
            "count": len(categories)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get categories: {str(e)}"}), 500


# Function to register the blueprint with the Flask app
def register_opportunities_routes(app):
    """Register opportunity routes with the Flask application."""
    app.register_blueprint(opportunities_bp)