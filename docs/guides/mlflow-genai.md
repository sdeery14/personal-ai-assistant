# MLflow GenAI Guide

**Last Updated**: 2026-01-28
**MLflow Version**: 3.8.1
**Purpose**: Capture best practices and lessons learned for MLflow GenAI evaluation

---

## Overview

MLflow 3.x provides a unified GenAI evaluation framework for LLM applications. This guide documents patterns for:

- **Agent evaluation** with tool-calling assessment
- **Evaluation datasets** for systematic test management
- **LLM-as-a-judge scorers** (predefined and custom)
- **Tracing** for observability during evaluation
- **MCP Server** for AI-assisted analysis
- **Model serving** for deployment

---

## Installation

```bash
pip install mlflow==3.8.1
```

For full stack with artifacts:

```bash
pip install mlflow[extras]==3.8.1 psycopg2-binary boto3
```

For MCP server:

```bash
pip install 'mlflow[mcp]>=3.5.1'
```

For lightweight production tracing:

```bash
pip install mlflow-tracing  # 95% smaller than full mlflow package
```

---

## Core Concepts

### Experiments

An experiment groups related runs:

```python
import mlflow

mlflow.set_experiment("personal-ai-assistant-eval")
```

### Runs

A run captures a single evaluation execution:

```python
with mlflow.start_run():
    mlflow.log_param("model", "gpt-4.1")
    mlflow.log_metric("pass_rate", 0.85)
    mlflow.log_artifact("results.json")
```

### Scorers (Judges)

LLM-based evaluators for quality assessment:

```python
from mlflow.genai.judges import make_judge
from typing import Literal

quality_judge = make_judge(
    name="quality",
    instructions="...",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)
```

---

## Patterns We Use

### Pattern 1: Custom Quality Judge

Used in Feature 002 for LLM-as-a-judge evaluation:

```python
from mlflow.genai.judges import make_judge
from typing import Literal

quality_judge = make_judge(
    name="quality",
    instructions="""You are an evaluation judge for an AI assistant.

## Task
Evaluate the assistant's response quality based on the provided rubric.

## Input
**User Question**: {{ inputs.question }}
**Assistant Response**: {{ outputs.response }}
**Evaluation Rubric**: {{ expectations.rubric }}

## Scoring Scale
- **5 (Excellent)**: Fully addresses the question, accurate, well-structured
- **4 (Good)**: Addresses the question correctly with minor issues
- **3 (Acceptable)**: Partially addresses the question; some gaps
- **2 (Poor)**: Significantly misses the point or contains errors
- **1 (Unacceptable)**: Completely wrong or irrelevant

Return ONLY the numeric score (1, 2, 3, 4, or 5).""",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)
```

**Key learnings:**

- Use Jinja2 templating: `{{ inputs.field }}`, `{{ outputs.field }}`, `{{ expectations.field }}`
- `feedback_value_type` must be a `Literal` type for structured output
- Model format: `openai:/model-name`

### Pattern 2: Evaluation with mlflow.genai.evaluate()

```python
import mlflow
import pandas as pd

# Prepare data
eval_data = [
    {
        "inputs": {"question": "What is 2+2?"},
        "outputs": {"response": "The answer is 4."},
        "expectations": {"rubric": "Should correctly state the answer is 4."},
    },
]

# Run evaluation
results = mlflow.genai.evaluate(
    data=eval_data,
    scorers=[quality_judge],
)

# Access metrics
print(results.metrics)
# {"quality/mean": 4.5, "quality/mode": "5"}
```

**Key learnings:**

- Data format: list of dicts with `inputs`, `outputs`, `expectations` keys
- Each key maps to a dict of fields accessible in judge template
- Metrics auto-aggregated as `{scorer_name}/mean`, `{scorer_name}/mode`

### Pattern 3: With Prediction Function

When you need to generate outputs dynamically:

