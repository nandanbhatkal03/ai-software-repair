"""A CommandRunner that emulates just enough of Maven + JUnit + JaCoCo for the demo-maven fixture, so the whole
pipeline can be exercised without Java/Maven. It EVALUATES the 'return x <op> K;' line of Calc.java, so patches
really change test outcomes."""
import re
from pathlib import Path
from aisr.testing.runner import CommandResult

TESTS = {"testPos": (5, True), "testNeg": (-1, False), "testZero": (0, False)}
OPS = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
       "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
# executable lines of the (unpatched) file and which tests reach them
LINES = {"testPos": [5, 8], "testNeg": [5, 8], "testZero": [5, 6, 8]}

def _eval(src: str, x: int):
    m = re.search(r"return x (>=|<=|==|!=|>|<) (-?\d+);", src)
    return OPS[m.group(1)](x, int(m.group(2))) if m else None

class FakeMaven:
    def __init__(self):
        self.calls = []
    def run(self, cmd, cwd, timeout):
        cwd = Path(cwd); self.calls.append(cmd)
        src = (cwd / "src/main/java/demo/Calc.java").read_text()
        joined = " ".join(cmd)
        if "compile" in cmd:
            return CommandResult(0 if _eval(src, 0) is not None else 1, "")
        if "test" not in cmd:
            return CommandResult(0, "")
        if _eval(src, 0) is None:
            return CommandResult(1, "COMPILATION ERROR")
        sel = next((c.split("=", 1)[1] for c in cmd if c.startswith("-Dtest=")), None)
        names = [sel.split("#")[1]] if sel else list(TESTS)
        rep = cwd / "target" / "surefire-reports"; rep.mkdir(parents=True, exist_ok=True)
        cases = ""
        for n in names:
            x, want = TESTS[n]
            if _eval(src, x) == want:
                cases += f'<testcase classname="demo.CalcTest" name="{n}" time="0.01"/>'
            else:
                cases += (f'<testcase classname="demo.CalcTest" name="{n}" time="0.01"><failure message="expected:&lt;{want}&gt;">'
                          f'java.lang.AssertionError\n\tat demo.Calc.isPositive(Calc.java:8)\n\tat demo.CalcTest.{n}(CalcTest.java:6)</failure></testcase>')
        (rep / "TEST-demo.CalcTest.xml").write_text(f'<testsuite name="demo.CalcTest">{cases}</testsuite>')
        if "jacoco" in joined:
            out = cwd / "target/site/jacoco"; out.mkdir(parents=True, exist_ok=True)
            hit = set(LINES[names[0]])
            lines = "".join(f'<line nr="{n}" mi="{0 if n in hit else 1}" ci="{1 if n in hit else 0}" mb="0" cb="0"/>' for n in (5, 6, 8))
            (out / "jacoco.xml").write_text(
                '<?xml version="1.0"?><!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">'
                '<report name="demo"><package name="demo">'
                '<class name="demo/Calc" sourcefilename="Calc.java"><method name="isPositive" desc="(I)Z" line="4"/></class>'
                f'<sourcefile name="Calc.java">{lines}</sourcefile></package></report>')
        return CommandResult(0, "")
