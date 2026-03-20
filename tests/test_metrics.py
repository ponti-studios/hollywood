"""
Tests for evaluation metrics.

These tests use tiny synthetic tensors/data — no model downloads required.
"""

import math

import pytest

torch = pytest.importorskip("torch")


class TestPerplexity:
    def test_perfect_prediction_is_low_perplexity(self):
        """A model that always predicts correctly should have perplexity close to 1."""
        from nexus.evaluation.metrics import compute_perplexity
        from unittest.mock import MagicMock, patch

        # Mock a model that always returns zero loss
        mock_model = MagicMock()
        mock_output = MagicMock()
        mock_output.loss = torch.tensor(0.01)  # very low loss
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.tensor([[1, 2, 3, 4]]),
            "attention_mask": torch.tensor([[1, 1, 1, 1]]),
        }

        # Low loss → perplexity close to e^0.01 ≈ 1.01
        ppl = compute_perplexity(
            mock_model, mock_tokenizer, ["test text"], device="cpu"
        )
        assert ppl < 5.0   # very low perplexity for near-zero loss


class TestSaveLoadMetrics:
    def test_round_trip(self, tmp_path):
        from nexus.evaluation.metrics import save_metrics, load_metrics

        metrics = {"perplexity": 12.5, "accuracy": 0.87, "dataset": "alpaca"}
        save_metrics(metrics, tmp_path)

        loaded = load_metrics(tmp_path)
        assert loaded["perplexity"] == 12.5
        assert loaded["accuracy"] == 0.87
        assert loaded["dataset"] == "alpaca"

    def test_saves_to_correct_file(self, tmp_path):
        from nexus.evaluation.metrics import save_metrics

        save_metrics({"loss": 1.5}, tmp_path)
        assert (tmp_path / "eval_metrics.json").exists()


class TestJudgeOutputParsing:
    def test_parses_score_and_reasoning(self):
        from nexus.evaluation.judge import parse_judge_output

        output = "SCORE: 8\nREASONING: Clear and helpful response."
        score, reasoning = parse_judge_output(output)

        assert score == 8.0
        assert reasoning == "Clear and helpful response."

    def test_clamps_out_of_range_score(self):
        from nexus.evaluation.judge import parse_judge_output

        score, _ = parse_judge_output("SCORE: 15\nREASONING: too high")
        assert score == 10.0   # clamped to max

        score, _ = parse_judge_output("SCORE: -1\nREASONING: too low")
        assert score == 1.0    # clamped to min

    def test_defaults_when_unparseable(self):
        from nexus.evaluation.judge import parse_judge_output

        score, reasoning = parse_judge_output("I cannot evaluate this.")
        assert score == 5.0    # default mid-range score
        assert "No reasoning" in reasoning
