"""
Stock Data MCP Server package.
"""

__version__ = "0.1.0"

# These will be populated when server.py is imported
app = None
mcp_server = None
run_mcp_server = None

# Import at the end to avoid circular imports
from .server import app, mcp_server, run_mcp_server  # noqa: E402

__all__ = [
    "app",
    "mcp_server",
    "run_mcp_server",
    "__version__"
]