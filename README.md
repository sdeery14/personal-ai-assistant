# Personal AI Assistant - Core Streaming Chat API

A FastAPI-based streaming chat API that interfaces with OpenAI's Agents SDK for real-time LLM responses.

## Features

- **Real-time Streaming**: Server-Sent Events (SSE) for live response streaming
- **Correlation IDs**: Request tracking across the entire request lifecycle
- **Structured Logging**: JSON-formatted logs with automatic sensitive data redaction
- **Error Handling**: User-friendly error messages following the constitutional UX pattern
- **Input Validation**: Pydantic-based request validation with clear error messages

## Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- OpenAI API key with access to chat models

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd personal-ai-assistant

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Required: OPENAI_API_KEY=sk-your-key-here
```

**Environment Variables:**

| Variable          | Required | Default | Description                                 |
| ----------------- | -------- | ------- | ------------------------------------------- |
| `OPENAI_API_KEY`  | ✅ Yes   | -       | Your OpenAI API key                         |
| `OPENAI_MODEL`    | No       | `gpt-4` | Model to use for completions                |
| `MAX_TOKENS`      | No       | `2000`  | Maximum tokens per response                 |
| `TIMEOUT_SECONDS` | No       | `30`    | Request timeout in seconds                  |
| `LOG_LEVEL`       | No       | `INFO`  | Logging level (DEBUG, INFO, WARNING, ERROR) |

### 3. Run the Server

```bash
# Development mode with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t personal-ai-assistant .

# Run the container
docker run -d \
  --name chat-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -e OPENAI_MODEL=gpt-4 \
  personal-ai-assistant
```

### Using Docker Compose (optional)

```yaml
# docker-compose.yml
version: "3.8"
services:
  chat-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=gpt-4
    restart: unless-stopped
```

```bash
docker-compose up -d
```

## API Reference

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-28T12:00:00.000000+00:00"
}
```

### Chat (Streaming)

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?"}'
```

**Request Body:**

```json
{
  "message": "Your question here",
  "model": "gpt-4", // Optional: override default model
  "max_tokens": 1000 // Optional: override default max tokens
}
```

**Response (SSE Stream):**

```
data: {"content": "The", "sequence": 0, "is_final": false, "correlation_id": "abc-123"}

data: {"content": " answer", "sequence": 1, "is_final": false, "correlation_id": "abc-123"}

data: {"content": " is", "sequence": 2, "is_final": false, "correlation_id": "abc-123"}

data: {"content": " 4", "sequence": 3, "is_final": false, "correlation_id": "abc-123"}

data: {"content": "", "sequence": 4, "is_final": true, "correlation_id": "abc-123"}
```

### Error Response

```json
{
  "error": "Validation error",
  "detail": "Field 'body.message': String should have at least 1 character",
  "correlation_id": "error-tracking-id"
}
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/integration/test_chat_endpoint.py -v
```

## Project Structure

```
personal-ai-assistant/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── middleware.py      # Correlation ID middleware
│   │   └── routes.py          # API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request.py         # Request validation models
│   │   └── response.py        # Response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chat_service.py    # OpenAI Agents SDK integration
│   │   └── logging_service.py # Structured logging config
│   ├── config.py              # Application settings
│   └── main.py                # FastAPI app initialization
├── tests/
│   ├── integration/           # API integration tests
│   └── unit/                  # Unit tests
├── .env.example               # Environment template
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Troubleshooting

### "OPENAI_API_KEY is required"

Make sure your `.env` file exists and contains a valid API key:

```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### Streaming not working

1. Ensure you're using `curl -N` (unbuffered) or a streaming-capable HTTP client
2. Check that your proxy/load balancer supports SSE
3. Verify the response headers include `Content-Type: text/event-stream`

### Docker container won't start

1. Check logs: `docker logs chat-api`
2. Verify environment variables are passed correctly
3. Ensure port 8000 is not in use

### Tests failing

1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Run from project root directory
3. Check Python version: `python --version` (requires 3.11+)

## License

MIT License - See LICENSE file for details.
