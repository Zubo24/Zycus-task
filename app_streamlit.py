import json
import streamlit as st
from src.triage import triage_ticket
from src.account_brief import generate_account_brief

# Setup page
st.set_page_config(page_title="Support AI Intern Task", layout="wide")
st.title("Support AI Intern Task")

# Load accounts for the dropdown
@st.cache_data
def load_accounts():
    try:
        with open("data/accounts.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

accounts = load_accounts()
account_ids = [acc["account_id"] for acc in accounts]
# Add a fake one for testing adversarial fallback
account_ids.append("ACC-FAKE-000")

# Create tabs
tab1, tab2 = st.tabs(["Triage a Ticket", "Account Brief"])

with tab1:
    st.header("Triage a Ticket")
    st.write("Enter the subject and body of a support ticket to automatically categorize it and draft a response.")
    
    with st.form("triage_form"):
        subject = st.text_input("Ticket Subject", value="Need help with DataBridge Pro API")
        body = st.text_area("Ticket Body", value="The API keeps throwing 403 Forbidden insufficient_scope errors when I try to sync data.")
        submit_triage = st.form_submit_button("Triage Ticket")
        
    if submit_triage:
        if not subject and not body:
            st.error("Please provide a ticket subject or body.")
        else:
            with st.spinner("Processing with local LLM..."):
                ticket_data = {
                    "ticket_id": "TKT-WEB-01",
                    "subject": subject,
                    "body": body
                }
                result = triage_ticket(ticket_data)
                
                st.success("Triage Complete")
                st.subheader("Classification")
                st.json({
                    "product": result.product,
                    "product_area": result.product_area,
                    "category": result.category,
                    "urgency": result.urgency,
                    "reasoning": result.reasoning,
                    "recommended_team": result.recommended_team,
                    "matched_kb_docs": result.matched_kb_docs
                })
                
                st.subheader("Draft Reply")
                st.info(result.draft_reply)

with tab2:
    st.header("Account Brief")
    st.write("Generate a synthesized health brief for a specific account based on recent ticket activity and escalation notes.")
    
    with st.form("brief_form"):
        selected_account = st.selectbox("Select Account ID", options=account_ids)
        submit_brief = st.form_submit_button("Generate Brief")
        
    if submit_brief:
        with st.spinner("Analyzing account with local LLM..."):
            result = generate_account_brief(selected_account)
            
            st.success(f"Brief Generated for {selected_account}")
            
            st.subheader("Executive Summary")
            st.write(result.executive_summary)
            
            st.subheader("Recommended Talking Points")
            for point in result.recommended_talking_points:
                st.write(f"- {point}")
                
            st.subheader("Flagged Issues (Verified)")
            if not result.flagged_issues:
                st.write("No issues flagged.")
            else:
                for issue in result.flagged_issues:
                    with st.expander(f"{issue.description} (Source: {issue.source})"):
                        st.write("**Direct Quote:**")
                        st.write(f"> {issue.quote}")
                        st.write(f"Verified: {'✅' if issue.is_verified else '❌'}")
