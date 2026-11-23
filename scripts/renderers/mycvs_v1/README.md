# Bundled myCVs renderer

FitCV owns a checked-in copy of the renderer used to turn canonical `mycvs_v1`
Markdown into the required one-page A4 PDF. The copied runtime assets are:

- `build_refined_converter_generic.py` - Markdown/HTML/PDF conversion script.
- `long-dang-template.css` - the application CV stylesheet.
- `fonts/Inter-Regular.ttf` and `fonts/Inter-Bold.ttf` - renderer font inputs.

These files were copied from the local `myCVs` repository so FitCV does not
depend on an untracked sibling checkout at runtime. `apply_cv_layout_fix.py` was
not copied because it is a one-off source mutation tool, not a runtime dependency.

## Local setup

Install the renderer dependencies and browser once, and ensure `pandoc` is available:

```text
uv pip install -r scripts/renderers/mycvs_v1/requirements.txt
uv run playwright install chromium
```

Enable the adapter with `FITCV_MYCVS_EXTERNAL_RENDER_ENABLED=1`. When converter,
stylesheet, and font paths are not supplied, FitCV resolves the bundled files
from this directory. Explicit paths still take precedence for controlled
comparisons or a separately pinned renderer revision.

The converter and stylesheet SHA-256 values are recorded in render proof for
reproducibility. Refresh this copy only when the source renderer changes, then
rerun the CV render acceptance tests and update the recorded revisions.