```python
def predict_fn(inputs: dict) -> dict:
    """Generate assistant response."""
    response = get_assistant_response(inputs["question"])
    return {"response": response}

# Data without outputs
eval_data = [
    {
        "inputs": {"question": "What is 2+2?"},
        "expectations": {"rubric": "Should correctly state the answer is 4."},
    },
]

results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=predict_fn,
    scorers=[quality_judge],
)
```

---

## Evaluating Agents

MLflow provides specialized support for evaluating AI agents with tools, multi-step workflows, and complex behaviors.

### Agent Evaluation Workflow

1. **Build your agent** with tools and instructions
2. **Create evaluation dataset** with inputs, expectations, and tags
3. **Define agent-specific scorers** that evaluate behaviors using traces
4. **Run evaluation** and analyze results in MLflow UI

### Wrapping an Agent for Evaluation

```python
from agents import Agent, Runner, function_tool

@function_tool
def add(a: float, b: float) -> float:
    """Adds two numbers."""
    return a + b

@function_tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

agent = Agent(
    name="Math Agent",
    instructions="Calculate using the given tools. Return the final number only.",
    tools=[add, multiply],
)

# Wrap agent in predict function for MLflow
def predict_fn(question: str) -> str:
    return Runner.run_sync(agent, question).final_output

# Async also supported!
async def predict_fn_async(question: str) -> str:
    result = await Runner.run(agent, question)
    return result.final_output
```

### Agent Evaluation Dataset

```python
eval_dataset = [
    {
        "inputs": {"task": "What is 15% of 240?"},
        "expectations": {"answer": 36},
        "tags": {"topic": "math"},
    },
    {
        "inputs": {"task": "I bought 2 shares at $100 each. It's now worth $150. How much profit?"},
        "expectations": {"answer": 100},
        "tags": {"topic": "math"},
    },
]
```

### Agent-Specific Scorers

```python
from mlflow.genai import scorer
from mlflow.genai.scorers import ToolCallEfficiency

@scorer
def exact_match(outputs, expectations) -> bool:
    """Check if output matches expected answer."""
    return int(outputs) == expectations["answer"]

# Run evaluation with agent scorers
results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=predict_fn,
    scorers=[
        exact_match,
        ToolCallEfficiency(),  # Built-in: evaluates tool usage patterns
    ],
)
```

### Built-in Agent Scorers

| Scorer                | What It Evaluates                     | Requires Trace |
| --------------------- | ------------------------------------- | -------------- |
| `ToolCallEfficiency`  | Are tool calls efficient?             | Yes            |
| `ToolCallCorrectness` | Are tool calls and arguments correct? | Yes            |

### Parallelization

```bash
# Speed up agent evaluation with parallelization
export MLFLOW_GENAI_EVAL_MAX_WORKERS=10

# Configure async timeout (default: 5 minutes)
export MLFLOW_GENAI_EVAL_ASYNC_TIMEOUT=600  # 10 minutes
```

---

## Evaluation Datasets

Evaluation datasets provide centralized test management with versioning and ground truth.

> **Note:** Requires MLflow Tracking Server with SQL backend (PostgreSQL, MySQL, SQLite).

### Creating Datasets

```python
from mlflow.genai.datasets import create_dataset, set_dataset_tags

# Create dataset linked to experiment
dataset = create_dataset(
    name="production_validation_set",
    experiment_id=["0"],  # "0" is default experiment
    tags={"team": "ml-platform", "stage": "validation"},
)

# Add additional tags
set_dataset_tags(
    dataset_id=dataset.dataset_id,
    tags={"environment": "dev", "version": "1.3"},
)
```

### Adding Records from Dictionaries

```python
records = [
    {
        "inputs": {"question": "What is 2+2?"},
        "expectations": {"answer": "4"},
    },
    {
        "inputs": {"question": "Explain machine learning."},
        "expectations": {"key_points": ["algorithms", "data", "patterns"]},
    },
]

dataset.merge_records(records)
```

### Building Datasets from Traces

