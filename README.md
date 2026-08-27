# Support AI Intern Task

This repository contains the solution for the Support AI Intern Task, demonstrating an automated workflow for triaging support tickets and generating account health briefs using local Large Language Models (LLMs).

## Project Overview

**Loom walkthrough:** - https://www.loom.com/share/58f23c461259483ebb11bf5f321ab9f0

The project consists of three main components:
1. **Task 1: Ticket Triage (`src/triage.py`)** - Parses incoming support tickets, uses an LLM to categorize them (Product, Category, Urgency), fetches relevant knowledge base articles via BM25 retrieval, determines routing via a deterministic ruleset, and drafts a contextual first response.
2. **Task 2: Account Health Briefs (`src/account_brief.py`)** - Synthesizes recent ticket data and account context into a structured executive summary, extracts flagged issues with verified direct quotes, and suggests talking points for Customer Success Managers.
3. **Task 3: Evaluation Harness (`eval/eval_harness.py`)** - An automated evaluation suite that runs a series of standard and adversarial test cases through the pipeline, grading the outputs structurally and utilizing an LLM-as-a-Judge for qualitative scoring.

## Setup Instructions

1. **Create and Activate a Virtual Environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables:**
   Copy `.env.example` to `.env`. Ensure the following values are set:
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=gemma3:1b
   ```

4. **Start Ollama Locally:**
   This project is configured to run exclusively on a local 1B parameter model. You must have [Ollama](https://ollama.com/) installed and the `gemma3:1b` model pulled:
   ```bash
   ollama run gemma3:1b
   ```

## Running the Demo

To run a full end-to-end demonstration covering a single triage ticket, two account briefs (one active, one inactive fallback), and the full evaluation suite, run:

```bash
python run_demo.py
```

## Sample Outputs

### Task 1: Triage Ticket Result
```json
{
  "product": "DataBridge Pro",
  "product_area": "Sync",
  "category": "Bug",
  "urgency": "P1",
  "reasoning": "The issue involves a critical system failure with DataBridge Pro, resulting in slow page loads and API timeouts for 198 users.",
  "suggested_team": "Escalations",
  "draft_response": "Hello Taylor,\n\nWe are investigating the performance issues with DataBridge Pro and treating this as a high priority. Our team is actively working on a resolution. We will provide updates as they become available.\n\nBest regards,\nSupport Team"
}
```

### Task 2: Account Brief Result (Active Account)
```json
{
  "executive_summary": "Omni Consumer Products' Business plan tier account (ACC-3336) is currently at risk due to a concerning pattern of P1 tickets and a decision maker considering vendor evaluation. Recent activity indicates a significant performance issue with DataBridge Pro, impacting 198 users across the EU-West region. Immediate attention is required to address the root cause and mitigate potential data loss.",
  "flagged_issues": [
    {
      "description": "Significant performance degradation in DataBridge Pro, resulting in slow page loads and API timeouts, impacting 198 users across the EU-West region.",
      "quote": "\"Page loads are taking 119+ seconds and API operations are timing out.\"",
      "source": "TKT-10293",
      "is_verified": true
    }
  ],
  "recommended_talking_points": [
    "Initiate a thorough investigation into the DataBridge Pro performance issues.",
    "Escalate to the decision maker to understand the root cause and potential impact on business operations.",
    "Review data integrity and monitoring dashboards to identify bottlenecks.",
    "Collaborate with the DataBridge Pro vendor to address the performance issues and ensure a stable solution."
  ]
}
```

## Known Limitations

This project is built and optimized for a local **1B parameter model (gemma3:1b)**, not a hosted API like Anthropic or OpenAI. 
- **Trade-offs:** Running locally ensures zero data privacy concerns and incurs zero API costs. However, small models struggle significantly with instruction following, structured JSON output, and complex logic. We had to implement robust application-level guardrails (multi-step extraction, deterministic post-checks, input guards) to compensate for these model limitations.
- **Speed:** Local inference on CPUs can be slow and prevents concurrent processing at scale.
- **Fallback Guard:** The "empty-data fallback" currently pieces together a rigid template using NPS and usage trends. It lacks true synthesis (e.g. failing to flag a contradiction between a 'Healthy' status and 'Inactive' usage with low NPS), which would require a smarter, multi-shot LLM pass instead of our current deterministic string injection.

For an in-depth discussion on design choices, failure modes, and scalability trade-offs, please refer to the [DESIGN_NOTE.md](DESIGN_NOTE.md).
