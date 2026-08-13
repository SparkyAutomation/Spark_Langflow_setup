from pathlib import Path
import subprocess

from mcp.server import MCPServer


mcp = MCPServer("Spark Developer Tools")

WORKSPACE_ROOT = Path(
    "/home/spark0/Documents/Workspace/projects"
).resolve()


def safe_path(relative_path: str) -> Path:
    """Resolve a workspace path while preventing directory traversal."""
    candidate = (WORKSPACE_ROOT / relative_path).resolve()

    if candidate != WORKSPACE_ROOT and WORKSPACE_ROOT not in candidate.parents:
        raise ValueError("Access outside the project workspace is prohibited.")

    return candidate


@mcp.tool()
def list_files(path: str = ".") -> str:
    """List files and directories inside the coding workspace."""
    target = safe_path(path)

    if not target.exists():
        return f"Path does not exist: {path}"

    if not target.is_dir():
        return f"Not a directory: {path}"

    entries = []

    for item in sorted(target.iterdir()):
        kind = "DIR" if item.is_dir() else "FILE"
        relative = item.relative_to(WORKSPACE_ROOT)
        entries.append(f"{kind}: {relative}")

    return "\n".join(entries) or "Directory is empty."


@mcp.tool()
def read_file(path: str) -> str:
    """Read a UTF-8 text file from the coding workspace."""
    target = safe_path(path)

    if not target.exists():
        return f"File does not exist: {path}"

    if not target.is_file():
        return f"Not a file: {path}"

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "File is not UTF-8 text."


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Create or overwrite a UTF-8 text file inside the coding workspace."""
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote file: {target.relative_to(WORKSPACE_ROOT)}"


@mcp.tool()
def create_directory(path: str) -> str:
    """Create a directory inside the coding workspace."""
    target = safe_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return f"Created directory: {target.relative_to(WORKSPACE_ROOT)}"


@mcp.tool()
def search_files(query: str, path: str = ".") -> str:
    """Search UTF-8-readable files for a case-insensitive string."""
    target = safe_path(path)

    if not target.exists():
        return f"Path does not exist: {path}"

    matches = []

    for file_path in target.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if query.lower() in line.lower():
                relative = file_path.relative_to(WORKSPACE_ROOT)
                matches.append(f"{relative}:{line_number}: {line.strip()}")

        if len(matches) >= 100:
            break

    return "\n".join(matches[:100]) or "No matches found."


@mcp.tool()
def git_status(project: str) -> str:
    """Run git status --short inside a project."""
    cwd = safe_path(project)

    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return result.stderr

    return result.stdout or "Working tree clean."


@mcp.tool()
def git_diff(project: str) -> str:
    """Show uncommitted Git changes for a project."""
    cwd = safe_path(project)

    result = subprocess.run(
        ["git", "diff"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return result.stderr

    return result.stdout or "No differences."


@mcp.tool()
def run_tests(project: str) -> str:
    """Run pytest inside a project. Only pytest is allowed by this tool."""
    cwd = safe_path(project)

    result = subprocess.run(
        ["python", "-m", "pytest", "-q"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = result.stdout

    if result.stderr:
        output += "\nSTDERR:\n" + result.stderr

    output += f"\nExit code: {result.returncode}"
    return output


if __name__ == "__main__":
    mcp.run()
