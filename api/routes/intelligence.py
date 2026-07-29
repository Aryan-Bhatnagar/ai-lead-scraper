from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from scraper.database import get_ai_insights_by_lead_id, get_lead_by_id
from api.services.ai_intelligence import intelligence_manager

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence"])

@router.get("/{lead_id}")
async def get_intelligence(lead_id: int):
    \"\"\"Retrieve cached AI insights for a lead.\"\"\"
    insights = get_ai_insights_by_lead_id(lead_id)
    if not insights:
        # Return an empty structure or 404.
        # Returning 200 with null insights allows frontend to decide to trigger generation.
        return {"lead_id": lead_id, "insights": None}

    return {"lead_id": lead_id, "insights": dict(insights)}

@router.post("/generate/{lead_id}")
async def generate_intelligence(lead_id: int, background_tasks: BackgroundTasks):
    \"\"\"Trigger AI intelligence generation for a lead.\"\"\"
    lead = get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    website = lead.get("website")
    if not website:
        raise HTTPException(status_code=400, detail="Lead has no website to analyze")

    company_name = lead.get("company_name", "the company")
    company_description = lead.get("company_description", "")

    try:
        # For this implementation, we do it synchronously to return the result immediately.
        # If the timeout is too high, we would move this to a BackgroundTask.
        insights = intelligence_manager.get_or_generate_intelligence(
            lead_id=lead_id,
            website=website,
            company_name=company_name,
            context=company_description
        )
        return {"status": "success", "insights": insights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Generation failed: {str(e)}")