```python
import mlflow

# Search for traces with specific criteria
traces = mlflow.search_traces(
    experiment_ids=["0"],
    max_results=20,
    filter_string="attributes.name = 'chat_completion'",
    return_type="list",
)

# Add expectations to traces
for trace in traces:
    mlflow.log_expectation(
        trace_id=trace.info.trace_id,
        name="expected_answer",
        value="The correct answer should include step-by-step instructions",
    )

# Retrieve annotated traces and add to dataset
annotated_traces = mlflow.search_traces(
    experiment_ids=["0"],
    max_results=20,
    return_type="list",
)

dataset.merge_records(annotated_traces)
```

### Source Types

| Source Type | Description                       | When Assigned            |
| ----------- | --------------------------------- | ------------------------ |
| `TRACE`     | Records from production traces    | Auto: from search_traces |
| `HUMAN`     | Subject matter expert annotations | Auto: has expectations   |
| `CODE`      | Programmatically generated        | Auto: no expectations    |
| `DOCUMENT`  | From documentation/specs          | Manual override only     |

### Dataset Benefits

- **Centralized test management** - No scattered CSV files
- **Ground truth management** - Define expected outputs
- **Schema evolution** - Add fields without breaking evaluations
- **Incremental updates** - Add cases from production
- **Performance tracking** - Monitor over time

---

## Predefined LLM Scorers

MLflow provides ready-to-use LLM judge scorers for common evaluation scenarios.

### Quick Usage

```python
from mlflow.genai.scorers import Correctness, RelevanceToQuery, Guidelines

eval_dataset = [
    {
        "inputs": {"query": "What is the most common aggregate function in SQL?"},
        "outputs": "The most common aggregate function in SQL is SUM().",
        "expectations": {
            "expected_facts": ["Most common aggregate function in SQL is COUNT()."],
        },
    },
]

results = mlflow.genai.evaluate(
    data=eval_dataset,
    scorers=[
        Correctness(),
        RelevanceToQuery(),
        Guidelines(
            name="is_concise",
            guidelines="The answer must be concise and straight to the point.",
        ),
    ],
)
```

### Single-Turn Scorers

| Scorer                   | What It Evaluates                             | Needs Expectations | Needs Trace |
| ------------------------ | --------------------------------------------- | ------------------ | ----------- |
| `RelevanceToQuery`       | Does response address the user's input?       | No                 | No          |
| `Correctness`            | Are expected facts in the response?           | Yes                | No          |
| `Completeness`           | Does agent address all questions?             | No                 | No          |
| `Fluency`                | Is response grammatically correct?            | No                 | No          |
| `Guidelines`             | Does response adhere to custom guidelines?    | Yes                | No          |
| `ExpectationsGuidelines` | Does response meet expectations + guidelines? | Yes                | No          |
| `Safety`                 | Avoids harmful/toxic content?                 | No                 | No          |
| `Equivalence`            | Is response equivalent to expected output?    | Yes                | No          |
| `RetrievalGroundedness`  | Is response grounded in retrieved info?       | No                 | Yes         |
| `RetrievalRelevance`     | Are retrieved docs relevant?                  | No                 | Yes         |
| `RetrievalSufficiency`   | Do retrieved docs have all needed info?       | Yes                | Yes         |
| `ToolCallCorrectness`    | Are tool calls and arguments correct?         | No                 | Yes         |
| `ToolCallEfficiency`     | Are tool calls efficient?                     | No                 | Yes         |

### Multi-Turn Scorers (Conversations)

| Scorer                             | What It Evaluates                         |
| ---------------------------------- | ----------------------------------------- |
| `ConversationCompleteness`         | All user questions addressed?             |
| `ConversationalRoleAdherence`      | Assistant maintains assigned role?        |
| `ConversationalSafety`             | Responses safe throughout?                |
| `ConversationalToolCallEfficiency` | Tool usage efficient across conversation? |
| `KnowledgeRetention`               | Retains info from earlier turns?          |
| `UserFrustration`                  | Is user frustrated? Resolved?             |

> Multi-turn scorers require traces with `mlflow.trace.session` metadata.

