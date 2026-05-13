from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "data" / "candidate_profile.template.yaml"
PRIVATE_PATH = ROOT / "data" / "candidate_profile.private.yaml"
COMPAT_PATH = ROOT / "data" / "candidate_profile.yaml"

REQUIRED_TOP_LEVEL_KEYS = {
    "name",
    "headline",
    "summary",
    "contact",
    "experiences",
    "education",
    "skills",
    "projects",
    "certifications",
    "languages",
    "achievements",
    "interests",
    "volunteering",
    "preferences",
}

FORBIDDEN_TEMPLATE_LITERALS = {
    "Nguyen Van A",
    "nguyen.vana@email.com",
    "+49 170 123 4567",
    "https://linkedin.com/in/nguyenvana",
    "https://github.com/nguyenvana",
    "Acme Analytics GmbH",
}


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"Expected mapping in {path}"
    return data


def test_candidate_profile_split_files_exist_and_parse() -> None:
    assert TEMPLATE_PATH.exists(), "Missing candidate_profile.template.yaml"
    assert PRIVATE_PATH.exists(), "Missing candidate_profile.private.yaml"
    assert COMPAT_PATH.exists(), "Missing candidate_profile.yaml"

    _load_yaml(TEMPLATE_PATH)
    _load_yaml(PRIVATE_PATH)
    _load_yaml(COMPAT_PATH)


def test_template_has_required_scaffold_keys() -> None:
    template_data = _load_yaml(TEMPLATE_PATH)
    missing = REQUIRED_TOP_LEVEL_KEYS - set(template_data.keys())
    assert not missing, f"Template missing required keys: {sorted(missing)}"


def test_template_contains_no_known_private_literals() -> None:
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    leaked = sorted(lit for lit in FORBIDDEN_TEMPLATE_LITERALS if lit in content)
    assert not leaked, f"Template leaked private literals: {leaked}"
