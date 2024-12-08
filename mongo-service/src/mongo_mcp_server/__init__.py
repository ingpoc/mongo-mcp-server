"""
Stock Data MCP Server package.
"""

__version__ = "0.1.0"

from .server import MongoMCPServer, main

__all__ = [
    "MongoMCPServer",
    "main",
    "__version__"
]