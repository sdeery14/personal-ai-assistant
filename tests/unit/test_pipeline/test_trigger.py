"""Unit tests for eval pipeline trigger (run-evals)."""

from unittest.mock import patch, MagicMock

from eval.pipeline.trigger import run_eval_suite, EvalRunResult


class TestRunEvalSuite:
    @patch("eval.pipeline.trigger.subprocess.run")
    def test_core_suite_runs_5_evals(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="PASS", stderr="")

        results = run_eval_suite(suite="core")

        assert len(results) == 5
        assert all(r.passed for r in results)
        assert mock_run.call_count == 5

    @patch("eval.pipeline.trigger.subprocess.run")
    def test_full_suite_runs_all_evals(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="PASS", stderr="")

        results = run_eval_suite(suite="full")

        assert len(results) == 19
        assert mock_run.call_count == 19

    @patch("eval.pipeline.trigger.subprocess.run")
    def test_failed_eval_captured(self, mock_run):
        # First eval passes, second fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="PASS", stderr=""),
            MagicMock(returncode=1, stdout="FAIL", stderr="threshold not met"),
            MagicMock(returncode=0, stdout="PASS", stderr=""),
            MagicMock(returncode=0, stdout="PASS", stderr=""),
            MagicMock(returncode=0, stdout="PASS", stderr=""),
        ]

        results = run_eval_suite(suite="core")

        assert len(results) == 5
        assert results[0].passed is True
        assert results[1].passed is False
        assert results[1].exit_code == 1

    @patch("eval.pipeline.trigger.subprocess.run")
    def test_progress_callback_called(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="PASS", stderr="")

        progress_calls = []

        def callback(i, total, dataset, result):
            progress_calls.append((i, total, dataset))

        run_eval_suite(suite="core", progress_callback=callback)

        assert len(progress_calls) == 5
        assert progress_calls[0][0] == 0  # first index
        assert progress_calls[0][1] == 5  # total

    @patch("eval.pipeline.trigger.subprocess.run")
    def test_timeout_handled(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="eval", timeout=600)

        results = run_eval_suite(suite="core")

        assert len(results) == 5
        assert all(r.exit_code == 2 for r in results)
        assert all(not r.passed for r in results)
