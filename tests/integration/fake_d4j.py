"""Emulates the `defects4j` CLI (test / compile / coverage / export) using the exact file formats read from the
Defects4J 3.0.1 sources: all_tests = JUnit toString lines, failing_tests = '--- Class::method' + stack trace,
coverage.xml = Cobertura. Reuses the Calc semantics of fake_maven."""
from pathlib import Path
from aisr.testing.runner import CommandResult
from fake_maven import TESTS, LINES, _eval

class FakeDefects4J:
    def __init__(self):
        self.calls = []
    def run(self, cmd, cwd, timeout):
        cwd = Path(cwd); self.calls.append(cmd)
        if cmd[0] != "defects4j":
            return CommandResult(127, "not found")
        sub = cmd[1]; src = (cwd / "src/main/java/demo/Calc.java").read_text()
        if sub == "export":
            return CommandResult(0, "some stderr noise: not a class!\ndemo.Calc\n") if cmd[3] == "classes.relevant" else CommandResult(0, "")
        if sub == "compile":
            return CommandResult(0 if _eval(src, 0) is not None else 1, "")
        sel = cmd[cmd.index("-t") + 1].split("::")[1] if "-t" in cmd else None
        names = [sel] if sel else list(TESTS)
        if sub == "test":
            if _eval(src, 0) is None:
                return CommandResult(1, "compile error")
            with open(cwd / "all_tests", "a") as a, open(cwd / "failing_tests", "a") as f:
                for n in names:
                    a.write(f"{n}(demo.CalcTest)\n")
                    x, want = TESTS[n]
                    if _eval(src, x) != want:
                        f.write(f"--- demo.CalcTest::{n}\njava.lang.AssertionError\n\tat demo.Calc.isPositive(Calc.java:8)\n"
                                f"\tat demo.CalcTest.{n}(CalcTest.java:6)\n")
            return CommandResult(0, "Failing tests: ...")
        if sub == "coverage":
            assert "-i" in cmd, "coverage must pass -i (otherwise only fix-modified classes are instrumented: oracle leak)"
            assert (cwd / cmd[cmd.index("-i") + 1]).read_text().split() == ["demo.Calc"]
            hit = set(LINES[names[0]])
            lines = "".join(f'<line number="{n}" hits="{1 if n in hit else 0}" branch="false"/>' for n in (5, 6, 8))
            (cwd / "coverage.xml").write_text(
                '<?xml version="1.0"?><!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">'
                '<coverage><packages><package name="demo"><classes>'
                '<class name="demo.Calc" filename="demo/Calc.java"><methods>'
                f'<method name="isPositive" signature="(I)Z"><lines><line number="5" hits="1"/><line number="8" hits="1"/></lines></method></methods>'
                f'<lines>{lines}</lines></class></classes></package></packages></coverage>')
            return CommandResult(0, "")
        return CommandResult(2, "unknown")
