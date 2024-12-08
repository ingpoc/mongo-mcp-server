"""
Main MCP server implementation for MongoDB integration.
"""

from contextlib import asynccontextmanager
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, Resource
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime
import logging
from . import config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MongoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB documents."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class MongoMCPServer:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.is_connected = False
        self.mcp_server = Server(name="stock-data-mcp-server")
        self._setup_mcp_handlers()

    def _setup_mcp_handlers(self):
        """Set up MCP server handlers."""
        # Create decorators for each handler
        @self.mcp_server.list_resources()
        async def list_resources() -> List[Resource]:
            return await self.list_resources()

        @self.mcp_server.read_resource()
        async def read_resource(uri: str) -> str:
            return await self.read_resource(uri)

        @self.mcp_server.list_tools()
        async def list_tools() -> List[Tool]:
            return await self.list_tools()

        @self.mcp_server.call_tool()
        async def call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> List[TextContent]:
            return await self.call_tool(name, arguments)

    def setup_mongodb(self) -> bool:
        """Initialize MongoDB connection."""
        try:
            # Initialize MongoDB client with connection timeout
            self.client = MongoClient(
                config.MONGO_URI,
                serverSelectionTimeoutMS=5000  # 5 second timeout
            )
            
            # Test the connection
            self.client.server_info()
            
            # Get database and collection
            self.db = self.client[config.DB_NAME]
            self.collection = self.db[config.COLLECTION_NAME]
            
            # Test collection access
            collection_count = self.collection.count_documents({})
            logger.info(
                f"Successfully connected to MongoDB. Collection '{config.COLLECTION_NAME}' "
                f"has {collection_count} documents"
            )
            self.is_connected = True
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.is_connected = False
            return False

    async def list_resources(self) -> List[Resource]:
        """List available MongoDB resources."""
        return [
            Resource(
                name=f"mongo_{config.COLLECTION_NAME}",
                uri=f"mongodb://{config.COLLECTION_NAME}",
                display_name=f"MongoDB {config.COLLECTION_NAME}",
                description=f"Access to MongoDB collection {config.COLLECTION_NAME}"
            )
        ]

    async def read_resource(self, uri: str) -> str:
        """Read content from MongoDB resource."""
        try:
            if not self.is_connected:
                return "MongoDB connection not initialized"

            # Parse collection name from URI
            collection_name = uri.split('://')[-1]
            
            # Get documents with pagination
            cursor = self.collection.find().limit(10)
            documents = list(cursor)
            
            if not documents:
                return "No documents found in the collection."
            
            # Format documents for better readability
            formatted_docs = []
            for doc in documents:
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                formatted_docs.append(json.dumps(doc, indent=2, cls=MongoJSONEncoder))
            
            return "\n".join(formatted_docs)
                
        except Exception as e:
            error_msg = f"Error reading resource: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def list_tools(self) -> List[Tool]:
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

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]]) -> List[TextContent]:
        """Execute MongoDB query tool."""
        try:
            if not self.is_connected:
                return [TextContent(type="text", text="MongoDB connection not initialized")]

            if not name.startswith("query_"):
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
                
            query = arguments.get("query", {})
            options = arguments.get("options", {})
            
            # Validate options
            allowed_options = {'projection', 'sort', 'limit', 'skip'}
            filtered_options = {k: v for k, v in options.items() if k in allowed_options}
            
            # Execute the query
            cursor = self.collection.find(query)
            if filtered_options.get('limit'):
                cursor = cursor.limit(filtered_options['limit'])
            if filtered_options.get('sort'):
                cursor = cursor.sort(list(filtered_options['sort'].items()))
            if filtered_options.get('projection'):
                cursor = cursor.project(filtered_options['projection'])
            
            results = list(cursor)
            
            if not results:
                return [TextContent(type="text", text="No matching documents found.")]
            
            # Format results
            formatted_results = []
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                formatted_results.append(json.dumps(doc, indent=2, cls=MongoJSONEncoder))
            
            result_text = (
                f"Found {len(results)} matching documents:\n"
                + "\n".join(formatted_results)
            )
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    async def run(self):
        """Run the MCP server using stdio transport."""
        logger.info("Starting MCP server...")
        try:
            # Initialize MongoDB connection first
            if not self.setup_mongodb():
                logger.error("Failed to initialize MongoDB connection")
                return

            async with stdio_server() as (read_stream, write_stream):
                logger.info("MCP server stdio transport initialized")
                init_options = InitializationOptions(
                    server_name="stock-data-mcp-server",
                    server_version="0.1.0",
                    capabilities=self.mcp_server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
                logger.info("Starting MCP server with initialization options")
                await self.mcp_server.run(read_stream, write_stream, init_options)
        except Exception as e:
            logger.error(f"Error in MCP server: {e}")

async def main():
    """Run the server when running as a script."""
    server = MongoMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())