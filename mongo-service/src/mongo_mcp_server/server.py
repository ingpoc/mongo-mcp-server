"""
Main MCP server implementation for MongoDB integration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, status
from mcp.server import Server
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
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# MongoDB connection
client = None
db = None
collection = None

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

# Create MCP Server
mcp_server = Server(name="stock-data-mcp-server")

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
            parameters={
                "query": {
                    "type": "object",
                    "description": "MongoDB query filter",
                    "required": True
                },
                "options": {
                    "type": "object",
                    "description": "MongoDB query options (projection, sort, limit)",
                    "required": False
                }
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

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint to verify server is running."""
    try:
        # Quick connection check
        if client and client.server_info():
            return {
                "message": "Stock Data MCP Server is running",
                "status": "healthy",
                "db_connected": True,
                "database": config.DB_NAME,
                "collection": config.COLLECTION_NAME,
                "pid": os.getpid()
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            content=json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "db_connected": False
            }),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    try:
        # Don't proceed if client is None
        if not client:
            raise Exception("MongoDB client not initialized")

        # Test MongoDB connection
        client.server_info()
        collection_count = collection.count_documents({})
        
        return {
            "status": "healthy",
            "db_connected": True,
            "db_name": config.DB_NAME,
            "collection": config.COLLECTION_NAME,
            "document_count": collection_count,
            "server_version": "0.1.0",
            "pid": os.getpid()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            content=json.dumps({
                "status": "unhealthy",
                "db_connected": False,
                "error": str(e)
            }),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )

async def run_mcp_server():
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    import uvicorn
    # Run both FastAPI and MCP server
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Create tasks for both servers
    fastapi_task = loop.create_task(
        uvicorn.run(
            app,
            host="127.0.0.1",  # Changed from 0.0.0.0 to localhost only
            port=config.PORT,
            log_level=config.LOG_LEVEL.lower()
        )
    )
    mcp_task = loop.create_task(run_mcp_server())
    
    try:
        # Run both servers concurrently
        loop.run_until_complete(asyncio.gather(fastapi_task, mcp_task))
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    finally:
        loop.close()