#!/usr/bin/env python3
"""Convert a Markdown CV + CSS to a one-page A4 PDF.

Requires: pandoc, playwright, pypdf; playwright chromium installed.
Usage: python build_refined_converter_generic.py resume.md style.css resume.pdf
       python build_refined_converter_generic.py resume.md style.css resume.pdf \
         --cover-markdown cover.md --cover-css cover.css --position "Role" --company "Company"
"""
import argparse
import base64
import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from playwright.async_api import async_playwright
from pypdf import PdfReader
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class DocumentResult:
    """Outcome for one rendered document."""

    path: Path
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class ConversionResult:
    """Separate outcomes for the required CV and optional cover letter."""

    cv: DocumentResult
    cover: DocumentResult | None = None

PRINT_CSS = """
/* Screenshot-matched header and section rows */
#vue-smart-pages-preview h1 {color:#397eb9; border-color:#5298d0; line-height:1; margin:0 0 6px; padding-bottom:6px; font-size:2.24em; text-align:center; }
#vue-smart-pages-preview .contact-grid { display:grid; grid-template-columns: 40% 39% 21%; grid-template-rows:auto auto; gap:1px 0; font-size:.94em; line-height:1.18; margin:0 0 10px; }
#vue-smart-pages-preview .contact-grid > div {white-space:nowrap;}
#vue-smart-pages-preview .contact-grid > div:nth-child(1) {grid-column:1;grid-row:1}
#vue-smart-pages-preview .contact-grid > div:nth-child(2) {grid-column:2;grid-row:1}
#vue-smart-pages-preview .contact-grid > div:nth-child(3) {grid-column:3;grid-row:1; text-align:right}
#vue-smart-pages-preview .contact-grid > div:nth-child(4) {grid-column:1;grid-row:2}
#vue-smart-pages-preview .contact-grid > div:nth-child(5) {grid-column:3;grid-row:2; text-align:right}
#vue-smart-pages-preview svg {width:1em; height:1em; display:inline-block; vertical-align:-.12em; fill:none; stroke:#263648; stroke-width:1.7; stroke-linejoin:round; stroke-linecap:round;}
#vue-smart-pages-preview {font-size:11px; line-height:1.25;}
#vue-smart-pages-preview h2 {margin:11px 0 4px; font-size:1.44em;}
#vue-smart-pages-preview p {margin:3px 0 2px;}
#vue-smart-pages-preview .cv-triple {display:grid; grid-template-columns:minmax(0,45%) minmax(0,37%) minmax(0,18%); column-gap:0; align-items:start; margin:2px 0 2px; font-size:.97em; line-height:1.2; break-inside:avoid;}
#vue-smart-pages-preview .cv-triple > div { min-width:0; font-weight:700; }
#vue-smart-pages-preview .cv-triple > div:first-child {white-space:normal; overflow-wrap:break-word;}
#vue-smart-pages-preview .cv-triple > div:last-child {text-align:right;white-space:nowrap;}
#vue-smart-pages-preview .cv-triple strong {font-weight:700}
#vue-smart-pages-preview .cv-triple + p {margin-top:2px;}
#vue-smart-pages-preview .education-subjects {margin:2px 0 0;}
#vue-smart-pages-preview .education-gpa {margin:4px 0 5px; line-height:1.25;}
#vue-smart-pages-preview ul:not(.crossref-list) {padding-left:1.15em; list-style-position:outside;}
#vue-smart-pages-preview ul {margin:3px 0 6px; padding-left:1.15em; line-height:1.25; min-width:0; max-width:100%; box-sizing:border-box;}
#vue-smart-pages-preview li {margin-bottom:2px; min-width:0; max-width:100%; overflow-wrap:break-word; white-space:normal; box-sizing:border-box;}
#vue-smart-pages-preview .certificate-row {margin:0;line-height:1.2;}
#vue-smart-pages-preview .certificate-row > div {white-space:nowrap;}
#vue-smart-pages-preview a {color:#397eb9!important; text-decoration:none;}

@media screen and (max-width:700px) {
  #vue-smart-pages-preview .contact-grid > div,
  #vue-smart-pages-preview .cv-triple > div,
  #vue-smart-pages-preview .cv-triple > div:first-child,
  #vue-smart-pages-preview .cv-triple > div:last-child {
    white-space:normal;
    overflow-wrap:anywhere;
  }
}

@page { size: A4; margin: 15px 25px; }
html, body { margin: 0; padding: 0; background: white; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
#vue-smart-pages-preview { box-sizing: border-box; }
#vue-smart-pages-preview * { box-sizing: border-box; }
#vue-smart-pages-preview h1, #vue-smart-pages-preview h2,
#vue-smart-pages-preview h3, #vue-smart-pages-preview dl,
#vue-smart-pages-preview li { break-inside: avoid; }
"""

