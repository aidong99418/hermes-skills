---
name: fastmcp
description: >
  Build, serve, or connect to MCP (Model Context Protocol) servers/tools. Use this skill
  whenever the user wants to create an MCP server, expose Python functions as MCP tools,
  build a tool server for an LLM, connect to an existing MCP server, set up an MCP client,
  add interactive UI components (Apps) to tools, or integrate with the Prefect Horizon
  MCP gateway. Also use when the user mentions FastMCP, MCP server, MCP client, MCP tools,
  model context protocol, or wants to build anything involving LLM tool calling. Not needed
  for general Python coding or non-MCP integrations.
---

# FastMCP

FastMCP is a Python framework for building, serving, and connecting to [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers. It wraps Python functions into MCP-compliant tools, resources, and prompts with automatic schema generation, validation, and documentation. The framework has three pillars: **Servers** (expose tools to LLMs), **Clients** (connect to any MCP server), and **Apps** (interactive UIs rendered in conversation).

Full docs: [gofastmcp.com](https://gofastmcp.com)

## Installation

We recommend `uv`:

```bash
uv pip install fastmcp
```

Or with pip:

```bash
pip install fastmcp
```

> [!NOTE]
> If `import fastmcp` fails right after a `pip` upgrade from FastMCP 3.2 or earlier, run `pip install --force-reinstall fastmcp`. This does not affect `uv` installs.

---

## Quick Start

### Minimal MCP Server

```python
from fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

if __name__ == "__main__":
    mcp.run()
```

The decorator automatically generates the tool schema, docstring becomes the description, and type hints drive validation.

### Run the Server

```bash
# stdio transport (for local/CLI usage)
python your_server.py

# HTTP/SSE transport (for remote clients)
mcp dev your_server.py
```

---

## Examples

### 1. Tool with Dependencies

Tools can accept and return complex types. Dependencies (DB connections, API clients, etc.) are injected via the `context` object.

```python
from fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP("My Server")

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

@mcp.tool
def search_documents(query: str, limit: int = 5) -> list[SearchResult]:
    """Search internal documentation by keyword."""
    results = docs_db.search(query, limit=limit)
    return [SearchResult(title=r.title, url=r.url, snippet=r.snippet) for r in results]
```

### 2. Resources (Read-only data)

Resources expose data to LLMs without tool calling overhead.

```python
@mcp.resource("config://app")
def get_config() -> dict:
    """Expose application config as a resource."""
    return {"version": "1.0", "debug": False}

# Template resources with path parameters
@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> dict:
    return db.get_profile(user_id)
```

### 3. Prompts (Reusable prompt templates)

```python
@mcp.prompt
def code_review(repo: str, pr: int) -> str:
    """Generate a code review prompt for a pull request."""
    return f"""Review PR #{pr} in {repo}. Focus on:
- Security vulnerabilities
- Performance regressions
- Test coverage
"""
```

### 4. MCP Client (connecting to servers)

```python
from fastmcp import FastMCP

mcp = FastMCP("Client App")

# Connect to a local server via stdio
@mcp.tool
async def call_remote_tool(arg: str) -> str:
    async with mcp.client as client:
        result = await client.call_tool("remote_tool_name", {"arg": arg})
        return result
```

### 5. Apps (Interactive UI in conversation)

Apps render rich, interactive UI components directly in the LLM conversation.

```python
from fastmcp import FastMCP

mcp = FastMCP("App Demo")

@mcp.tool
@mcp.app
def data_explorer(data: list[dict]) -> str:
    """Interactive data explorer with charts and filters."""
    return {
        "type": "table",
        "data": data,
        "columns": ["name", "value", "timestamp"],
        "sortable": True,
        "filterable": True,
    }
```

---

## Scenarios

Use FastMCP when you want to:

- **Build an MCP server** from Python functions — decorate with `@mcp.tool`, `@mcp.resource`, `@mcp.prompt`, and run with `mcp.run()`.
- **Expose domain-specific tools to an LLM** — file system ops, database queries, API calls, code execution, etc.
- **Create a tool registry** — centralize and version-control the tools available to agents.
- **Connect to an existing MCP server** — use `FastMCP.client` to call remote tools programmatically.
- **Add interactive UIs** — use `@mcp.app` to render tables, forms, charts, and other components in the conversation.
- **Remote server deployment** — serve over HTTP/SSE so clients don't need local stdio access.
- **Integrate with Prefect Horizon** — deploy FastMCP servers with SSO, RBAC, audit logs, and observability for enterprise stacks.

---

## Notes & Caveats

- **Transports**: FastMCP supports `stdio` (local/CLI), `http`/`sse` (remote). Choose the transport that matches your client setup.
- **Schema generation is automatic** — type hints + docstrings are converted to JSON schemas. Keep type hints precise (use Pydantic models for complex inputs/outputs).
- **Async is supported** — all tool/resource functions can be `async def`. FastMCP handles the event loop.
- **Context injection**: Use the `Context` parameter to access server state, logging, and dependency injection without global singletons.
- **Apps require client support** — not all MCP clients render interactive App components. Check your client's capabilities.
- **Import after upgrade**: If `import fastmcp` fails post-upgrade from v3.2 or earlier via pip, force-reinstall: `pip install --force-reinstall fastmcp`.
- **Docs**: Full API reference and advanced patterns at [gofastmcp.com](https://gofastmcp.com). LLM-friendly docs also available as [llms.txt](https://gofastmcp.com/llms.txt).
