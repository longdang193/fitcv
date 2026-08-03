from pathlib import Path

import yaml

from fitcv.candidate import validate_candidate_profile_v2


def test_v2_sample_is_valid_and_template_uses_current_contract() -> None:
    root = Path(__file__).parents[1]
    sample = yaml.safe_load((root / "data/candidate_profile.v2.sample.yaml").read_text(encoding="utf-8"))
    template = yaml.safe_load((root / "data/candidate_profile.template.yaml").read_text(encoding="utf-8"))

    assert sample["schema_version"] == "candidate-profile.v2"
    assert validate_candidate_profile_v2(sample) == []
    assert template["schema_version"] == "candidate-profile.v2"
    assert "preferences" not in template
    assert "search_preferences" in template
    assert "current" not in str(template)