MAX_PRINT_SCALE = 2.0

COVER_PRINT_CSS = """
@page { size: A4; margin: 15px 25px; }
html, body { margin: 0; padding: 0; background: white; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
#vue-smart-pages-preview { box-sizing: border-box; }
#vue-smart-pages-preview * { box-sizing: border-box; }
#vue-smart-pages-preview svg {width:1em; height:1em; display:inline-block; vertical-align:-.12em; fill:none; stroke:#263648; stroke-width:1.7; stroke-linejoin:round; stroke-linecap:round;}
#vue-smart-pages-preview .cover-header {text-align:center;}
#vue-smart-pages-preview .cover-header h1 {border:0; color:#397eb9; letter-spacing:.12em; margin:0 0 4px; padding:0;}
#vue-smart-pages-preview .cover-subtitle {color:#397eb9; font-size:.9em; font-weight:700; letter-spacing:.08em; text-transform:uppercase;}
#vue-smart-pages-preview .cover-subtitle a {color:inherit;}
#vue-smart-pages-preview .cover-contact {text-align:center; margin:.35em 0 0;}
#vue-smart-pages-preview .cover-contact .resume-header-item {white-space:nowrap;}
#vue-smart-pages-preview .cover-meta {margin:1.5em 0 .55em;}
#vue-smart-pages-preview .cover-subject {margin:0 0 .55em;}
#vue-smart-pages-preview .cover-greeting {margin:0 0 .55em;}
#vue-smart-pages-preview .cover-intro {margin:0 0 .9em;}
#vue-smart-pages-preview .cover-intro p {margin:0 0 .35em;}
#vue-smart-pages-preview .timeline {border-left:1px solid #d4dee8; margin-left:.45em; padding-left:1.7em;}
#vue-smart-pages-preview .tl-item {position:relative; margin:0 0 .95em;}
#vue-smart-pages-preview .tl-item::before {background:#fff; border:1px solid #79a9d1; border-radius:50%; content:""; height:.58em; left:-2.03em; position:absolute; top:.22em; width:.58em;}
#vue-smart-pages-preview .tl-item.tl-focus::before {border:2px solid #397eb9; height:.8em; left:-2.14em; top:.15em; width:.8em;}
#vue-smart-pages-preview .tl-kicker {border:0!important; color:#397eb9!important; font-size:.72em!important; letter-spacing:.12em; line-height:1.2; margin:0 0 .38em!important; padding:0!important; text-transform:uppercase;}
#vue-smart-pages-preview .tl-title {font-weight:700; margin:0 0 .28em;}
#vue-smart-pages-preview .tl-text {margin:0;}
#vue-smart-pages-preview .tl-highlight {background:#f1f5f9; border:1px solid #d9e3ec; border-radius:6px; padding:.72em .9em;}
#vue-smart-pages-preview .tl-highlight .tl-title {margin-top:0;}
#vue-smart-pages-preview .branch-group {display:grid; gap:.8em; grid-template-columns:repeat(2,minmax(0,1fr)); margin-top:.35em;}
#vue-smart-pages-preview .branch-node {background:#f7f9fb; border:1px solid #d9e3ec; border-radius:6px; padding:.65em .75em;}
#vue-smart-pages-preview .branch-title {color:#397eb9; font-size:.86em; margin:0 0 .2em;}
#vue-smart-pages-preview .leaf-list {line-height:1.25; margin:.15em 0 0; padding-left:1.1em;}
#vue-smart-pages-preview .contribution-list {margin-top:.15em;}
#vue-smart-pages-preview .cover-outro {margin:.8em 0 .45em;}
#vue-smart-pages-preview .cover-signoff {margin-top:.35em;}
#vue-smart-pages-preview .cover-signoff .signature {margin:0;}
#vue-smart-pages-preview :where(.tl-item, .branch-node, .tl-highlight) {
  break-inside: avoid;
  page-break-inside: avoid;
}
#vue-smart-pages-preview a { color: #397eb9; }
"""


