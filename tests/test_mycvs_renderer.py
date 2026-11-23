import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("playwright")


RENDERER_PATH = Path(__file__).parents[1] / "scripts" / "renderers" / "mycvs_v1" / "build_refined_converter_generic.py"
SPEC = importlib.util.spec_from_file_location("mycvs_renderer", RENDERER_PATH)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def test_generated_html_removes_executable_and_external_resource_html() -> None:
    soup = renderer.BeautifulSoup(
        """
        <main>
          <script>document.body.innerHTML = 'tampered';</script>
          <div onclick="fetch('https://evil.example')">Safe text</div>
          <img src="https://evil.example/pixel" onerror="alert(1)">
          <a href="javascript:alert(1)">Link</a>
          <a href="https://example.com">Allowed link</a>
        </main>
        """,
        "html.parser",
    )

    renderer.sanitize_generated_html(soup)

    assert soup.find("script") is None
    assert soup.find("img") is None
    assert soup.find(attrs={"onclick": True}) is None
    assert soup.find("a", href="javascript:alert(1)") is None
    assert soup.find("a", href="https://example.com") is not None
