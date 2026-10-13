# Setup on Ubuntu 22.04/24.04

## Core (Maven projects, demo fixture)
```bash
sudo apt update && sudo apt install -y git unzip python3 python3-venv python3-pip openjdk-17-jdk maven
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]' && pytest -q
aisr baseline tests/fixtures/demo-maven && aisr localize tests/fixtures/demo-maven
```

## Defects4J benchmark (requires Java 11)
```bash
sudo apt install -y openjdk-11-jdk git subversion perl cpanminus build-essential
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64          # Defects4J 3.x was validated with Java 11
git clone https://github.com/rjust/defects4j ~/defects4j && cd ~/defects4j
cpanm --installdeps . && ./init.sh                           # downloads project repos; takes a while
export PATH=$PATH:$HOME/defects4j/framework/bin
defects4j info -p Lang | head                                # sanity check
# one bug by hand first
defects4j checkout -p Lang -v 1b -w /tmp/lang1b && cd /tmp/lang1b && defects4j compile && defects4j test
# then, from the project:
aisr localize /tmp/lang1b --max-tests 200
aisr d4j-eval --project Lang --bugs 1,3-5 --max-tests 200 --repair B
```
`init.sh` and the first checkouts need internet access. Run `aisr` with the Defects4J Java on `PATH`.

## Optional: LLM and Docker
```bash
curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen2.5-coder:7b
export AISR_MODEL_NAME=qwen2.5-coder:7b
aisr repair /tmp/lang1b --config D
export AISR_USE_DOCKER=1   # Maven/Gradle projects only: the stock image has no `defects4j`; containers have no network, so pre-populate the dependency cache
```

## Dashboard
```bash
pip install -e '.[api]' && aisr serve        # http://127.0.0.1:8000
```
