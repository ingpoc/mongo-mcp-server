"""
MongoDB Collection Resource implementation.
"""

from mcp.types import Resource, TextContent
from pymongo.database import Database
from typing import Dict, Any, Optional, List
import json
import logging

logger = logging.getLogger(__name__)

class MongoCollectionResource(Resource):
    def __init__(self, collection_name: str, db: Database):
        """
        Initialize MongoDB Collection Resource.
        
        Args:
            collection_name (str): Name of the MongoDB collection
            db (Database): MongoDB database instance
        """
        # Initialize base Resource with required fields
        super().__init__(
            name=f"mongo_{collection_name}",  # Required: Unique name for the resource
            uri=f"mongodb://{collection_name}",  # Required: URI for the resource
            display_name=f"MongoDB {collection_name}",  # Optional: Human-readable name
            description=f"Access to MongoDB collection {collection_name}"  # Optional: Description
        )
        self.collection = db[collection_name]
        self.collection_name = collection_name

    async def get_content(
        self, 
        query: Optional[Dict[str, Any]] = None, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[TextContent]:
        """
        Get content from MongoDB collection.
        
        Args:
            query (Dict[str, Any], optional): MongoDB query to filter documents
            skip (int): Number of documents to skip (default: 0)
            limit (int): Maximum number of documents to return (default: 10)
            
        Returns:
            List[TextContent]: List of text content representing the documents
        """
        if query is None:
            query = {}
        
        try:
            # Get total count for the query
            total_count = self.collection.count_documents(query)
            
            # Fetch documents with pagination
            cursor = self.collection.find(query).skip(skip).limit(limit)
            documents = list(cursor)
            
            if not documents:
                return [TextContent(text="No documents found matching the query.")]
            
            # Format documents for better readability
            formatted_docs = []
            for doc in documents:
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                formatted_docs.append(json.dumps(doc, indent=2))
            
            # Prepare result text with pagination info
            result_text = (
                f"Found {total_count} total documents matching query.\n"
                f"Showing documents {skip + 1}-{min(skip + len(documents), total_count)}:\n"
                + "\n".join(formatted_docs)
            )
            return [TextContent(text=result_text)]
            
        except Exception as e:
            error_msg = f"Error retrieving documents from {self.collection_name}: {str(e)}"
            logger.error(error_msg)
            return [TextContent(text=error_msg)]