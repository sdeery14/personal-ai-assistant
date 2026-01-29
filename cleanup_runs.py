import mlflow

mlflow.set_tracking_uri("http://localhost:5000")

# Get all RUNNING runs
runs = mlflow.search_runs(
    experiment_names=["personal-ai-assistant-eval"],
    filter_string="status = 'RUNNING'",
    order_by=["start_time DESC"],
)

print(f"Found {len(runs)} stuck RUNNING runs\n")

client = mlflow.MlflowClient()

for idx, row in runs.iterrows():
    run_id = row["run_id"]
    start_time = row["start_time"]
    print(f"Ending run {run_id} (started {start_time})...")
    try:
        client.set_terminated(run_id, status="FAILED")
        print("  ✓ Terminated")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\nDone!")
