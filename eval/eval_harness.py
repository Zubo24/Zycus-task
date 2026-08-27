"""Evaluation harness to run test cases and generate reports."""
import json
import os
from pydantic import BaseModel, Field
from src.triage import triage_ticket
from src.account_brief import generate_account_brief
from src.llm_client import call_structured

class JudgeOutput(BaseModel):
    score: float = Field(description="Quality score from 0.0 to 1.0. 1.0 is perfect, 0.0 is completely irrelevant or hallucinates.")
    reasoning: str = Field(description="Brief explanation of the score")

def evaluate_triage(test_case: dict) -> dict:
    ticket = test_case["ticket"]
    try:
        res = triage_ticket(ticket)
        passed = True
        notes = []
        
        if "expected_category" in test_case and res.category.lower() != test_case["expected_category"].lower():
            if "adv" not in test_case["id"]:
                passed = False
                notes.append(f"Expected category '{test_case['expected_category']}', got '{res.category}'.")
        
        # LLM Judge
        sys_prompt = "You are an evaluator grading a customer support draft reply. Rate its relevance, tone, and groundedness."
        user_prompt = f"Ticket:\n{ticket}\n\nDraft Reply:\n{res.draft_reply}\n\nEvaluate and score 0.0 to 1.0."
        
        try:
            judge = call_structured(sys_prompt, user_prompt, JudgeOutput)
            score = judge.score
            reason = judge.reasoning
        except Exception as e:
            score = 0.5
            reason = f"Judge failed to parse JSON: {e}"
            
        if score < 0.6:
            passed = False
            notes.append(f"Judge score low: {score}")
            
        return {
            "test_id": test_case["id"],
            "task": "Triage",
            "pass": passed,
            "score": score,
            "notes": " | ".join(notes) if notes else reason.replace('\n', ' ')
        }
    except Exception as e:
        return {
            "test_id": test_case["id"],
            "task": "Triage",
            "pass": False,
            "score": 0.0,
            "notes": f"Pipeline Exception: {str(e)}"
        }

def evaluate_brief(test_case: dict) -> dict:
    acc_id = test_case["account_id"]
    try:
        res = generate_account_brief(acc_id)
        passed = True
        notes = []
        
        if "adv" in test_case["id"]:
            if "not found" not in res.executive_summary.lower():
                passed = False
                notes.append("Adversarial case failed to return 'not found' message.")
        else:
            for issue in res.flagged_issues:
                if not issue.is_verified:
                    passed = False
                    notes.append(f"Unverified quote detected.")
        
        # LLM Judge
        sys_prompt = "You are an evaluator grading an account health brief. Rate its clarity and actionability."
        user_prompt = f"Account ID: {acc_id}\nBrief:\n{res.executive_summary}\n\nEvaluate and score 0.0 to 1.0."
        
        print("\n[DEBUG] --- LLM Judge Input ---")
        print(f"SYSTEM PROMPT:\n{sys_prompt}")
        print(f"USER PROMPT:\n{user_prompt}")
        print("-------------------------------\n")
        
        try:
            judge = call_structured(sys_prompt, user_prompt, JudgeOutput)
            score = judge.score
            reason = judge.reasoning
            print(f"[DEBUG] Judge Call SUCCEEDED. Score: {score}")
        except Exception as e:
            score = 0.5
            reason = f"Judge failed to parse JSON: {e}"
            print(f"[DEBUG] Judge Call FAILED. Exception: {e}")
            
        if score < 0.6:
            passed = False
            notes.append(f"Judge score low: {score}")
            
        return {
            "test_id": test_case["id"],
            "task": "Brief",
            "pass": passed,
            "score": score,
            "notes": " | ".join(notes) if notes else reason.replace('\n', ' ')
        }
    except Exception as e:
        return {
            "test_id": test_case["id"],
            "task": "Brief",
            "pass": False,
            "score": 0.0,
            "notes": f"Pipeline Exception: {str(e)}"
        }

def run_eval():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    triage_path = os.path.join(base_dir, "eval", "test_cases_triage.json")
    brief_path = os.path.join(base_dir, "eval", "test_cases_brief.json")
    report_path = os.path.join(base_dir, "eval", "eval_report.md")
    
    with open(triage_path, "r", encoding="utf-8") as f:
        triage_cases = json.load(f)
    with open(brief_path, "r", encoding="utf-8") as f:
        brief_cases = json.load(f)
        
    results = []
    print("Running Triage Evals (5 cases)...")
    for c in triage_cases:
        print(f"  -> {c['id']}")
        results.append(evaluate_triage(c))
        
    print("Running Brief Evals (5 cases)...")
    for c in brief_cases:
        print(f"  -> {c['id']}")
        results.append(evaluate_brief(c))
        
    # Write report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Evaluation Report\n\n")
        f.write("| Test ID | Task | Pass/Fail | Quality Score | Notes |\n")
        f.write("|---------|------|-----------|---------------|-------|\n")
        for r in results:
            pf = "Pass" if r["pass"] else "Fail"
            clean_notes = str(r['notes']).replace('\n', ' ')
            f.write(f"| {r['test_id']} | {r['task']} | {pf} | {r['score']:.2f} | {clean_notes[:100]} |\n")
            
    print(f"\nEvaluation complete! Report written to {report_path}")

if __name__ == "__main__":
    run_eval()
