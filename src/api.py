"""FastAPI application providing endpoints for Triage and Account Brief tasks."""
from fastapi import FastAPI, Body
from typing import Union, Dict, Any
from src.schemas import TriageResult
from src.triage import triage_ticket

app = FastAPI(title="Support AI API")

@app.post("/triage", response_model=TriageResult)
def triage_endpoint(ticket: Union[Dict[str, Any], str] = Body(..., description="Raw text or JSON with subject and body")):
    """Triage a raw ticket and generate classification, routing, and a draft response."""
    return triage_ticket(ticket)