### Selecting Judge Models

```python
from mlflow.genai.scorers import Correctness

# Default is GPT-4o-mini
Correctness()

# Override with specific model
Correctness(model="openai:/gpt-4o-mini")
Correctness(model="anthropic:/claude-4-opus")
Correctness(model="google:/gemini-2.0-flash")
```

**Supported providers:** OpenAI, Azure OpenAI, Anthropic, Amazon Bedrock, Cohere, Together AI, and any LiteLLM-supported provider.

### Output Format

Scorers return structured assessments:

```python
# score: "yes" or "no" (renders as Pass/Fail in UI)
# rationale: Explanation of the decision
# source: Metadata about evaluation source
```

---

## Custom LLM Scorers

Three approaches for creating custom LLM judges:

### 1. Guidelines-based (Simplest)

```python
from mlflow.genai.scorers import Guidelines

concise_scorer = Guidelines(
    name="is_concise",
    guidelines="The answer must be concise and straight to the point.",
)
```

### 2. Template-based (More Control)

```python
from mlflow.genai.judges import make_judge
from typing import Literal

quality_judge = make_judge(
    name="quality",
    instructions="""Evaluate the assistant's response quality.

**User Question**: {{ inputs.question }}
**Assistant Response**: {{ outputs.response }}
**Evaluation Rubric**: {{ expectations.rubric }}

## Scoring Scale
- **5**: Excellent - fully addresses question
- **4**: Good - correct with minor issues
- **3**: Acceptable - partially addresses
- **2**: Poor - significantly misses point
- **1**: Unacceptable - completely wrong

Return ONLY the numeric score.""",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)
```

### 3. Function-based (Full Control)

```python
from mlflow.genai import scorer

@scorer
def custom_metric(inputs, outputs, expectations) -> float:
    """Custom scorer with full control."""
    # Access trace if needed via trace parameter
    # Perform any custom logic
    score = compute_custom_score(inputs, outputs, expectations)
    return score
```

### Choosing Judge Models

| Development Stage  | Recommended Model         | Why                               |
| ------------------ | ------------------------- | --------------------------------- |
| Early (inner loop) | GPT-4o, Claude Opus       | Deep exploration, identify issues |
| Production         | GPT-4o-mini, Claude Haiku | Cost-effective at scale           |

---

## MLflow Tracing

MLflow Tracing captures inputs, outputs, and metadata for each step of agent execution.

### One-Line Auto Tracing

```python
import mlflow

# Enable automatic tracing for OpenAI Agents SDK
mlflow.openai.autolog()

# Other supported libraries
mlflow.langchain.autolog()
mlflow.anthropic.autolog()
# ... and 20+ more integrations
```

### Manual Tracing

```python
import mlflow

# Decorator approach
@mlflow.trace
def my_function(input: str) -> str:
    # Function is automatically traced
    return process(input)

# Context manager approach
with mlflow.start_span("custom_operation") as span:
    result = do_something()
    span.set_attribute("custom_key", "value")
```

### Tracing During Evaluation

When using `predict_fn` in evaluation, traces are automatically captured:

```python
import mlflow

mlflow.openai.autolog()  # Enable tracing

results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=predict_fn,  # Traces captured automatically
    scorers=[ToolCallEfficiency()],  # Scorers can analyze traces
)
```

### Trace Features

| Feature                | Description                         |
| ---------------------- | ----------------------------------- |
| **OpenTelemetry**      | Fully compatible, no vendor lock-in |
| **Framework Agnostic** | 20+ library integrations            |
| **Async Logging**      | Non-blocking for production         |
| **PII Redaction**      | Mask sensitive data                 |
| **Sampling**           | Control trace throughput            |
| **Session Grouping**   | Group traces by user/session        |

### Production Tracing

```python
# Use lightweight SDK for production
# pip install mlflow-tracing

# Configure async logging (non-blocking)
import mlflow
mlflow.config.enable_async_logging(True)
```

---

## MLflow MCP Server

