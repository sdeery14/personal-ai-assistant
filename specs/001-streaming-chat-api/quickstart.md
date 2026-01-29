# Quickstart: Core Streaming Chat API

**Feature**: 001 - Core Streaming Chat API
**Purpose**: Get the chat API running locally in under 5 minutes
**Target Audience**: Developers setting up for the first time

---

## Prerequisites

- Docker installed and running
- OpenAI API key (get one at https://platform.openai.com/api-keys)
- Git (to clone the repository)
- curl or httpie for testing (optional but recommended)

---

## 1. Setup Environment

Create `.env` file in repository root:

```bash
# Copy example and fill in your API key
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4
MAX_TOKENS=2000
TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

⚠️ **Security Note**: Never commit `.env` to version control. It's in `.gitignore` by default.

---

## 2. Build and Run

### Option A: Docker (Recommended)

```bash
# Build the image
docker build -t chat-api .

# Run the container
docker run -p 8000:8000 --env-file .env chat-api
```

**With live reload** (for development):

```bash
docker run -p 8000:8000 --env-file .env -v $(pwd)/src:/app/src chat-api
```

### Option B: Local Python (Alternative)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables and run
export $(cat .env | xargs)  # On Windows: set them manually or use python-dotenv
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 3. Verify It's Running

**Health Check**:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T14:32:10.123456Z"
}
```

---

## 4. Send Your First Message

### Using curl

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

### Using httpie (cleaner syntax)

```bash
http POST http://localhost:8000/chat message="What is the capital of France?"
```

### Expected Response

You'll see a **stream** of Server-Sent Events (SSE):

```
data: {"content":"The","sequence":0,"is_final":false,"correlation_id":"550e8400-e29b-41d4-a716-446655440000"}

data: {"content":" capital","sequence":1,"is_final":false,"correlation_id":"550e8400-e29b-41d4-a716-446655440000"}

data: {"content":" of France is Paris.","sequence":2,"is_final":true,"correlation_id":"550e8400-e29b-41d4-a716-446655440000"}
```

---

## 5. Check the Logs

Logs are written to **stdout** in structured JSON format:

```bash
# If using Docker
docker logs <container-id>

# If running locally
# Logs appear in terminal where uvicorn is running
```

Example log entry:

```json
{
  "event": "request_received",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/chat",
  "timestamp": "2026-01-28T14:32:10.123456Z",
  "log_level": "INFO"
}
```

---

## 6. Test Error Handling

**Empty message** (validation error):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": ""}'
```

Expected: `400 Bad Request` with error details

**Invalid model**:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "model": "invalid-model"}'
```

Expected: `400 Bad Request` with allowed models list

---

## 7. Run Tests

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests (requires API key in .env)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=src --cov-report=html
```

**View coverage report**: Open `htmlcov/index.html` in browser

---

## Common Issues

### Issue: "OpenAI API key not found"

**Symptom**: Error on first request
**Solution**: Verify `.env` file exists and contains `OPENAI_API_KEY=sk-...`

### Issue: "Module not found" errors

**Symptom**: Import errors when running tests
**Solution**: Install dev dependencies: `pip install -r requirements.txt`

### Issue: Docker container won't start

**Symptom**: Port 8000 already in use
**Solution**:

```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000   # Windows (note PID, then: taskkill /PID <pid> /F)
```

### Issue: Slow streaming responses

**Symptom**: First chunk takes >5 seconds
**Solution**:

- Check OpenAI API status: https://status.openai.com
- Try `gpt-3.5-turbo` (faster than `gpt-4`)
- Reduce `max_tokens` in request

---

## Next Steps

1. **Read the API contract**: See `specs/001-streaming-chat-api/contracts/chat-api.yaml` for full API documentation
2. **Explore the code**: Start at `src/main.py` and follow the data flow
3. **Write a test**: Add a new test case in `tests/integration/test_chat_endpoint.py`
4. **Check observability**: Query logs with `jq` to filter by correlation_id:
   ```bash
   docker logs <container-id> | jq 'select(.correlation_id == "YOUR-UUID-HERE")'
   ```

---

## Stopping the Service

**Docker**:

```bash
docker ps  # Find container ID
docker stop <container-id>
```

**Local Python**:

```bash
# Press Ctrl+C in the terminal where uvicorn is running
```

---

**Questions?** Check the full specification at `specs/001-streaming-chat-api/spec.md`
