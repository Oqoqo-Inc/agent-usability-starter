import json
import pathlib
import tempfile
import unittest
import runner

class RunnerTest(unittest.TestCase):
    def test_missing_attempt_is_not_zero_or_failure(self):
        row = dict(id="missing", agent="a", condition="baseline", task="search", artifact="missing")
        result = runner.verify_attempt(row, pathlib.Path("/tmp"))
        self.assertEqual(result["status"], "unmeasured")
        self.assertIsNone(result["passed"])
        summary = runner.summarize([result])[0]
        self.assertEqual(summary["measured"], 0)
        self.assertIsNone(summary["pass_rate"])
        self.assertIsNone(summary["input_tokens_mean"])

    def test_duplicates_and_invalid_metrics_rejected(self):
        row = dict(id="same", agent="a", condition="baseline", task="search", artifact="a")
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "attempts.json"
            path.write_text(json.dumps([row, row]))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                runner.load_manifest(path)
            for value in (-1, True, float("nan")):
                path.write_text(json.dumps([dict(row, input_tokens=value)]))
                with self.assertRaisesRegex(ValueError, "Invalid input_tokens"):
                    runner.load_manifest(path)

    def test_cohorts_and_metric_coverage_stay_separate(self):
        base = dict(id="a", agent="a", condition="baseline", task="search", status="measured", passed=True, input_tokens=100)
        other = dict(base, id="b", agent="b", passed=False, input_tokens=None)
        summary = runner.summarize([base, other])
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]["input_tokens_mean"], 100)
        self.assertEqual(summary[1]["input_tokens_coverage"], 0)

if __name__ == "__main__":
    unittest.main()