The MLflow MCP Server lets AI assistants (Claude, Cursor, VS Code) interact with traces programmatically.

### Installation

```bash
pip install 'mlflow[mcp]>=3.5.1'
```

### VS Code Configuration

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "mlflow-mcp": {
      "command": "uv",
      "args": ["run", "--with", "mlflow[mcp]>=3.5.1", "mlflow", "mcp", "run"],
      "env": {
        "MLFLOW_TRACKING_URI": "http://localhost:5000"
      }
    }
  }
}
```

### Available Tools

| Tool                | Description                         |
| ------------------- | ----------------------------------- |
| `search_traces`     | Search/filter traces in experiments |
| `get_trace`         | Get detailed trace information      |
| `delete_traces`     | Delete traces by ID or timestamp    |
| `set_trace_tag`     | Add custom tags to traces           |
| `delete_trace_tag`  | Remove tags from traces             |
| `log_feedback`      | Log evaluation scores/judgments     |
| `log_expectation`   | Log ground truth labels             |
| `get_assessment`    | Retrieve assessment details         |
| `update_assessment` | Modify existing assessments         |
| `delete_assessment` | Remove assessments                  |

### Use Cases

```text
# Debugging production issues
User: Find all failed traces in experiment 1 from the last hour
Agent: Uses search_traces with filter_string="status='ERROR' AND timestamp_ms > [recent]"

# Performance analysis
User: Show me the slowest traces with execution times over 5 seconds
Agent: Uses search_traces with filter_string="execution_time_ms > 5000"

# Quality assessment
User: Log a relevance score of 0.85 for trace tr-abc123
Agent: Uses log_feedback with appropriate parameters
```

### Field Selection

```python
# Extract specific fields to reduce response size
search_traces(
    experiment_id="1",
    extract_fields="info.trace_id,info.state,data.spans.*.name",
)
```

---

## Model Serving

MLflow can serve trained models as REST APIs for production deployment.

### Quick Start

```bash
# Serve a logged model
mlflow models serve -m "models:/<model-id>" -p 5000

# Serve a registered model
mlflow models serve -m "models:/<model-name>/<version>" -p 5000

# Serve from local path
mlflow models serve -m ./path/to/model -p 5000
```

### Endpoints

| Endpoint       | Method | Description              |
| -------------- | ------ | ------------------------ |
| `/invocations` | POST   | Main prediction endpoint |
| `/ping`        | GET    | Health check             |
| `/health`      | GET    | Health check             |
| `/version`     | GET    | Server and model info    |

### Input Formats

```json
// dataframe_split format
{
  "dataframe_split": {
    "columns": ["feature1", "feature2"],
    "data": [[1.0, 2.0], [3.0, 4.0]]
  }
}

// dataframe_records format
{
  "dataframe_records": [
    {"feature1": 1.0, "feature2": 2.0},
    {"feature1": 3.0, "feature2": 4.0}
  ]
}

// instances format
{
  "instances": [[1.0, 2.0], [3.0, 4.0]]
}
```

### Logging Models for Serving

```python
import mlflow
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient

# Log model with signature for validation
signature = infer_signature(X_train, model.predict(X_train))
mlflow.sklearn.log_model(
    sk_model=model,
    name="my_model",
    signature=signature,
    registered_model_name="production_model",
    input_example=X_train[:5],
)

