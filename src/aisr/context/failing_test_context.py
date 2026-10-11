# Named failing_test_context.py (not test_context.py): pytest would collect any test_*.py under src/.
from __future__ import annotations
from ..testing.results import TestResult

def failing_test_context(r: TestResult) -> dict:
    return {"test": r.case.id, "message": r.message, "stack_trace": r.stack_trace.splitlines()[:25]}
