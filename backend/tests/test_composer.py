from app.heal.composer import MAX_PROMPT, compose_prompt
from app.detect.classifier import FieldSignal
from app.contracts.loader import load_contracts


def test_prompt_under_1000():
    reg = load_contracts("contracts/pricing_pages.yaml")
    sig = FieldSignal(
        host="linear.app",
        field="tier_price_monthly",
        fill_rate=0.0,
        malformed_rate=0.0,
        n_rows=4,
        baseline=0.8,
        z=8.0,
        effect=0.8,
        flagged=True,
        malformed_structural=False,
        sparse_prone=True,
    )
    prompt = compose_prompt("linear.app", [sig], reg.by_name(), previous_failure="x" * 200)
    assert len(prompt) <= MAX_PROMPT
    assert "tier_price_monthly" in prompt
