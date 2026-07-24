"""Personio provider parsing for FitCV job acquisition."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Callable, Sequence
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree

from fitcv.ingest import validate_linkedin_schema

_PERSONIO_HOST = re.compile(r"^[a-z0-9][a-z0-9-]*\.jobs\.personio\.(?:de|com)$")
_BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "li", "ol", "p", "ul"}


class _DescriptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)





def build_personio_feed_url(careers_url: str) -> str:
    parsed = urlsplit(careers_url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not _PERSONIO_HOST.fullmatch(hostname):
        raise ValueError("careers URL must be an HTTPS Personio jobs host")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Personio careers URL must not contain credentials or a custom port")
    return urlunsplit(("https", hostname, "/xml", "", ""))


def _description_text(value: str) -> str:
    parser = _DescriptionParser()
    parser.feed(value)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def extract_personio_job_page_description(html_text: str) -> str:
    main = re.search(r"<main\b[^>]*>(.*?)</main>", html_text, flags=re.IGNORECASE | re.DOTALL)
    return _description_text(main.group(1)) if main else ""


def _label(value: str) -> str:
    value = value.strip()
    return value[:1].upper() + value[1:] if value else ""


def parse_personio_jobs(
    xml_text: str,
    *,
    company_name: str,
    careers_url: str,
    keywords: Sequence[str] = (),
    description_loader: Callable[[str], str] | None = None,
) -> list[dict[str, str]]:
    feed_url = build_personio_feed_url(careers_url)
    host = urlsplit(feed_url).hostname or ""
    normalized_keywords = tuple(keyword.strip().casefold() for keyword in keywords if keyword.strip())
    root = ElementTree.fromstring(xml_text)
    jobs: list[dict[str, str]] = []

    for position in root.findall("position"):
        personio_id = (position.findtext("id") or "").strip()
        title = (position.findtext("name") or "").strip()
        if not personio_id.isdigit() or not title:
            continue
        if normalized_keywords and not any(keyword in title.casefold() for keyword in normalized_keywords):
            continue

        job_url = f"https://{host}/job/{personio_id}"
        description_sections: list[str] = []
        for section in position.findall("./jobDescriptions/jobDescription"):
            heading = (section.findtext("name") or "").strip()
            body = _description_text(section.findtext("value") or "")
            text = "\n".join(part for part in (heading, body) if part)
            if text:
                description_sections.append(text)
        description = "\n\n".join(description_sections)
        if not description and description_loader is not None:
            description = description_loader(job_url).strip()
        if not description:
            continue

        locations = list(
            dict.fromkeys(
                text
                for office in position.findall(".//office")
                if (text := (office.text or "").strip())
            )
        )
        seniority = _label(position.findtext("seniority") or "")
        years = (position.findtext("yearsOfExperience") or "").strip()
        experience_level = f"{seniority} ({years} years)" if seniority and years else seniority or years
        created_at = (position.findtext("createdAt") or "").strip()
        job = {
            "title": title,
            "location": ", ".join(locations),
            "publishedAt": created_at[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", created_at) else "",
            "jobUrl": job_url,
            "companyName": company_name,
            "companyUrl": careers_url.rstrip("/"),
            "description": description,
            "contractType": _label(
                position.findtext("schedule") or position.findtext("employmentType") or ""
            ),
            "experienceLevel": experience_level,
            "workType": (position.findtext("department") or "").strip(),
            "applyUrl": job_url,
            "applyType": "EXTERNAL",
            "source": "career-ops:personio",
            "personioId": personio_id,
        }
        errors = validate_linkedin_schema(job)
        if errors:
            raise ValueError(f"Personio job {personio_id} violates FitCV contract: {', '.join(errors)}")
        jobs.append(job)

    return jobs
