# Benchmarks
Primary: Defects4J (https://github.com/rjust/defects4j). Check its README for the required JDK and Perl setup.
Defects4J checkouts are built through its own `defects4j compile|test|coverage` commands, so the Maven/Gradle
runner needs a `Defects4JAdapter` (TODO) before benchmark runs. Freeze the bug list in `configs/` once builds are verified.