# Use aliases for deployment
client = MlflowClient()
client.set_registered_model_alias(
    name="production_model",
    alias="production",
    version="1",
)
```

### Serving GenAI Models

For agents and chat models, see [Agent Server](https://mlflow.org/docs/3.8.1/genai/serving/agent-server/) and [Responses Agents](https://mlflow.org/docs/3.8.1/genai/serving/responses-agent/).

### Production-like Local Setup

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: mlflow
      POSTGRES_PASSWORD: mlflow
      POSTGRES_DB: mlflow
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "mlflow"]
      interval: 5s
      retries: 5

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      retries: 5

  minio-init:
    image: minio/mc
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      bash -c "
      mc alias set minio http://minio:9000 minioadmin minioadmin &&
      mc mb --ignore-existing minio/mlflow
      "

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.17.0
    depends_on:
      postgres:
        condition: service_healthy
      minio-init:
        condition: service_completed_successfully
    ports:
      - "5000:5000"
    environment:
      MLFLOW_BACKEND_STORE_URI: postgresql://mlflow:mlflow@postgres:5432/mlflow
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
    command: >
      mlflow server
      --backend-store-uri postgresql://mlflow:mlflow@postgres:5432/mlflow
      --artifacts-destination s3://mlflow
      --host 0.0.0.0
      --port 5000

volumes:
  postgres_data:
  minio_data:
```

**Key learnings:**

- Use health checks for proper startup ordering
- MinIO init container creates bucket before MLflow starts
- Artifacts stored in S3-compatible MinIO, not local filesystem

### Client Configuration

```python
import os

os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
```

---

## Logging Best Practices

### Parameters (Configuration)

```python
mlflow.log_params({
    "assistant_model": "gpt-4.1",
    "judge_model": "gpt-4.1",
    "temperature": 0,
    "max_tokens": 2000,
    "dataset_version": "1.0.0",
    "pass_rate_threshold": 0.80,
    "score_threshold": 3.5,
})
```

### Metrics (Results)

```python
mlflow.log_metrics({
    "total_cases": 10,
    "passed_cases": 8,
    "failed_cases": 2,
    "error_cases": 0,
    "pass_rate": 0.80,
    "average_score": 4.2,
})
```

### Artifacts (Files)

```python
import json
import tempfile

# Log JSON artifact
results_data = [{"case_id": "case-001", "score": 5, ...}]
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(results_data, f, indent=2)
    mlflow.log_artifact(f.name, "results")
```

---

## Regression Gating

### Computing Pass/Fail

```python
def compute_gate_result(
    pass_rate: float,
    average_score: float,
    pass_rate_threshold: float = 0.80,
    score_threshold: float = 3.5,
) -> tuple[bool, str]:
    """Compute overall pass/fail for regression gate."""
    reasons = []

    if pass_rate < pass_rate_threshold:
        reasons.append(f"pass rate {pass_rate:.1%} < {pass_rate_threshold:.1%}")

    if average_score < score_threshold:
        reasons.append(f"avg score {average_score:.2f} < {score_threshold:.2f}")

    passed = len(reasons) == 0
    reason = "; ".join(reasons) if reasons else "all thresholds met"

    return passed, reason
```

### Exit Codes

```python
import sys

passed, reason = compute_gate_result(pass_rate, avg_score)

mlflow.log_metric("overall_passed", 1 if passed else 0)
mlflow.set_tag("gate_reason", reason)

if passed:
    print("✓ OVERALL: PASS")
    sys.exit(0)
else:
    print(f"✗ OVERALL: FAIL - {reason}")
    sys.exit(1)
```

---

## Testing

### Mocking MLflow

```python
from unittest.mock import patch, MagicMock

@patch("mlflow.start_run")
@patch("mlflow.log_params")
@patch("mlflow.log_metrics")
def test_evaluation_logging(mock_metrics, mock_params, mock_run):
    mock_run.return_value.__enter__ = MagicMock()
    mock_run.return_value.__exit__ = MagicMock()

    # Run evaluation
    run_evaluation(...)

    # Assert logging calls
    mock_params.assert_called_once()
    mock_metrics.assert_called_once()
```

### Testing Without Server

Use file-based tracking for tests:

```python
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    os.environ["MLFLOW_TRACKING_URI"] = f"file://{tmpdir}"

    # Tests run with local file storage
    run_evaluation(...)
```

---

## Gotchas & Lessons Learned

### 1. Judge Template Variables

❌ **Wrong:**

```python
instructions="Question: {question}"  # Python f-string won't work
```

✅ **Correct:**

```python
instructions="Question: {{ inputs.question }}"  # Jinja2 template
```

