"""Task 1 Pipeline: Ticket Triage."""
import json
from pydantic import BaseModel, Field
from src.schemas import TriageClassification, TriageResult
from src.llm_client import call_structured
from src.retrieval import search

class DraftReplyOutput(BaseModel):
    draft_reply: str = Field(description="The drafted first response to the customer")

TEAM_ROUTING_RULES = {
    "P1": "Escalations",
    "Billing": "Billing Ops",
    "Integration": "Platform Integrations",
    "Onboarding": "Onboarding Success"
}

def determine_team(urgency: str, category: str, product: str) -> str:
    """Deterministic routing based on urgency and category."""
    if urgency.upper() == "P1":
        return TEAM_ROUTING_RULES["P1"]
    
    # Handle capitalization variations
    for key, team in TEAM_ROUTING_RULES.items():
        if key.lower() in category.lower():
            return team
            
    return "General Support"

def triage_ticket(ticket: dict | str) -> TriageResult:
    """End-to-end triage pipeline for a single ticket."""
    
    # 1. Parse input
    if isinstance(ticket, str):
        try:
            parsed = json.loads(ticket)
            if isinstance(parsed, dict):
                subject = parsed.get("subject", "")
                body = parsed.get("body", "")
            else:
                subject = ""
                body = ticket
        except json.JSONDecodeError:
            subject = ""
            body = ticket
    else:
        subject = ticket.get("subject", "")
        body = ticket.get("body", "")
        
    ticket_text = f"Subject: {subject}\nBody: {body}".strip()
    
    # 2. Classification LLM Call
    sys_prompt_classification = (
        "You are an expert technical support triage agent. Read the ticket and classify it. "
        "Strictly adhere to the enum values described in the schema."
    )
    classification = call_structured(sys_prompt_classification, ticket_text, TriageClassification)
    
    # 3. KB Retrieval
    # Combine ticket content and LLM classification for a rich BM25 query
    query = f"{classification.product} {classification.product_area} {classification.category} {subject} {body}"
    kb_results = search(query, top_k=2)
    matched_docs = [f"{r['source_file']} - {r['heading']}" for r in kb_results]
    
    # 4. Routing
    team = determine_team(classification.urgency, classification.category, classification.product)
    
    # 5. Draft Reply LLM Call
    kb_context = "\n\n".join([f"--- Source: {r['source_file']} | Section: {r['heading']} ---\n{r['text']}" for r in kb_results])
    
    sys_prompt_draft = (
        "You are a helpful customer support agent. Write a professional, empathetic first response to the customer's ticket. "
        "Use the provided Knowledge Base context to ground your answer. Do not hallucinate troubleshooting steps; "
        "if you provide steps, they MUST come from the KB context. "
        "If the KB docs don't contain the answer, acknowledge the issue, state that we are investigating, and ask for any needed clarification."
    )
    user_prompt_draft = f"Ticket:\n{ticket_text}\n\nRelevant KB Context:\n{kb_context}"
    
    draft_out = call_structured(sys_prompt_draft, user_prompt_draft, DraftReplyOutput)
    
    # 6. Assemble
    return TriageResult(
        product=classification.product,
        product_area=classification.product_area,
        category=classification.category,
        urgency=classification.urgency,
        reasoning=classification.reasoning,
        matched_kb_docs=matched_docs,
        recommended_team=team,
        draft_reply=draft_out.draft_reply
    )

if __name__ == "__main__":
    from src.data_loader import load_tickets
    
    print("--- Sanity Check: Triage Pipeline ---")
    tickets = load_tickets()
    if tickets:
        sample = tickets[0]
        print(f"Processing ticket: {sample.get('ticket_id')}")
        result = triage_ticket(sample)
        print("\n--- Result ---")
        print(json.dumps(result.model_dump(), indent=2))
    else:
        print("No tickets found to test.")
