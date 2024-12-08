"""
Main MCP server implementation for MongoDB integration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, status
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, Resource
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Dict, Any, List, Optional, AsyncIterator
import asyncio
import json
import logging
import os
from . import config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
client = None
db = None
collection = None

# MCP Server instance
mcp_server = Server(name="stock-data-mcp-server")

def setup_mongodb():
    """Initialize MongoDB connection."""
    global client, db, collection
    
    try:
        # Initialize MongoDB client with connection timeout
        client = MongoClient(
            config.MONGO_URI,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        
        # Test the connection
        client.server_info()
        
        # Get database and collection
        db = client[config.DB_NAME]
        collection = db[config.COLLECTION_NAME]
        
        # Test collection access
        collection_count = collection.count_documents({})
        logger.info(
            f"Successfully connected to MongoDB. Collection '{config.COLLECTION_NAME}' "
            f"has {collection_count} documents"
        )
        return True
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events for FastAPI.
    """
    # Startup
    if not setup_mongodb():
        logger.error("Failed to setup MongoDB during startup")
    yield
    # Shutdown
    if client:
        logger.info("Closing MongoDB connection...")
        client.close()

app = FastAPI(
    title="Stock Data MCP Server",
    description="MCP Server providing access to financial stock data via MongoDB",
    version="0.1.0",
    lifespan=lifespan
)

# Define resources
@mcp_server.list_resources()
async def list_resources() -> List[Resource]:
    """List available MongoDB resources."""
    return [
        Resource(
            name=f"mongo_{config.COLLECTION_NAME}",
            uri=f"mongodb://{config.COLLECTION_NAME}",
            display_name=f"MongoDB {config.COLLECTION_NAME}",
            description=f"Access to MongoDB collection {config.COLLECTION_NAME}"
        )
    ]

@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    """Read content from MongoDB resource."""
    try:
        # Parse collection name from URI
        collection_name = uri.split('://')[-1]
        
        # Get documents with pagination
        cursor = collection.find().limit(10)
        documents = list(cursor)
        
        if not documents:
            return "No documents found in the collection."
        
        # Format documents for better readability
        formatted_docs = []
        for doc in documents:
            # Convert ObjectId to string for JSON serialization
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            formatted_docs.append(json.dumps(doc, indent=2))
        
        return "\n".join(formatted_docs)
            
    except Exception as e:
        error_msg = f"Error reading resource: {str(e)}"
        logger.error(error_msg)
        return error_msg

# Define tools
@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    """List available MongoDB query tools."""
    return [
        Tool(
            name=f"query_{config.COLLECTION_NAME}",
            display_name=f"Query {config.COLLECTION_NAME}",
            description=f"Query the {config.COLLECTION_NAME} collection in MongoDB",
            inputSchema={
                "type": "object",
                "title": "QueryParameters",
                "properties": {
                    "query": {
                        "type": "object",
                        "description": "MongoDB query filter"
                    },
                    "options": {
                        "type": "object",
                        "description": "MongoDB query options",
                        "properties": {
                            "projection": {
                                "type": "object",
                                "description": "Fields to include/exclude"
                            },
                            "sort": {
                                "type": "object",
                                "description": "Sort criteria"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of documents",
                                "minimum": 1,
                                "maximum": 100
                            }
                        }
                    }
                },
                "required": ["query"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> List[TextContent]:
    """Execute MongoDB query tool."""
    try:
        if not name.startswith("query_"):
            return [TextContent(text=f"Unknown tool: {name}")]
            
        query = arguments.get("query", {})
        options = arguments.get("options", {})
        
        # Validate options
        allowed_options = {'projection', 'sort', 'limit', 'skip'}
        filtered_options = {k: v for k, v in options.items() if k in allowed_options}
        
        # Execute the query
        cursor = collection.find(query, **filtered_options)
        if filtered_options.get('limit'):
            cursor = cursor.limit(filtered_options['limit'])
        
        results = list(cursor)
        
        if not results:
            return [TextContent(text="No matching documents found.")]
        
        # Format results
        formatted_results = []
        for doc in results:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            formatted_results.append(json.dumps(doc, indent=2))
        
        result_text = (
            f"Found {len(results)} matching documents:\n"
            + "\n".join(formatted_results)
        )
        return [TextContent(text=result_text)]
        
    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        logger.error(error_msg)
        return [TextContent(text=error_msg)]

async def run_mcp_server():
    """Run the MCP server using stdio transport."""
    logger.info("Starting MCP server...")
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("MCP server stdio transport initialized")
            init_options = InitializationOptions(
                server_name="stock-data-mcp-server",
                server_version="0.1.0",
                capabilities=mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
            logger.info("Starting MCP server with initialization options")
            await mcp_server.run(read_stream, write_stream, init_options)
    except Exception as e:
        logger.error(f"Error in MCP server: {e}")
        # Don't raise the exception - we want the task to stay alive

async def run_fastapi():
    """Run FastAPI server using uvicorn."""
    import uvicorn
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Run both servers when running as a script."""
    if os.environ.get("RUN_HTTP", "").lower() == "true":
        # Run both MCP and HTTP servers
        await asyncio.gather(
            run_mcp_server(),
            run_fastapi()
        )
    else:
        # Run only MCP server
        await run_mcp_server()

if __name__ == "__main__":
    asyncio.run(main())