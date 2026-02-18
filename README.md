# Text-to-SQL Application

Convert natural language questions into SQL queries and execute them against SQLite databases. Built with FastAPI, Streamlit, and Ollama.

## Features

- Upload SQLite databases (.db, .sqlite, .sqlite3)
- Ask questions in plain Arabic,English or any other language 
- View database schema
- See generated SQL and results 

## Prerequisites

- Docker & Docker Compose
- Ollama running locally 

```bash
# Install and start Ollama
ollama pull qwen
ollama serve
```

## Quick Start

```bash
# Start the application
docker compose up -d

# Access the interfaces
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000/docs
```

## Usage

1. **Upload** your SQLite database file
2. **Ask** questions in natural language:
   - "Show me all customers from New York"
   - "What are the top 5 products by revenue?"
   - "Count orders by status"
3. **View** the generated SQL and results

## Docker Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f frontend
docker compose logs -f api

# Stop services
docker compose down

# Rebuild after changes
docker compose up -d --build
```

## Project Structure

```
├── front.py                 # Streamlit interface
├── main.py                  # FastAPI backend
├── config.py                # Configuration
├── docker-compose.yml       # Docker setup
└── src/
    ├── chat_bot_ui.py
    ├── clients.py
    └── UnifiedDatabaseLoader.py
```

## API Endpoints

- `POST /database/upload` - Upload database file
- `POST /database/query` - Query database with natural language
- `GET /database/{file_id}/schema` - Get database schema
- `DELETE /database/{file_id}` - Delete uploaded database
- `GET /health` - Health check

## Troubleshooting

**Cannot connect to Ollama:**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags
```

**Services not starting:**
```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f
```

**Query errors:**
- Check generated SQL in the UI
- Verify table/column names in schema viewer
- Review backend logs: `docker compose logs -f api`

## Development

Run locally without Docker:

```bash
# Backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (in separate terminal)
streamlit run frontend.py --server.port 8501
```

## Architecture

```
Streamlit Frontend (8501) → FastAPI Backend (8000) → Ollama (11434)
                                     ↓
                                 DuckDB
```

- **Frontend**: Handles file upload, user input, and displays results
- **Backend**: Manages databases, processes queries, coordinates LLM calls
- **Ollama**: Translates questions and generates SQL
- **DuckDB**: Executes SQL queries on SQLite databases