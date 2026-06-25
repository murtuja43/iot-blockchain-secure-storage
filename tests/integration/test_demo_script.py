"""Test that the tamper-detection demo script works end to end."""

from scripts.demo_tamper_detection import run_demo


def test_demo_reports_valid_then_detects_tampering():
    result = run_demo(difficulty=2)  # seeds its own demo chain in a temp dir
    assert result["valid_before"] is True
    assert result["valid_after"] is False
    assert result["block_index"] == 1
    assert result["reason"]
