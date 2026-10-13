# Benchmarks
Primary benchmark: Defects4J (https://github.com/rjust/defects4j), version 3.0.1 at time of writing, **Java 11**.
Install steps: `docs/SETUP_UBUNTU.md`. The `defects4j` backend (`build_system == "defects4j"`) is selected automatically for any
directory that contains `defects4j.build.properties`.

Checkouts go to `benchmarks/checkouts/` (git-ignored). Freeze the list of bug ids in your experiment notes once you have verified that
`defects4j compile` and `defects4j test` work for them on your machine (some bugs depend on the JDK and timezone).
