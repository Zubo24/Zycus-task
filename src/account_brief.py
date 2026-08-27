"""Task 2 Pipeline: TAM Account Health Summariser."""
import json
from src.schemas import AccountBrief
from src.llm_client import call_structured
from src.data_loader import get_account, load_tickets, get_recent_tickets

def generate_account_brief(account_id: str) -> AccountBrief:
    """Generate a TAM account brief summarizing health and recent tickets."""
    
    # 1. Lookup account
    account = get_account(account_id)
    if not account:
        return AccountBrief(
            executive_summary=f"Account {account_id} not found in the system.",
            flagged_issues=[],
            recommended_talking_points=[]
        )
        
    # 2. Get recent tickets
    all_tickets = load_tickets()
    recent_tickets = get_recent_tickets(account_id, all_tickets, days=90)
    from src.llm_client import call_structured, call_text
    
    # 2b. Early return if no tickets and no escalation notes
    notes = account.get("escalation_notes", [])
    if not recent_tickets and not notes:
        h_status = account.get('health_status', 'Unknown')
        u_trend = account.get('usage_trend', 'Unknown')
        nps = account.get('nps_score', 'N/A')
        
        summary = (
            f"No recent ticket activity or escalation notes in the last 90 days. "
            f"Account health status is '{h_status}' with a '{u_trend}' usage trend. "
            f"NPS score is {nps}."
        )
        return AccountBrief(
            executive_summary=summary,
            flagged_issues=[],
            recommended_talking_points=[
                f"Acknowledge their {h_status} health status.",
                f"Discuss their {u_trend} usage trend.",
                "Check in on their general satisfaction."
            ]
        )
        
    # Step 3a: Extract Quotes First
    extract_sys = (
        "List each sentence from the ACCOUNT DATA below that indicates risk. "
        "Output one per line. Do not include instructions or examples in your output."
    )
    acc_data = {
        "account_id": account.get("account_id"),
        "company": account.get("company"),
        "plan_tier": account.get("plan_tier"),
        "health_status": account.get("health_status"),
        "usage_trend": account.get("usage_trend"),
        "escalation_notes": account.get("escalation_notes", []),
        "nps_score": account.get("nps_score")
    }
    tickets_data = [
        {
            "ticket_id": t.get("ticket_id"),
            "subject": t.get("subject"),
            "category": t.get("category"),
            "urgency": t.get("urgency"),
            "status": t.get("status"),
            "body": t.get("body")
        } for t in recent_tickets
    ]
    user_prompt = f"Account Data:\n{json.dumps(acc_data, indent=2)}\n\nRecent Tickets (last 90 days):\n{json.dumps(tickets_data, indent=2)}\n\nExtract the quotes."
    
    extracted_text = call_text(extract_sys, user_prompt)
    print(f"\n[DEBUG] Extracted Text from LLM:\n{extracted_text}\n")
    
    extracted_quotes = [line.strip("- ").strip() for line in extracted_text.split("\n") if line.strip().startswith("- ")]
    if not extracted_quotes:
        # Fallback if model doesn't use the dash
        extracted_quotes = [line.strip() for line in extracted_text.split("\n") if line.strip()]
        
    print(f"\n[DEBUG] Parsed Quotes Array:\n{extracted_quotes}\n")
    
    # Step 3b: Generate Final Brief
    sys_prompt = (
        "You are an expert Technical Account Manager (TAM) assistant. Analyze the provided account data "
        "and recent tickets to generate a concise health summary. For any flagged risks, you MUST provide "
        "a VERBATIM quote directly extracted from the ticket body or escalation_notes. Do not paraphrase quotes.\n\n"
        "Crucially, your output MUST be a JSON object with this exact structure. Do NOT reuse the placeholder text "
        "shown in the example. You MUST extract a real quote from the provided 'Extracted Candidate Quotes':\n"
        "{\n"
        '  "executive_summary": "<3-5 sentences summarizing account health>",\n'
        '  "flagged_issues": [\n'
        '    {\n'
        '      "description": "<what the issue is>",\n'
        '      "quote": "<verbatim text copied EXACTLY from the Extracted Candidate Quotes>",\n'
        '      "source": "<ticket_id or escalation_notes>",\n'
        '      "is_verified": true\n'
        '    }\n'
        '  ],\n'
        '  "recommended_talking_points": [\n'
        '    "<actionable talking point 1>",\n'
        '    "<actionable talking point 2>"\n'
        '  ]\n'
        "}"
    )
    
    user_prompt_final = f"Account Data:\n{json.dumps(acc_data, indent=2)}\n\nRecent Tickets (last 90 days):\n{json.dumps(tickets_data, indent=2)}\n\nExtracted Candidate Quotes:\n{json.dumps(extracted_quotes, indent=2)}\n\nGenerate the account brief."
    
    brief = call_structured(sys_prompt, user_prompt_final, AccountBrief)
    
    # 4. Rule-based post-check: verify quotes
    for issue in brief.flagged_issues:
        clean_quote = issue.quote.strip(' "\',\n\r')
        if not clean_quote:
            issue.is_verified = False
            issue.description = f"[UNVERIFIED QUOTE] {issue.description}"
            continue
            
        found = False
        
        # Check escalation notes
        for note in acc_data.get("escalation_notes", []):
            if clean_quote in note:
                found = True
                break
                
        # Check ticket bodies
        if not found:
            for t in tickets_data:
                body = t.get("body", "")
                if clean_quote in body or clean_quote.replace('\\n', '\n') in body:
                    found = True
                    break
                    
        issue.is_verified = found
        if not found:
            issue.description = f"[UNVERIFIED QUOTE] {issue.description}"
            
    return brief

if __name__ == "__main__":
    print("--- Sanity Check: Account Brief Pipeline ---")
    
    # 1. Known account with tickets
    known_id = "ACC-3336"  # The one we checked earlier
    print(f"\n[Testing Known Account: {known_id}]")
    try:
        brief_known = generate_account_brief(known_id)
        print(json.dumps(brief_known.model_dump(), indent=2))
    except Exception as e:
        print(f"Error generating brief: {e}")
        
    # 2. Fake account
    fake_id = "ACC-MISSING-404"
    print(f"\n[Testing Fake Account: {fake_id}]")
    brief_fake = generate_account_brief(fake_id)
    print(json.dumps(brief_fake.model_dump(), indent=2))
