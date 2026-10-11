"""Optional PIT mutation-score stage (expensive; run only on patches that survived everything else)."""
from __future__ import annotations
import re
from pathlib import Path
from ..testing.runner import CommandRunner, LocalRunner

def pit_mutation_score(project: Path, target_classes: str, pit_version: str = "1.15.8",
                       runner: CommandRunner | None = None) -> float | None:
    p = f"org.pitest:pitest-maven:{pit_version}"
    r = (runner or LocalRunner()).run(["mvn", "-B", "-q", f"{p}:mutationCoverage", f"-DtargetClasses={target_classes}",
                                       "-DoutputFormats=XML"], project, 1800)
    xmls = sorted(Path(project, "target", "pit-reports").rglob("mutations.xml"))
    if not xmls:
        return None
    text = xmls[-1].read_text(errors="ignore")
    total = len(re.findall(r"<mutation ", text))
    killed = len(re.findall(r'<mutation [^>]*status=.KILLED.', text))
    return killed / total if total else None
