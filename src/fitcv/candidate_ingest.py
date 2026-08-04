"""Deterministic Candidate Profile source ingestion."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
from pathlib import PurePosixPath, PureWindowsPath
import re
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

import yaml

from fitcv.candidate import adapt_candidate_profile_to_v2, validate_candidate_profile_v2


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_DOCX_EXPANDED_BYTES = 25 * 1024 * 1024
_SUPPORTED_MEDIA_TYPES = {
    ".md": {"text/markdown"},
    ".docx": {DOCX_MEDIA_TYPE},
    ".yaml": {"application/yaml", "application/x-yaml", "text/yaml"},
}
_DEFAULT_MEDIA_TYPES = {
    ".md": "text/markdown",
    ".docx": DOCX_MEDIA_TYPE,
    ".yaml": "application/yaml",
}
_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_WORD = f"{{{_WORD_NAMESPACE}}}"
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_LIST_ITEM = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+(.+?)\s*$")


class CandidateIngestError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CandidateIngestResult:
    source_document: dict[str, Any]
    source_blocks: tuple[dict[str, Any], ...]
    extraction_fingerprint: str
    profile: dict[str, Any] | None = None


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def validate_candidate_source_upload(
    filename: str,
    media_type: str,
    content: bytes,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    if (
        not filename
        or filename in {".", ".."}
        or "\x00" in filename
        or PurePosixPath(filename).name != filename
        or PureWindowsPath(filename).name != filename
    ):
        raise CandidateIngestError("candidate_profile_unsafe_filename", "Filename must not contain a path")
    extension = PureWindowsPath(filename).suffix.lower()
    if extension not in _SUPPORTED_MEDIA_TYPES:
        raise CandidateIngestError("candidate_profile_unsupported_source", "Unsupported Candidate Profile source")
    normalized_media_type = media_type.lower().split(";", 1)[0].strip()
    if normalized_media_type == "application/octet-stream":
        normalized_media_type = ""
    if normalized_media_type and normalized_media_type not in _SUPPORTED_MEDIA_TYPES[extension]:
        raise CandidateIngestError("candidate_profile_media_mismatch", "Filename and media type do not match")
    if not content:
        raise CandidateIngestError("candidate_profile_empty_source", "Candidate Profile source is empty")
    if len(content) > max_bytes:
        raise CandidateIngestError("candidate_profile_source_too_large", "Candidate Profile source exceeds byte limit")
    return extension


def _source_document(filename: str, media_type: str, content: bytes, parser_name: str) -> dict[str, Any]:
    checksum = hashlib.sha256(content).hexdigest()
    normalized_media_type = media_type.lower().split(";", 1)[0].strip()
    if normalized_media_type == "application/octet-stream":
        normalized_media_type = ""
    return {
        "id": f"doc_{checksum[:16]}",
        "origin": "uploaded",
        "filename": filename,
        "media_type": normalized_media_type or _DEFAULT_MEDIA_TYPES[PureWindowsPath(filename).suffix.lower()],
        "byte_length": len(content),
        "sha256": checksum,
        "parser": {"name": parser_name, "version": "1"},
    }


def _block(
    document_id: str,
    checksum: str,
    ordinal: int,
    kind: str,
    text: str,
    locator: dict[str, Any],
) -> dict[str, Any]:
    normalized = _normalize_text(text)
    identity = _canonical_hash([checksum, locator, normalized])[:20]
    return {
        "block_id": f"block_{identity}",
        "document_id": document_id,
        "kind": kind,
        "ordinal": ordinal,
        "locator": locator,
        "text": normalized,
    }


def _decode_utf8(content: bytes, code: str) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CandidateIngestError(code, "Candidate Profile source must be UTF-8") from exc


def _markdown_blocks(document: dict[str, Any], content: bytes) -> tuple[dict[str, Any], ...]:
    lines = _decode_utf8(content, "candidate_profile_invalid_markdown").splitlines()
    blocks: list[dict[str, Any]] = []
    paragraph: list[str] = []
    paragraph_start = 0

    def add(kind: str, text: str, start: int, end: int) -> None:
        normalized = _normalize_text(text)
        if normalized:
            blocks.append(
                _block(
                    document["id"],
                    document["sha256"],
                    len(blocks) + 1,
                    kind,
                    normalized,
                    {"kind": "markdown_lines", "start": start, "end": end},
                )
            )

    def flush_paragraph(end: int) -> None:
        nonlocal paragraph, paragraph_start
        if paragraph:
            add("paragraph", " ".join(paragraph), paragraph_start, end)
            paragraph = []
            paragraph_start = 0

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            flush_paragraph(line_number - 1)
            continue
        heading = _HEADING.match(line)
        list_item = _LIST_ITEM.match(line)
        if heading:
            flush_paragraph(line_number - 1)
            add("heading", heading.group(1), line_number, line_number)
        elif list_item:
            flush_paragraph(line_number - 1)
            add("list_item", list_item.group(1), line_number, line_number)
        elif stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph(line_number - 1)
            add("table_row", " | ".join(cell.strip() for cell in stripped.strip("|").split("|")), line_number, line_number)
        else:
            if not paragraph:
                paragraph_start = line_number
            paragraph.append(stripped)
    flush_paragraph(len(lines))
    return tuple(blocks)


def _unsafe_zip_name(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts or bool(path.parts and ":" in path.parts[0])


def _parse_xml(content: bytes) -> ET.Element:
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise CandidateIngestError("candidate_profile_unsafe_docx", "DOCX contains unsafe XML declarations")
    try:
        return ET.fromstring(content)
    except ET.ParseError as exc:
        raise CandidateIngestError("candidate_profile_invalid_docx", "DOCX contains malformed XML") from exc


def _xml_text(element: ET.Element) -> str:
    return _normalize_text("".join(node.text or "" for node in element.iter(f"{_WORD}t")))


def _docx_blocks(
    document: dict[str, Any],
    content: bytes,
    max_docx_expanded_bytes: int,
) -> tuple[dict[str, Any], ...]:
    try:
        archive = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise CandidateIngestError("candidate_profile_invalid_docx", "DOCX is not a valid ZIP package") from exc
    with archive:
        infos = archive.infolist()
        if any(_unsafe_zip_name(info.filename) for info in infos):
            raise CandidateIngestError("candidate_profile_unsafe_docx", "DOCX contains unsafe archive paths")
        if any(info.flag_bits & 0x1 for info in infos):
            raise CandidateIngestError("candidate_profile_unsafe_docx", "Encrypted DOCX is unsupported")
        if sum(info.file_size for info in infos) > max_docx_expanded_bytes:
            raise CandidateIngestError("candidate_profile_docx_expansion_too_large", "DOCX expanded content exceeds byte limit")
        names = {info.filename for info in infos}
        if "[Content_Types].xml" not in names or "word/document.xml" not in names:
            raise CandidateIngestError("candidate_profile_invalid_docx", "DOCX package is incomplete")
        if any(name.lower().endswith(("vbaproject.bin", ".docm")) for name in names):
            raise CandidateIngestError("candidate_profile_unsafe_docx", "Macro-enabled DOCX is unsupported")
        for name in sorted(value for value in names if value.endswith(".rels")):
            relationships = _parse_xml(archive.read(name))
            if any(str(node.attrib.get("TargetMode", "")).lower() == "external" for node in relationships):
                raise CandidateIngestError("candidate_profile_unsafe_docx", "External DOCX relationships are unsupported")

        blocks: list[dict[str, Any]] = []

        def add(kind: str, text: str, locator: dict[str, Any], source_key: str) -> None:
            if not text:
                return
            blocks.append(
                _block(
                    document["id"],
                    document["sha256"],
                    len(blocks) + 1,
                    kind,
                    text,
                    {**locator, "source_part": source_key},
                )
            )

        def read_part(name: str, part: str) -> None:
            root = _parse_xml(archive.read(name))
            body = root.find(f"{_WORD}body") if part == "document" else root
            if body is None:
                raise CandidateIngestError("candidate_profile_invalid_docx", "DOCX document body is missing")
            paragraph_number = 0
            table_number = 0
            for child in list(body):
                if child.tag == f"{_WORD}p":
                    paragraph_number += 1
                    kind = "paragraph" if part == "document" else part
                    add(kind, _xml_text(child), {"kind": "docx_paragraph", "part": part, "paragraph": paragraph_number}, name)
                elif child.tag == f"{_WORD}tbl":
                    table_number += 1
                    for row_number, row in enumerate(child.findall(f"{_WORD}tr"), start=1):
                        for cell_number, cell in enumerate(row.findall(f"{_WORD}tc"), start=1):
                            kind = "table_cell" if part == "document" else part
                            add(
                                kind,
                                _xml_text(cell),
                                {"kind": "docx_table_cell", "part": part, "table": table_number, "row": row_number, "cell": cell_number},
                                name,
                            )

        read_part("word/document.xml", "document")
        for name in sorted(value for value in names if re.fullmatch(r"word/header\d+\.xml", value)):
            read_part(name, "header")
        for name in sorted(value for value in names if re.fullmatch(r"word/footer\d+\.xml", value)):
            read_part(name, "footer")
        return tuple(blocks)


def ingest_candidate_source(
    filename: str,
    media_type: str,
    content: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_docx_expanded_bytes: int = DEFAULT_MAX_DOCX_EXPANDED_BYTES,
) -> CandidateIngestResult:
    extension = validate_candidate_source_upload(filename, media_type, content, max_bytes)
    parser_name = {".md": "fitcv-markdown-parser", ".docx": "fitcv-docx-parser", ".yaml": "fitcv-yaml-importer"}[extension]
    document = _source_document(filename, media_type, content, parser_name)
    profile: dict[str, Any] | None = None
    if extension == ".md":
        blocks = _markdown_blocks(document, content)
    elif extension == ".docx":
        blocks = _docx_blocks(document, content, max_docx_expanded_bytes)
    else:
        blocks = ()
        try:
            loaded = yaml.safe_load(_decode_utf8(content, "candidate_profile_invalid_yaml"))
        except yaml.YAMLError as exc:
            raise CandidateIngestError("candidate_profile_invalid_yaml", "Candidate Profile YAML is invalid") from exc
        if not isinstance(loaded, dict):
            raise CandidateIngestError("candidate_profile_invalid_yaml", "Candidate Profile YAML must be a mapping")
        try:
            profile = adapt_candidate_profile_to_v2(loaded, document)
        except (KeyError, TypeError, ValueError) as exc:
            raise CandidateIngestError("candidate_profile_invalid_yaml", "Candidate Profile YAML cannot be canonicalized") from exc
        errors = validate_candidate_profile_v2(profile)
        if errors:
            reference_error = any("ref" in error or "duplicate ID" in error for error in errors)
            code = "candidate_profile_invalid_references" if reference_error else "candidate_profile_invalid_yaml"
            raise CandidateIngestError(code, "; ".join(errors))
    fingerprint = _canonical_hash({"source_document": document, "source_blocks": blocks, "profile": profile})
    return CandidateIngestResult(document, blocks, fingerprint, profile)
