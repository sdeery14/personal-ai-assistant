import mlflow

mlflow.set_tracking_uri("http://localhost:5000")

# Get all runs
runs = mlflow.search_runs(
    experiment_names=["personal-ai-assistant-eval"],
    order_by=["start_time DESC"],
    max_results=10,
)

print(f"Total runs found: {len(runs)}\n")

for idx, row in runs.iterrows():
    print(f"Run #{idx + 1}:")
    print(f"  ID: {row['run_id']}")
    print(f"  Status: {row['status']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print(f"  Total cases: {row.get('params.total_cases', 'N/A')}")
    print()

# Check the latest RUNNING run for artifacts
running_runs = runs[runs["status"] == "RUNNING"]
if len(running_runs) > 0:
    latest_running = running_runs.iloc[0]
    run_id = latest_running["run_id"]
    print(f"\nLatest RUNNING run: {run_id}")

    # Try to get the run details
    client = mlflow.MlflowClient()
    run = client.get_run(run_id)

    print(f"Metrics logged: {list(run.data.metrics.keys())}")
    print(f"Params logged: {list(run.data.params.keys())}")

    # Try to list artifacts
    try:
        artifacts = client.list_artifacts(run_id)
        print(f"Artifacts: {[a.path for a in artifacts]}")
    except Exception as e:
        print(f"Error listing artifacts: {e}")
