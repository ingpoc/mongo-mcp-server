import mcp
import inspect

# Print MCP version
print(f"MCP Version: {mcp.__version__ if hasattr(mcp, '__version__') else 'Unknown'}")

# Print MCP package structure
print("\nMCP Package Structure:")
for name, obj in inspect.getmembers(mcp):
    if not name.startswith('_'):  # Skip private attributes
        print(f"{name}: {type(obj)}")

# Try to import specific modules
print("\nTrying specific imports:")
try:
    import mcp.server
    print("mcp.server contents:", dir(mcp.server))
except ImportError as e:
    print("Failed to import mcp.server:", e)

try:
    import mcp.resources
    print("mcp.resources contents:", dir(mcp.resources))
except ImportError as e:
    print("Failed to import mcp.resources:", e)