def inter_css(regular: Path, bold: Path) -> str:
    """Embed locally supplied Inter font files directly in HTML for consistent PDF layout."""
    def face(path: Path, weight: str) -> str:
        ext = path.suffix.lower()
        formats = {".ttf": ("font/ttf", "truetype"), ".woff2": ("font/woff2", "woff2"), ".otf": ("font/otf", "opentype")}
        if ext not in formats:
            raise ValueError(f"Unsupported font extension: {path} (use .ttf, .otf, or .woff2)")
        if not path.is_file():
            raise FileNotFoundError(f"Inter font missing: {path}")
        mime, fmt = formats[ext]
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return (f'@font-face {{ font-family: "Inter"; '
                f'src: url("data:{mime};base64,{encoded}") format("{fmt}"); '
                f'font-style: normal; font-weight: {weight}; font-display: block; }}')
    return "\n".join((face(regular, "400"), face(bold, "700 900"),
                      '#vue-smart-pages-preview { font-family: "Inter", sans-serif !important; }'))


def _certificate_groups(dl):
    """Return certificate rows when a definition list uses dt/dd/dd groups."""
    entries = dl.find_all(["dt", "dd"], recursive=False)
    if not entries or len(entries) % 3:
        return []
    groups = [entries[index:index + 3] for index in range(0, len(entries), 3)]
    if any(
        [entry.name for entry in group] != ["dt", "dd", "dd"]
        for group in groups
    ):
        return []
    return groups


def normalize_definition_lists(soup: BeautifulSoup) -> None:
    """Convert Pandoc definition lists into the CV's stable grid rows."""
    header = soup.find("h1")
    contact = header.find_next_sibling("dl") if header else None
    if contact:
        nodes = contact.find_all(["dt", "dd"], recursive=False)
        if len(nodes) == 5:
            contact.name = "div"
            contact["class"] = "contact-grid"
            for element in nodes:
                element.name = "div"

    # Certificates are emitted as one dt/dd/dd group per entry. Handle the
    # complete section before the generic three-cell conversion below.
    cert_heading = soup.find("h2", id=lambda value: value in ("certificates", "zertifikate"))
    if cert_heading:
        for sibling in list(cert_heading.next_siblings):
            if getattr(sibling, "name", None) == "h2":
                break
            if getattr(sibling, "name", None) != "dl":
                continue
            rows = []
            for group in _certificate_groups(sibling):
                row = soup.new_tag("div")
                row["class"] = ["cv-triple", "certificate-row"]
                for element in group:
                    element.name = "div"
                    row.append(element.extract())
                rows.append(row)
            if rows:
                for row in rows:
                    sibling.insert_before(row)
                sibling.decompose()

    # Other definition lists represent a single three-column row.
    for definition_list in soup.find_all("dl"):
        entries = definition_list.find_all(["dt", "dd"], recursive=False)
        if len(entries) == 3:
            definition_list.name = "div"
            definition_list["class"] = "cv-triple"
            for element in entries:
                element.name = "div"

    # Mark individual certificate rows, including rows authored by a caller
    # that already supplied the certificate structure.
    if cert_heading:
        for sibling in cert_heading.next_siblings:
            if getattr(sibling, "name", None) == "h2":
                break
            if getattr(sibling, "name", None) == "div" and "cv-triple" in sibling.get("class", []):
                sibling["class"] = ["cv-triple", "certificate-row"]


def normalize_education_gpa(soup: BeautifulSoup) -> None:
    """Split a Markdown hard break before GPA into separate styled paragraphs."""
    heading = soup.find("h2", id=lambda value: value in ("education", "ausbildung"))
    if heading is None:
        return
    for sibling in list(heading.next_siblings):
        if getattr(sibling, "name", None) == "h2":
            break
        if getattr(sibling, "name", None) != "p":
            continue
        for br in list(sibling.find_all("br", recursive=False)):
            next_text = "".join(str(node) for node in br.next_siblings).strip()
            if not next_text.startswith("GPA:"):
                continue
            gpa = soup.new_tag("p")
            gpa["class"] = "education-gpa"
            for node in list(br.next_siblings):
                gpa.append(node.extract())
            br.decompose()
            sibling["class"] = "education-subjects"
            sibling.insert_after(gpa)
            break


