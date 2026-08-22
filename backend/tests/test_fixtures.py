from pathlib import Path

import pytest

from app.brightdata.client import FixtureClient

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def names(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.glob("*.json"))


@pytest.mark.parametrize("name", names(FIXTURES))
def test_every_fixture_loads(name):
    # raw_trigger.json carries a byte-order mark and a trailing HTTP_CODE line
    # from capture. Captures stay verbatim, so the loader absorbs both.
    assert FixtureClient(FIXTURES)._load(name) is not None


@pytest.mark.parametrize("name", names(SAMPLES))
def test_every_sample_loads(name):
    assert FixtureClient(SAMPLES)._load(name) is not None


def test_trigger_returns_collection_id():
    assert FixtureClient(FIXTURES).trigger("c_x", []) == "j_msm4bhaieddzgdqjd"
