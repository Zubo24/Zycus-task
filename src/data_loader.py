"""Module for loading tickets and accounts data, and filtering by date."""
import json
import os
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def load_tickets() -> list:
    """Load tickets from JSON file."""
    tickets_path = os.path.join(DATA_DIR, "tickets.json")
    if not os.path.exists(tickets_path):
        return []
    with open(tickets_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_accounts() -> list:
    """Load accounts from JSON file."""
    accounts_path = os.path.join(DATA_DIR, "accounts.json")
    if not os.path.exists(accounts_path):
        return []
    with open(accounts_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_account(account_id: str) -> dict | None:
    """Retrieve an account by ID gracefully."""
    accounts = load_accounts()
    for acc in accounts:
        if acc.get("account_id") == account_id:
            return acc
    return None

def get_dataset_reference_date(tickets: list) -> datetime:
    """
    Mock dataset is frozen at a point in the past; we treat the latest ticket's created_at as 'now' so the 90-day window is meaningful regardless of when this code is actually run.
    """
    if not tickets:
        return datetime.now(timezone.utc)
    return max(datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) for t in tickets)

def get_recent_tickets(account_id: str, tickets: list, days: int = 90, reference_date: datetime | None = None) -> list:
    """Filter tickets for an account created within the last N days."""
    if reference_date is None:
        reference_date = get_dataset_reference_date(tickets)
    cutoff = reference_date - timedelta(days=days)
    return [
        t for t in tickets
        if t.get("account_id") == account_id
        and datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) > cutoff
    ]

if __name__ == "__main__":
    print("--- Sanity Checks ---")
    
    # 1. Load data
    all_accounts = load_accounts()
    all_tickets = load_tickets()
    print(f"Loaded {len(all_accounts)} accounts and {len(all_tickets)} tickets.")
    
    # 2. Known account
    if all_accounts:
        known_id = all_accounts[0]["account_id"]
        known_acc = get_account(known_id)
        print(f"\n[Known Account] ID: {known_id}")
        print(f"Found: {known_acc is not None} (Company: {known_acc.get('company')})")
        
        recent = get_recent_tickets(known_id, all_tickets, days=90)
        print(f"Recent tickets (last 90 days): {len(recent)}")
        
        # We might have 0 recent tickets if dataset dates are old compared to today's date
        # Let's see how many tickets exist ignoring date to be sure
        all_for_acc = [t for t in all_tickets if t.get("account_id") == known_id]
        print(f"Total tickets ignoring date: {len(all_for_acc)}")

    # 3. Fake account
    fake_id = "ACC-FAKE-999"
    fake_acc = get_account(fake_id)
    print(f"\n[Fake Account] ID: {fake_id}")
    print(f"Found: {fake_acc is not None}")
