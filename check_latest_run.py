import mlflow
import pandas as pd

mlflow.set_tracking_uri("http://localhost:5000")

# Get the latest run
runs = mlflow.search_runs(
    experiment_names=["personal-ai-assistant-eval"],
    order_by=["start_time DESC"],
    max_results=1,
)

if len(runs) == 0:
    print("No runs found!")
    exit(1)

run_id = runs.iloc[0]["run_id"]
print(f"Latest run: {run_id}")
print(f"Status: {runs.iloc[0]['status']}")
print(f"Duration: {runs.iloc[0]['end_time'] - runs.iloc[0]['start_time']}")
print()

# Get run details
client = mlflow.MlflowClient()
run = client.get_run(run_id)

print("=" * 60)
print("METRICS:")
print("=" * 60)
for key, value in sorted(run.data.metrics.items()):
    print(f"  {key}: {value}")

print()
print("=" * 60)
print("PARAMS:")
print("=" * 60)
for key, value in sorted(run.data.params.items()):
    print(f"  {key}: {value}")

print()
print("=" * 60)
print("TAGS:")
print("=" * 60)
for key, value in sorted(run.data.tags.items()):
    if not key.startswith("mlflow."):
        print(f"  {key}: {value}")
