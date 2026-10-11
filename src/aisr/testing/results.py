from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class Outcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"

@dataclass(frozen=True)
class TestCase:
    __test__ = False  # not a pytest class
    class_name: str
    method: str
    @property
    def id(self) -> str:
        return f"{self.class_name}#{self.method}"

@dataclass
class TestResult:
    __test__ = False
    case: TestCase
    outcome: Outcome
    time_s: float = 0.0
    message: str = ""
    stack_trace: str = ""
    @property
    def failed(self) -> bool:
        return self.outcome in (Outcome.FAIL, Outcome.ERROR)

@dataclass
class SuiteResult:
    results: list[TestResult] = field(default_factory=list)
    build_ok: bool = True           # False => compilation/build failure before tests ran
    raw_log: str = ""
    duration_s: float = 0.0

    @property
    def failing(self) -> list[TestResult]:
        return [r for r in self.results if r.failed]
    @property
    def passing(self) -> list[TestResult]:
        return [r for r in self.results if r.outcome == Outcome.PASS]
    def stats(self) -> dict:
        return {"total": len(self.results), "passed": len(self.passing),
                "failed": len(self.failing), "build_ok": self.build_ok,
                "duration_s": round(self.duration_s, 2)}
