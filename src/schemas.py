from pydantic import BaseModel, Field
from typing import List

# --- Task 1 Models ---

class TriageClassification(BaseModel):
    """The structured output strictly produced by the first LLM classification call."""
    product: str = Field(description="One of: DataBridge Pro, CloudSync, AnalyticsHub, SecureVault, WorkflowEngine, or Unknown")
    product_area: str = Field(description="Module within product, e.g. Connectors")
    category: str = Field(description="Bug / Feature Request / How-To / Performance / Billing / Integration / Onboarding / Data Loss")
    urgency: str = Field(description="P1, P2, P3, or P4")
    reasoning: str = Field(description="1-3 sentences explaining the classification")

class TriageResult(BaseModel):
    """The final assembled output returned by the triage pipeline."""
    product: str
    product_area: str
    category: str
    urgency: str
    reasoning: str
    matched_kb_docs: List[str]
    recommended_team: str
    draft_reply: str

# --- Task 2 Models ---

class FlaggedIssue(BaseModel):
    description: str = Field(description="Description of the open risk or flagged issue")
    quote: str = Field(description="A direct quote copied verbatim from the ticket body or escalation_notes")
    source: str = Field(description="Which field or ticket_id the quote came from")
    is_verified: bool = Field(default=True, description="Internal flag indicating if the quote was successfully verified against the source text")

class AccountBrief(BaseModel):
    executive_summary: str = Field(description="3-5 sentences summarizing the account health and recent tickets")
    flagged_issues: List[FlaggedIssue] = Field(description="List of open risks and flagged issues with explicit quotes")
    recommended_talking_points: List[str] = Field(description="Bulleted, action-oriented talking points for the TAM")