async def choose_print_scale(render, min_scale: float, max_scale: float = MAX_PRINT_SCALE) -> float:
    """Return the largest scale that keeps the document to one page."""
    if await render(1.0) == 1:
        low, high = 1.0, max_scale
        if await render(high) == 1:
            return high
    else:
        low, high = min_scale, 1.0
        if await render(low) > 1:
            raise RuntimeError(
                f"Even at scale {low:.2f}, content takes more than one page. "
                "Reduce text/margins/font or lower --min-scale."
            )

    for _ in range(13):
        mid = (low + high) / 2
        if await render(mid) == 1:
            low = mid
        else:
            high = mid
    return max(min_scale, low - 0.002)


async def _convert_document(source: Path, css_path: Path, destination: Path, min_scale: float,
                              inter_regular: Path, inter_bold: Path, print_css: str = PRINT_CSS):
    if not shutil.which("pandoc"):
        raise RuntimeError("pandoc is not installed or is not on PATH")
    source_text = source.read_text(encoding="utf-8")
    normalized_source = strip_outer_code_fence(source_text)
    pandoc_source = "-" if normalized_source != source_text else str(source)
    fragment = subprocess.check_output([
        "pandoc", pandoc_source, "--from=markdown+definition_lists+raw_html",
        "--to=html5", "--wrap=none"
    ], input=normalized_source if pandoc_source == "-" else None,
       text=True, encoding="utf-8")
    soup = BeautifulSoup(fragment, "html.parser")
    normalize_definition_lists(soup)
    normalize_education_gpa(soup)
    sanitize_generated_html(soup)
    # Link certificate titles to their official program pages (not individual credential-verification URLs).
    certificate_links = {
        "Azure AI Engineer Associate": "https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/",
        "Machine Learning Zoomcamp": "https://github.com/DataTalksClub/machine-learning-zoomcamp",
        "Data Engineering Zoomcamp": "https://github.com/DataTalksClub/data-engineering-zoomcamp",
    }
    for row in soup.select('.certificate-row'):
        first = row.find('div', recursive=False)
        if first is None:
            continue
        title_text = first.get_text(' ', strip=True)
        href = certificate_links.get(title_text)
        if href and not first.find('a'):
            link = soup.new_tag('a', href=href)
            link['title'] = 'Official certificate or course information'
            for child in list(first.contents):
                link.append(child.extract())
            first.append(link)
    for title in soup.select('.cv-triple > div:first-child'):
        # Remove literal colon placed after the GitHub icon by the Markdown source.
        for child in title.contents:
            if isinstance(child, str) and child.strip().startswith(':'):
                child.replace_with(child.replace(':', '', 1))
                break
    # Inline the actual Tabler brand-github vector, rather than a hand-drawn approximation
    icons = {
      'tabler:mail': '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
      'tabler:phone': '<svg viewBox="0 0 24 24"><path d="M7 3h3l2 5-2.1 1.5a15 15 0 0 0 4.6 4.6L16 12l5 2v3c0 2-2 4-4 4A14 14 0 0 1 3 7c0-2 2-4 4-4Z"/></svg>',
      'tabler:brand-linkedin': '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10v7m0-10v.3M12 17v-7m0 3a3 3 0 0 1 6 0v4"/></svg>',
      'tabler:brand-github': '<svg xmlns="http://www.w3.org/2000/svg" class="iconify" data-icon="tabler:brand-github" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 6v-3.87a3.37 3.37 0 0 0 -.94 -2.61c3.14 -.35 6.44 -1.54 6.44 -7a5.44 5.44 0 0 0 -1.5 -3.75a5.07 5.07 0 0 0 -.09 -3.77s-1.18 -.35 -3.91 2.09a13.38 13.38 0 0 0 -7 0c-2.73 -2.44 -3.91 -2.09 -3.91 -2.09a5.07 5.07 0 0 0 -.09 3.77a5.44 5.44 0 0 0 -1.5 3.78c0 5.42 3.3 6.61 6.44 7a3.37 3.37 0 0 0 -.94 2.61v3.87"/></svg>',
      'ic:outline-location-on': '<svg viewBox="0 0 24 24"><path d="M12 22S5 14 5 10a7 7 0 0 1 14 0c0 4-7 12-7 12Z"/><circle cx="12" cy="10" r="2.5"/></svg>'}
    for icon in soup.select('span.iconify'):
        icon.replace_with(BeautifulSoup(icons.get(icon.get('data-icon'), ''), 'html.parser'))
    fragment = str(soup)
    css = css_path.read_text(encoding="utf-8") + "\n" + inter_css(inter_regular, inter_bold)
    # Icons have been replaced with inline SVG; no external CDN required.
    doc = ("<!doctype html><html><head><meta charset='utf-8'>"
           "<style>" + css + "\n" + print_css + "</style>"
           ""
           "</head><body><main id='vue-smart-pages-preview'>" + fragment +
           "</main></body></html>")

    with TemporaryDirectory() as temp:
        page_file = Path(temp) / "resume.html"
        page_file.write_text(doc, encoding="utf-8")
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("google-chrome") or None, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.set_content(doc, wait_until="domcontentloaded")
            await page.evaluate("""async () => {
                await Promise.all([
                    document.fonts.load('400 13px "Inter"'),
                    document.fonts.load('700 13px "Inter"'),
                ]);
                await document.fonts.ready;
                const faces = [...document.fonts].filter(f => f.family === 'Inter');
                if (faces.length < 2 || faces.some(f => f.status !== 'loaded')) {
                    throw new Error('Inter font faces did not load successfully');
                }
            }""")
            try:
                await page.wait_for_function(
                    "document.querySelectorAll('span.iconify').length === 0", timeout=3500
                )
            except Exception:
                print("Warning: Iconify SVGs did not load; check network access.")
            await page.emulate_media(media="print")

            async def render(scale, target):
                await page.pdf(path=str(target), format="A4", scale=scale,
                               print_background=True, prefer_css_page_size=True)
                return len(PdfReader(str(target)).pages)

            probe = Path(temp) / "probe.pdf"
            chosen = await choose_print_scale(
                lambda scale: render(scale, probe), min_scale
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            pages = await render(chosen, destination)
            await browser.close()
    if pages != 1:
        raise RuntimeError(f"Expected 1 page, got {pages}")
    mediabox = PdfReader(str(destination)).pages[0].mediabox
    w, h = float(mediabox.width), float(mediabox.height)
    if not (abs(w - 595.28) < 2 and abs(h - 841.89) < 2):
        raise RuntimeError(f"Expected A4 portrait, got {w:.1f} x {h:.1f} PDF points")
    print(f"Created {destination} (A4, 1 page; print scale {chosen:.1%})")
    if chosen < 0.76:
        print("Warning: The CV is dense. Consider reducing content for legibility.")


def sanitize_generated_html(soup: BeautifulSoup) -> None:
    """Remove executable markup and fetch-capable resource elements before printing."""
    for tag in soup.find_all(["base", "embed", "form", "iframe", "img", "link", "meta", "object", "script", "source", "track", "video", "audio"]):
        tag.decompose()
    for tag in soup.find_all(True):
        for attribute in list(tag.attrs):
            name = str(attribute).lower()
            if name.startswith("on") or name == "style":
                del tag.attrs[attribute]
                continue
            if name not in {"action", "formaction", "href", "src"}:
                continue
            value = str(tag.attrs.get(attribute) or "").strip()
            if urlparse(value).scheme.lower() in {"data", "javascript", "vbscript"}:
                tag.decompose()
                break


def strip_outer_code_fence(markdown: str) -> str:
    """Remove a matching outer Markdown or HTML code fence, if present."""
    lines = markdown.splitlines(keepends=True)
    if len(lines) < 2:
        return markdown

    opening_index = 0
    if lines[0].strip() == "---":
        closing_front_matter = next(
            (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
            None,
        )
        if closing_front_matter is None:
            return markdown
        opening_index = closing_front_matter + 1

    while opening_index < len(lines) and not lines[opening_index].strip():
        opening_index += 1
    if opening_index >= len(lines):
        return markdown

    opening_info = lines[opening_index].strip()[3:].strip()
    opening_language = opening_info.split(None, 1)[0].lower()
    if opening_language not in {"markdown", "html"}:
        return markdown

    closing_index = len(lines) - 1
    while closing_index > opening_index and not lines[closing_index].strip():
        closing_index -= 1
    if lines[closing_index].strip() != "```":
        return markdown

    return "".join(
        lines[:opening_index] + lines[opening_index + 1:closing_index] + lines[closing_index + 1:]
    )


def apply_cover_fields(markdown: str, position: str = "", company: str = "") -> str:
    """Replace optional cover-template fields in their stable display order."""
    return (markdown
            .replace("{{POSITION}}", position or "")
            .replace("{{COMPANY}}", company or ""))


def default_cover_output(cv_output: Path) -> Path:
    """Return the default cover-letter PDF path beside the CV PDF."""
    return cv_output.with_name(f"{cv_output.stem}-cover{cv_output.suffix}")


async def convert(source: Path, css_path: Path, destination: Path, min_scale: float,
                  inter_regular: Path, inter_bold: Path, *,
                  cover_markdown: Path | None = None,
                  cover_css: Path | None = None,
                  cover_destination: Path | None = None,
                  position: str = "", company: str = "") -> ConversionResult:
    """Render the CV and, when requested, an optional cover-letter PDF."""
    try:
        await _convert_document(source, css_path, destination, min_scale,
                                inter_regular, inter_bold, PRINT_CSS)
    except Exception as exc:
        return ConversionResult(
            cv=DocumentResult(destination, False, f"{type(exc).__name__}: {exc}")
        )

    cv_result = DocumentResult(destination, True)
    if cover_markdown is None:
        return ConversionResult(cv=cv_result)
    cover_destination = cover_destination or default_cover_output(destination)

    try:
        if not cover_markdown.is_file():
            raise FileNotFoundError(f"Cover Markdown not found: {cover_markdown}")
        cover_css_path = cover_css or css_path
        if not cover_css_path.is_file():
            raise FileNotFoundError(f"Cover CSS not found: {cover_css_path}")
        if cover_destination.resolve() == destination.resolve():
            raise ValueError("Cover output must be different from the CV output")
        with TemporaryDirectory() as temp:
            prepared = Path(temp) / cover_markdown.name
            prepared.write_text(
                apply_cover_fields(cover_markdown.read_text(encoding="utf-8"), position, company),
                encoding="utf-8",
            )
            await _convert_document(prepared, cover_css_path, cover_destination, min_scale,
                                    inter_regular, inter_bold, COVER_PRINT_CSS)
    except Exception as exc:
        return ConversionResult(
            cv=cv_result,
            cover=DocumentResult(cover_destination, False, f"{type(exc).__name__}: {exc}"),
        )

    return ConversionResult(cv=cv_result, cover=DocumentResult(cover_destination, True))



def main():
    ap = argparse.ArgumentParser(
        description="Convert a Markdown CV and an optional cover letter to A4 PDFs."
    )
    ap.add_argument("markdown", type=Path, help="CV Markdown input")
    ap.add_argument("css", type=Path, help="CV CSS input")
    ap.add_argument("output", type=Path, help="CV PDF output")
    ap.add_argument("--cover-markdown", type=Path,
                    help="Optional cover-letter Markdown input")
    ap.add_argument("--cover-css", type=Path,
                    help="Optional cover-letter CSS; defaults to the CV CSS")
    ap.add_argument("--cover-output", type=Path,
                    help="Optional cover-letter PDF output; defaults beside the CV PDF")
    ap.add_argument("--position", default="",
                    help="Optional {{POSITION}} value in the cover template")
    ap.add_argument("--company", default="",
                    help="Optional {{COMPANY}} value in the cover template")
    ap.add_argument("--min-scale", type=float, default=0.55)
    ap.add_argument("--inter-regular", type=Path,
                    default=SCRIPT_DIR / "fonts" / "Inter-Regular.ttf")
    ap.add_argument("--inter-bold", type=Path,
                    default=SCRIPT_DIR / "fonts" / "Inter-Bold.ttf")
    args = ap.parse_args()
    if not (0.1 <= args.min_scale <= 1):
        ap.error("--min-scale must be between 0.1 and 1")
    if args.cover_css and not args.cover_markdown:
        ap.error("--cover-css requires --cover-markdown")
    if args.cover_output and not args.cover_markdown:
        ap.error("--cover-output requires --cover-markdown")
    result = asyncio.run(convert(
        args.markdown, args.css, args.output, args.min_scale,
        args.inter_regular, args.inter_bold,
        cover_markdown=args.cover_markdown,
        cover_css=args.cover_css,
        cover_destination=args.cover_output,
        position=args.position,
        company=args.company,
    ))
    if result.cv.success:
        print(f"CV conversion succeeded: {result.cv.path}")
    else:
        print(f"CV conversion failed: {result.cv.path}: {result.cv.error}")
    if result.cover is not None:
        if result.cover.success:
            print(f"Cover-letter conversion succeeded: {result.cover.path}")
        else:
            print(f"Cover-letter conversion failed: {result.cover.path}: {result.cover.error}")
    if not result.cv.success or (result.cover is not None and not result.cover.success):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
