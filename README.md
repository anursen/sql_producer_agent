# SQL Producer Agent

An intelligent SQL query assistant powered by LangChain and GPT-4 that helps users generate and execute SQL queries through natural language interactions.

## Features

- Natural language to SQL query conversion
- Interactive CLI and Web interface
- Support for multiple database schemas
- Real-time query execution and validation
- Performance evaluation against ground truth data
- Memory persistence for conversation context
- Docker and Kubernetes deployment support

## Prerequisites

- Python 3.9+
- Docker (optional)
- Kubernetes (optional)
- OpenAI API key

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
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

### CLI Interface

Run the main application:
```bash
python main.py
```

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
├── app.py              # FastAPI web application
├── config.py           # Configuration management
├── main.py            # CLI application
├── requirements.txt    # Project dependencies
├── docker-compose.yml  # Docker compose configuration
├── k8s/               # Kubernetes manifests
├── services/          # Core services
├── tools/             # Utility tools
├── static/            # Web static files
└── templates/         # HTML templates
```

## Configuration

The application can be configured through:
- Environment variables
- config.yaml file
- CLI arguments

Key configuration options:
- Database settings
- LLM model parameters
- API endpoints
- Logging preferences

## Features in Detail

### Schema Analysis
- Automatic database schema detection
- Table relationship mapping
- Index analysis

### Query Generation
- Natural language processing
- Context-aware query generation
- SQL syntax validation

### Memory Management
- Conversation persistence
- Context maintenance
- MongoDB integration for storage

### Performance Evaluation
- Ground truth comparison
- Similarity scoring
- Error analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## Acknowledgments

- LangChain
- OpenAI
- FastAPI
- SQLAlchemy