### 2. Literal Type for Feedback

❌ **Wrong:**

```python
feedback_value_type=str  # Unstructured output
```

✅ **Correct:**

```python
feedback_value_type=Literal["1", "2", "3", "4", "5"]  # Constrained
```

### 3. Data Format Keys

The data format uses specific keys that map to template variables:

- `inputs` → `{{ inputs.* }}`
- `outputs` → `{{ outputs.* }}`
- `expectations` → `{{ expectations.* }}`

### 4. S3 Endpoint for MinIO

When using MinIO locally, set the endpoint:

```python
os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
```

Without this, boto3 will try to reach AWS S3.

### 5. Datasets Require SQL Backend

❌ **Wrong:**

```python
# File-based tracking won't work with datasets
os.environ["MLFLOW_TRACKING_URI"] = "file:///tmp/mlruns"
create_dataset(name="test")  # Error!
```

✅ **Correct:**

```python
# Use SQLite or PostgreSQL
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///mlflow.db"
# or
os.environ["MLFLOW_TRACKING_URI"] = "postgresql://..."
```

### 6. Retrieval Scorers Need Traces

❌ **Wrong:**

```python
# Static data won't work with retrieval scorers
data = [{"inputs": {...}, "outputs": {...}}]
mlflow.genai.evaluate(
    data=data,
    scorers=[RetrievalGroundedness()],  # Error: no RETRIEVER spans!
)
```

✅ **Correct:**

```python
# Use predict_fn to generate traces during evaluation
mlflow.genai.evaluate(
    data=data,
    predict_fn=rag_pipeline,  # Generates traces with RETRIEVER spans
    scorers=[RetrievalGroundedness()],
)
```

### 7. Agent Scorers Need Tracing Enabled

❌ **Wrong:**

```python
# No tracing = no tool call analysis
def predict_fn(q):
    return agent.run(q)

mlflow.genai.evaluate(
    predict_fn=predict_fn,
    scorers=[ToolCallEfficiency()],  # Won't see tool calls!
)
```

✅ **Correct:**

```python
import mlflow
mlflow.openai.autolog()  # Enable tracing BEFORE evaluation

mlflow.genai.evaluate(
    predict_fn=predict_fn,
    scorers=[ToolCallEfficiency()],  # Can analyze traced tool calls
)
```

### 8. Multi-Turn Scorers Need Session IDs

Multi-turn scorers require traces with session metadata:

```python
# Set session ID when tracing
with mlflow.start_span("chat") as span:
    span.set_attribute("mlflow.trace.session", "session-123")
    # ... conversation logic
```

---

## Resources

- [MLflow Documentation](https://mlflow.org/docs/3.8.1/)
- [MLflow GenAI Evaluation](https://mlflow.org/docs/3.8.1/genai/eval-monitor/)
- [Evaluating Agents](https://mlflow.org/docs/3.8.1/genai/eval-monitor/running-evaluation/agents/)
- [Evaluation Datasets](https://mlflow.org/docs/3.8.1/genai/datasets/)
- [Predefined Scorers](https://mlflow.org/docs/3.8.1/genai/eval-monitor/scorers/llm-judge/predefined/)
- [LLM-as-a-Judge](https://mlflow.org/docs/3.8.1/genai/eval-monitor/scorers/llm-judge/)
- [MLflow Tracing](https://mlflow.org/docs/3.8.1/genai/tracing/)
- [MLflow MCP Server](https://mlflow.org/docs/3.8.1/genai/mcp/)
- [Model Serving](https://mlflow.org/docs/3.8.1/genai/serving/)
- [OpenAI Agents SDK Integration](https://mlflow.org/docs/3.8.1/genai/tracing/integrations/listing/openai-agent/)

---

## Changelog

| Date       | Change                                                         |
| ---------- | -------------------------------------------------------------- |
| 2026-01-28 | Add Agent Evaluation, Datasets, Scorers, Tracing, MCP, Serving |
| 2026-01-28 | Initial guide created for Feature 002 planning                 |
