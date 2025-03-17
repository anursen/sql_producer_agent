# SQL Producer Agent

An intelligent SQL query assistant powered by LangChain and GPT that helps users generate and execute SQL queries through natural language interactions.

## Features

- Natural language to SQL query conversion with contextual understanding
- Multi-database support (SQLite, MongoDB, MySQL, PostgreSQL)
- Interactive CLI and Web interface
- Real-time query execution and validation
- Performance evaluation against ground truth data
- Memory persistence for conversation context
- Built-in data dictionary and schema analysis tools
- Docker and Kubernetes deployment support

## Prerequisites

- Python 3.9+
- OpenAI API key
- Docker (optional)
- Database system (SQLite by default)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sql_producer_agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Add to .env file
OPENAI_API_KEY=your_api_key
ENVIRONMENT=development
```

## Usage

### CLI Interface

Launch the CLI application:
```bash
python main.py
```

Available commands:
- Execute queries
- Toggle debug mode
- Toggle SQL-only mode
- Show database schema
- Run performance evaluation
- Get help

### Web Interface

Start the web server:
```bash
python app.py
```
Access the web interface at `http://localhost:8000`

### Docker Deployment

Build and run using Docker Compose:
```bash
docker-compose up -d
```

Services included:
- PostgreSQL database
- pgAdmin interface
- MongoDB (for memory persistence)
- Web application

### Kubernetes Deployment

1. Create namespace:
```bash
kubectl apply -f k8s/namespace.yaml
```

2. Deploy components:
```bash
kubectl apply -f k8s/
```

## Project Structure

```
sql_producer_agent/
├── app.py                  # FastAPI web application
├── config.py              # Configuration management
├── config.yaml           # Configuration settings
├── main.py              # CLI application
├── requirements.txt     # Project dependencies
├── docker-compose.yml  # Docker configuration
├── services/          # Core services
│   ├── agents/       # LLM agents
│   └── llm_service.py # LLM service
├── tools/            # Utility tools
│   ├── execute_sql.py
│   ├── get_schema.py
│   └── query_data_dictionary.py
├── utils/           # Helper utilities
├── static/         # Web static files
└── templates/      # HTML templates
```

## Configuration

The application is configured through `config.yaml` and supports:

- LLM settings (model, temperature, tokens)
- Database connections (multiple types)
- API settings
- Evaluation parameters
- Tool configurations
- System messages
- Logging preferences

## Available Tools

1. Schema Analysis (`get_schema`)
   - Database structure inspection
   - Relationship mapping
   - Index analysis

2. SQL Execution (`execute_sql_query`)
   - Query execution
   - Result formatting
   - Error handling

3. Data Dictionary (`get_db_field_definition`)
   - Column descriptions
   - Data type information
   - Table relationships

## Performance Evaluation

The system includes a comprehensive evaluation framework:
- Ground truth comparison
- Similarity scoring
- Error analysis
- Performance metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker.
