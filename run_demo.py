import json
from src.triage import triage_ticket
from src.account_brief import generate_account_brief
from eval.eval_harness import evaluate_triage, evaluate_brief

def main():
    print("==================================================")
    print("   Support AI Intern Task - End-to-End Demo")
    print("==================================================\n")
    
    # 1. Task 1: Triage Ticket
    print("--- TASK 1: Triage Ticket ---")
    with open("data/tickets.json") as f:
        tickets = json.load(f)
    sample_ticket = tickets[0] # Pick the first ticket
    print(f"Input Ticket ({sample_ticket['ticket_id']}): {sample_ticket['subject']}")
    triage_result = triage_ticket(sample_ticket)
    print("Result:")
    print(triage_result.model_dump_json(indent=2))
    print("\n")
    
    # 2. Task 2: Account Brief (With tickets)
    print("--- TASK 2: Account Brief (With Activity) ---")
    acc_with_tickets = "ACC-3336"
    print(f"Input Account: {acc_with_tickets}")
    brief_active = generate_account_brief(acc_with_tickets)
    print("Result:")
    print(brief_active.model_dump_json(indent=2))
    print("\n")
    
    # 3. Task 2: Account Brief (No tickets fallback)
    print("--- TASK 2: Account Brief (No Activity Fallback) ---")
    acc_no_tickets = "ACC-4654"
    print(f"Input Account: {acc_no_tickets}")
    brief_inactive = generate_account_brief(acc_no_tickets)
    print("Result:")
    print(brief_inactive.model_dump_json(indent=2))
    print("\n")
    
    # 4. Eval Harness
    print("--- TASK 3: Running Evaluation Harness ---")
    print("This will take a few minutes as it processes all test cases through the local 1B model...")
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "eval.eval_harness"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Eval harness failed:")
        print(result.stderr)
    else:
        print("Eval harness completed successfully. Output written to eval/eval_report.md.")
        
    print("\n==================================================")
    print("   Demo Complete!")
    print("==================================================")

if __name__ == "__main__":
    main()
