from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_connection():
    """Test connecting to the MCP server."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command=".venv/Scripts/python",  # Use Python from venv
        args=["-m", "src.mongo_mcp_server.server"],  # Run as module
        env=None  # Use current environment
    )

    try:
        # Create stdio connection
        async with stdio_client(server_params) as (read, write):
            # Create client session
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                logger.info("Successfully connected to MCP server")

                # List available resources
                resources = await session.list_resources()
                logger.info(f"Available resources: {resources}")

                # List available tools
                tools = await session.list_tools()
                logger.info(f"Available tools: {tools}")

    except Exception as e:
        logger.error(f"Error connecting to MCP server: {e}")
        raise  # Re-raise to see full traceback

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())