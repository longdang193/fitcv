from fitcv.candidate_name_policy import (
    is_candidate_name_placeholder,
    normalize_candidate_name_token,
    resolved_candidate_profile_name,
)


def test_normalize_candidate_name_token_brackets_and_case() -> None:
    assert normalize_candidate_name_token(" [Your Name] ") == "your name"


def test_is_candidate_name_placeholder() -> None:
    assert is_candidate_name_placeholder("Candidate Name") is True
    assert is_candidate_name_placeholder("[Your Name]") is True
    assert is_candidate_name_placeholder("Jane Doe") is False


def test_resolved_candidate_profile_name_filters_placeholder() -> None:
    assert resolved_candidate_profile_name({"name": "Candidate Name"}) == ""
    assert resolved_candidate_profile_name({"name": "Jane Doe"}) == "Jane Doe"
    assert resolved_candidate_profile_name(None) == ""
