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


def test_candidate_profile_templates_bind_real_delete_and_undo_controls() -> None:
    root = Path(__file__).parents[1]
    review_template = (root / "src/fitcv_cp/templates/candidate_profile_creation.html").read_text(encoding="utf-8")
    profiles_template = (root / "src/fitcv_cp/templates/candidate_profiles.html").read_text(encoding="utf-8")

    assert 'data-can-undo="{{ \'true\' if review.capabilities.undo_regeneration else \'false\' }}"' in review_template
    assert 'id="undoStage"' in review_template
    assert "/actions/undo-regeneration" in review_template
    assert "Delete Profile" in profiles_template
    assert "'delete' if view == 'archived' else 'archive'" in profiles_template
    assert "option.dataset.profileDelete" in profiles_template




def test_candidate_profile_upload_captures_file_before_locking_input() -> None:
    root = Path(__file__).parents[1]
    template = (root / "src/fitcv_cp/templates/candidate_profile_creation.html").read_text(encoding="utf-8")
    upload_handler = template.split("function processCandidateProfileUpload() {", 1)[1].split(
        "uploadForm.addEventListener", 1
    )[0]

    assert "var uploadBody = new FormData(uploadForm);" in upload_handler
    assert upload_handler.index("var uploadBody = new FormData(uploadForm);") < upload_handler.index(
        "uploadFile.disabled = true;"
    )
    assert "body: uploadBody" in upload_handler
