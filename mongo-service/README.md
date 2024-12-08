# MongoDB MCP Server

A Model Context Protocol (MCP) server implementation that provides Claude with read access to MongoDB collections. This server enables Claude to query and analyze MongoDB data through a standardized interface.

## Features

- MongoDB collection access via MCP resources
- Advanced query capabilities with MongoDB query syntax
- Pagination and result limiting
- Secure, read-only access to MongoDB data
- Full support for MongoDB query operators and options
- Built-in error handling and logging

## Quick Start

1. Install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Configure MongoDB connection in environment variables:
```bash
# Required environment variables
export MONGO_URI="mongodb://localhost:27017/"
export DB_NAME="stock_data"
export COLLECTION_NAME="detailed_financials"
```

3. Test the server:
```bash
python src/mongo_mcp_server/test_mcp_server.py
```

4. Configure Claude Desktop:
```json
{
    "mongo-service": {
        "command": "python",
        "args": [
            "-m",
            "src.mongo_mcp_server.server"
        ],
        "env": {
            "MONGO_URI": "mongodb://localhost:27017/",
            "DB_NAME": "stock_data",
            "COLLECTION_NAME": "detailed_financials",
            "PYTHONPATH": "path/to/mongo-service"
        }
    }
}
```

## Available Resources

### MongoDB Collection Resource
- **Name:** `mongo_detailed_financials`
- **URI:** `mongodb://detailed_financials`
- **Description:** Direct access to MongoDB collection
- **Capabilities:** Read-only access to documents

## Available Tools

### MongoDB Query Tool
- **Name:** `query_detailed_financials`
- **Description:** Execute MongoDB queries with options
- **Parameters:**
  ```json
  {
      "query": {
          "type": "object",
          "description": "MongoDB query filter",
          "required": true
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
                  "description": "Maximum documents (1-100)"
              }
          }
      }
  }
  ```

## Query Examples

1. Simple Query:
```python
query = {"symbol": "AAPL"}
options = {"limit": 5}
```

2. Advanced Query:
```python
query = {
    "financial_metrics.revenue": {"$gt": 1000000},
    "timestamp": {"$gte": "2023-01-01"}
}
options = {
    "projection": {"company_name": 1, "financial_metrics": 1},
    "sort": {"timestamp": -1},
    "limit": 10
}
```

## Error Handling

The server implements comprehensive error handling for:
- MongoDB connection issues
- Invalid queries
- Query execution errors
- Resource access problems
- Tool execution failures

All errors are logged and returned with descriptive messages.

## Logging

- Default log level: INFO
- Log format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Logs connection status, queries, and errors

## Security Features

- Read-only access to MongoDB
- Query parameter validation
- Resource access controls
- Rate limiting on queries
- Error message sanitization

## Best Practices

1. **Query Optimization:**
   - Use specific filters
   - Include necessary fields only
   - Implement pagination
   - Set reasonable limits

2. **Error Handling:**
   - Handle connection issues
   - Validate input parameters
   - Check query results
   - Process errors gracefully

3. **Resource Management:**
   - Close connections properly
   - Implement timeouts
   - Monitor query performance
   - Manage memory usage

## Development

The server is built using:
- Python 3.8+
- MCP Protocol
- FastAPI (optional HTTP interface)
- PyMongo

### Project Structure
```
mongo-service/
├── src/
│   └── mongo_mcp_server/
│       ├── server.py          # Main MCP server
│       ├── config.py          # Configuration
│       ├── resources/         # Resource implementations
│       └── tools/             # Tool implementations
├── tests/
├── requirements.txt
└── README.md
```

## Testing

Run the test suite:
```bash
python src/mongo_mcp_server/test_mcp_server.py
```

## Troubleshooting

1. Connection Issues:
   - Verify MongoDB is running
   - Check connection string
   - Confirm network access
   - Review server logs

2. Query Problems:
   - Validate query syntax
   - Check collection exists
   - Verify data types
   - Review query options

3. Claude Desktop Integration:
   - Check configuration
   - Verify PYTHONPATH
   - Review environment variables
   - Check server logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details