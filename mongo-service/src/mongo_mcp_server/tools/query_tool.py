"""
MongoDB Query Tool implementation.
"""

from mcp.types import Tool, TextContent
from pymongo.database import Database
from typing import Dict, Any, List, Set
import json
import logging

logger = logging.getLogger(__name__)

class MongoQueryTool(Tool):
    # Set of allowed MongoDB query options
    ALLOWED_OPTIONS: Set[str] = {'projection', 'sort', 'limit', 'skip'}

    def __init__(self, collection_name: str, db: Database):
        """
        Initialize MongoDB Query Tool.
        
        Args:
            collection_name (str): Name of the MongoDB collection
            db (Database): MongoDB database instance
        """
        super().__init__(
            name=f"query_{collection_name}",  # Required: Unique name for the tool
            display_name=f"Query {collection_name}",  # Optional: Human-readable name
            description=f"Query the {collection_name} collection in MongoDB",  # Optional: Description
            parameters={  # Required: Define the parameters this tool accepts
                "query": {
                    "type": "object",
                    "description": "MongoDB query filter",
                    "required": True
                },
                "options": {
                    "type": "object",
                    "description": "MongoDB query options (projection, sort, limit, skip)",
                    "required": False,
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
                            "description": "Maximum number of documents to return",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "skip": {
                            "type": "integer",
                            "description": "Number of documents to skip",
                            "minimum": 0
                        }
                    }
                }
            }
        )
        self.collection = db[collection_name]
        self.collection_name = collection_name

    def _validate_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and filter MongoDB query options.
        
        Args:
            options (Dict[str, Any]): Raw query options
            
        Returns:
            Dict[str, Any]: Validated and filtered options
        """
        validated = {}
        for key, value in options.items():
            if key in self.ALLOWED_OPTIONS:
                if key == 'limit' and (not isinstance(value, int) or value > 100):
                    validated[key] = 100  # Cap limit at 100
                elif key == 'skip' and (not isinstance(value, int) or value < 0):
                    validated[key] = 0  # Ensure skip is non-negative
                else:
                    validated[key] = value
        return validated

    async def execute(self, params: Dict[str, Any]) -> List[TextContent]:
        """
        Execute a query on the MongoDB collection.
        
        Args:
            params (Dict[str, Any]): {
                "query": MongoDB query filter,
                "options": MongoDB query options (optional)
            }
            
        Returns:
            List[TextContent]: List of text content representing the query results
        """
        try:
            query = params.get("query", {})
            options = self._validate_options(params.get("options", {}))
            
            # Get total count for the query
            total_count = self.collection.count_documents(query)
            
            # Execute the query with options
            cursor = self.collection.find(query)
            
            # Apply options
            if options.get('projection'):
                cursor = cursor.projection(options['projection'])
            if options.get('sort'):
                cursor = cursor.sort(list(options['sort'].items()))
            if options.get('skip'):
                cursor = cursor.skip(options['skip'])
            if options.get('limit'):
                cursor = cursor.limit(options['limit'])
            
            # Get results
            results = list(cursor)
            
            if not results:
                return [TextContent(text="No matching documents found.")]
            
            # Format results
            formatted_results = []
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                formatted_results.append(json.dumps(doc, indent=2))
            
            # Prepare result text
            result_text = (
                f"Found {total_count} total matching documents.\n"
                f"Showing {len(results)} document(s):\n"
                + "\n".join(formatted_results)
            )
            return [TextContent(text=result_text)]
            
        except Exception as e:
            error_msg = f"Error executing query on {self.collection_name}: {str(e)}"
            logger.error(error_msg)
            return [TextContent(text=error_msg)]