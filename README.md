# Spark Langflow Multi-Agent Developer Setup

Native **Langflow + Ollama + MCP** setup for building a local multi-agent software development system on NVIDIA DGX Spark.

## Architecture

```text
DGX Spark
├── Ollama                  # local LLM serving
├── Langflow                # native host install and orchestration
├── MCP developer server    # restricted filesystem/Git/test tools
└── ~/Documents/Workspace/
    ├── agent-system/
    │   ├── langflow/
    │   └── mcp-server/
    ├── projects/
    └── shared/
```

Recommended agent hierarchy:

```text
User
  |
  v
Supervisor
  |-- Architect
  |-- Developer
  |-- Tester
  `-- Reviewer
```

The recommended pattern is **one supervisor plus specialist agents**, with Git and project files as the shared source of truth.

## 1. Create the workspace

```bash
mkdir -p ~/Documents/Workspace/projects
mkdir -p ~/Documents/Workspace/agent-system/mcp-server
mkdir -p ~/Documents/Workspace/agent-system/langflow
mkdir -p ~/Documents/Workspace/agent-system/prompts
mkdir -p ~/Documents/Workspace/shared
```

Autonomous coding should be restricted to:

```text
/home/spark0/Documents/Workspace/projects
```

Do not expose unrestricted `/home`, `/etc`, SSH keys, `sudo`, or system package management to the coding agents.

## 2. Install the MCP development server

```bash
cd ~/Documents/Workspace/agent-system/mcp-server
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install "mcp[cli]==2.0.0" pydantic pytest
```

Copy `mcp-server/server.py` from this repository to:

```text
~/Documents/Workspace/agent-system/mcp-server/server.py
```

Test it:

```bash
python server.py
```

A STDIO MCP server normally waits quietly for a client. Press `Ctrl+C` to stop it.

Optional MCP Inspector:

```bash
mcp dev server.py
```

## 3. Install Langflow natively

Native Langflow is recommended here because it shares the host filesystem and can launch the host-side STDIO MCP server directly.

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

Create a dedicated Langflow environment:

```bash
cd ~/Documents/Workspace/agent-system/langflow
uv venv .venv
source .venv/bin/activate
uv pip install "langflow[postgresql]"
langflow --version
```

Create a persistent data directory:

```bash
mkdir -p ~/Documents/Workspace/agent-system/langflow/data
```

Create `.env` from `.env.example` and set a strong password.

Start Langflow:

```bash
cd ~/Documents/Workspace/agent-system/langflow
source .venv/bin/activate
langflow run --env-file .env
```

Open:

```text
http://127.0.0.1:7860
```

## 4. Start Langflow automatically

Copy `systemd/langflow.service` to:

```text
/etc/systemd/system/langflow.service
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable langflow
sudo systemctl start langflow
systemctl status langflow
```

The MCP STDIO server does not need its own service. Langflow launches it when needed.

## 5. Ollama

Verify Ollama:

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
```

With native Langflow on the same Spark host, use:

```text
http://127.0.0.1:11434
```

A local coding model such as `qwen3-coder:30b` is a good starting point if installed.

## 6. Register the MCP server in Langflow

Add an MCP server using **STDIO**:

```text
Name:
spark_developer_tools

Command:
/home/spark0/Documents/Workspace/agent-system/mcp-server/.venv/bin/python

Arguments:
/home/spark0/Documents/Workspace/agent-system/mcp-server/server.py
```

Expected tools:

```text
list_files
read_file
write_file
create_directory
search_files
git_status
git_diff
run_tests
```

## 7. Create the Developer Agent

Create a blank Langflow named `Developer Agent`.

Conceptually:

```text
Chat Input --> Agent --> Chat Output
                ^
                |
        spark_developer_tools
```

Configure the Agent to use Ollama as its model provider and use `prompts/developer.md` as its instructions.

## 8. First validation project

```bash
cd ~/Documents/Workspace/projects
mkdir -p hello-agent
cd hello-agent
git init

cat > app.py <<'PY'
def add(a, b):
    return a + b
PY

cat > test_app.py <<'PY'
from app import add


def test_add():
    assert add(2, 3) == 5
PY

python3 -m pytest -q
git add .
git commit -m "Initial hello-agent project"
```

Then ask the Developer Agent:

```text
Work on project hello-agent.

Inspect the project first.
Add multiply(a, b) to app.py.
Add a pytest test verifying multiply(4, 5) == 20.
Run all tests.
If tests fail because of your changes, fix them.
Finally inspect git diff.
Do not modify unrelated files.
```

The desired loop is:

```text
inspect -> read -> edit -> test -> diagnose/fix -> test -> diff -> report
```

Do not add the full multi-agent hierarchy until this loop works reliably.

## 9. Add specialist agents

Add them in this order:

1. **Tester** — read/test/diff access; no source-code writes initially.
2. **Architect** — converts requirements into dependency-aware tasks with measurable acceptance criteria.
3. **Reviewer** — inspects diffs, tests, architecture, security, and maintainability.
4. **Supervisor** — routes work; it should not normally modify application code itself.

Recommended lifecycle:

```text
Requirements
  -> Architecture
  -> Task
  -> Developer
  -> Tester
      -> fail: Developer
      -> pass: Reviewer
          -> changes required: Developer -> Tester
          -> approved: next task
  -> Done
```

Keep implementation tasks small and sequential until the orchestration is stable.

## 10. Safety defaults

Initially allow:

```text
read project files
authorized project writes
pytest
git status
git diff
```

Keep these manual or approval-gated:

```text
sudo
apt/system package changes
git push
deployment
large file deletion
database migrations
Docker daemon access
arbitrary shell=True execution
```

Use Git commits and project-local state files as durable agent memory rather than relying only on conversation history.

## 11. Project-local agent state

For larger generated projects:

```text
project/
├── .agent/
│   ├── requirements.md
│   ├── architecture.md
│   ├── tasks.json
│   ├── status.json
│   ├── decisions.md
│   └── test_results.json
├── src/
├── tests/
└── README.md
```

## 12. Next upgrades

After the core loop is stable:

- exact text/patch editing instead of whole-file rewrites
- controlled Python/Node command allowlist
- Docker sandbox for generated applications
- Playwright browser testing
- GitHub branch/commit/PR automation
- structured task/status schemas
- specialized frontend/database/security agents
