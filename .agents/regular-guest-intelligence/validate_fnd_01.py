"""Validate the local FND-01 decision record and tracked handoff evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "REGULAR_GUEST_INTELLIGENCE_MVP_SPEC.md"
TRACKER = Path(__file__).with_name("TRACKER.yaml")


def require(text: str, marker: str, source: Path) -> None:
    if marker not in text:
        raise AssertionError(f"{source}: missing required marker {marker!r}")


def main() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    tracker = TRACKER.read_text(encoding="utf-8")

    for marker in (
        "## 24. Approved implementation decisions",
        "### D1. Demo-bar lifecycle and identity boundary",
        "### D2. Rating and feedback provenance",
        "### D3. Flavor taxonomy v1 ownership and boundary",
        "### D4. Pilot patron notice and consent expectation",
        "`guest_stated`",
        "`bartender_observed`",
        "`sweet`, `sour`, `bitter`, `spirituous`, `fruity`, `herbal`, `spicy`, and",
        "`notice_acknowledged_at`",
        "No blocking item\nis unlabeled",
        "### FND-01 sign-off",
    ):
        require(spec, marker, SPEC)

    for marker in (
        "branch: codex/fnd-01-blocking-decisions",
        "planned: 46",
        "completed: 1",
        "- id: FND-01",
        "status: completed",
        'result: "passed"',
        "Stop at Human Checkpoint A",
    ):
        require(tracker, marker, TRACKER)

    print("FND-01 decision record and tracker evidence: passed")


if __name__ == "__main__":
    main()
