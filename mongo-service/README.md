# Stock Data MongoDB MCP Server

This is a specialized Model Context Protocol (MCP) server implementation that provides AI models access to financial stock data stored in MongoDB. This README is designed to help AI models understand the project and effectively work with the codebase.

## Project Purpose
Provide AI models with structured access to financial stock data through a standardized MCP interface, enabling them to:
- Query financial metrics and company data
- Process historical financial information
- Analyze stock market data patterns

## Data Structure
The MongoDB collection contains financial records with this structure:
```json
{
    "_id": ObjectId,
    "company_name": "String",
    "symbol": "String",
    "financial_metrics": {
        // Financial metrics data
    },
    "timestamp": "YYYY-MM-DD"
}
```

## Server Configuration
- MongoDB URI: mongodb://localhost:27017/
- Database: stock_data
- Collection: detailed_financials
- HTTP Server: http://127.0.0.1:8000
- Available Documents: 1888 financial records

## Available Tools
1. Query Tool
   - Name: query_detailed_financials
   - Purpose: Execute MongoDB queries
   - Parameters:
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
             "required": false
         }
     }
     ```

## Available Resources
1. MongoDB Collection Resource
   - Name: mongo_detailed_financials
   - URI: mongodb://detailed_financials
   - Purpose: Direct access to financial data

## Important Notes for AI Models

### Data Access Patterns
1. For single document queries:
   ```python
   # Use the query tool with specific filters
   query = {"symbol": "AAPL"}
   ```

2. For bulk data access:
   ```python
   # Use the collection resource with pagination
   limit = 10
   skip = 0
   ```

### Query Best Practices
1. Always include filters to limit result sets
2. Use projection to select only needed fields
3. Implement pagination for large result sets
4. Handle null values in financial metrics

### Error Handling
1. Handle MongoDB connection errors
2. Validate query parameters
3. Check for empty result sets
4. Process ObjectId conversions

### Performance Considerations
1. Queries are limited to 100 documents by default
2. Use skip/limit for pagination
3. Avoid full collection scans
4. Consider query timeout settings

## Health Check Example
```bash
GET http://127.0.0.1:8000/health

Response:
{
    "status": "healthy",
    "db_connected": true,
    "db_name": "stock_data",
    "collection": "detailed_financials",
    "document_count": 1888
}
```

## For AI Model Reference
1. The server implements current MCP protocol standards
2. All MongoDB queries are automatically validated
3. Results are returned as TextContent objects
4. Financial data is read-only

## Code Organization
```
mongo-service/
├── src/mongo_mcp_server/
│   ├── server.py          # Main server implementation
│   ├── config.py          # Configuration settings
│   └── __init__.py        # Package initialization
```

## Additional Context for AI Models
- This is a read-only financial data service
- Data is structured for AI analysis
- Query results are paginated and formatted
- Error messages provide clear context
- Health checks verify data availability

This README is designed to be read in conjunction with project_knowledge.txt and project_instructions.txt for complete MCP development context.