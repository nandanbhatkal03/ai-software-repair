"""Detect build system and source/test directories of a Java project."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectInfo:
    build_system: str          # "maven" | "gradle" | "unknown"
    language: str              # "java" | "unknown"
    source_dirs: tuple[str, ...]
    test_dirs: tuple[str, ...]

def detect_project(root: Path) -> ProjectInfo:
    root = Path(root)
    if (root / "defects4j.build.properties").exists():
        from ..testing.defects4j import read_properties
        props = read_properties(root)
        return ProjectInfo("defects4j", "java",
                           (props.get("d4j.dir.src.classes", "src/main/java"),),
                           (props.get("d4j.dir.src.tests", "src/test/java"),))
    if (root / "pom.xml").exists():
        build = "maven"
    elif (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        build = "gradle"
    else:
        build = "unknown"

    def existing(cands):
        return tuple(c for c in cands if (root / c).is_dir())

    # Maven/Gradle defaults first, then common Defects4J layouts (src/java, src/main/java, source, ...)
    src = existing(["src/main/java", "src/java", "source", "src"])
    tst = existing(["src/test/java", "src/test", "tests", "test"])
    # drop a directory when a more specific one inside it was found ("src" contains "src/main/java", "src/test" contains "src/test/java")
    def most_specific(dirs):
        return tuple(d for d in dirs if not any(o != d and o.startswith(d + "/") for o in dirs))
    src, tst = most_specific(src), most_specific(tst)
    has_java = any(root.rglob("*.java"))
    return ProjectInfo(build, "java" if has_java else "unknown", src, tst)
