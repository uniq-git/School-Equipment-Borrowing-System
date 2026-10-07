"""
Run the overdue check once from the command line (for Windows Task Scheduler / cron):
    python scripts/run_overdue_check.py

Every active borrowing that is past its due date gets a reminder email
(repeated every few days until the equipment is returned).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services import borrow_service


def main():
    sent, failed, first_error = borrow_service.run_overdue_check()
    print(f"Overdue check done: {sent} reminder(s) sent, {failed} failed.")

    if failed:
        print(f"First error: {first_error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())