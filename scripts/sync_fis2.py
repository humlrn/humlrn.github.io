#!/usr/bin/env python3
"""Synchronize the HUmLrn FIS2 bibliography with curated Metelli BibTeX sources.

The main inputs are the three annotated bibliography/biblio_{c,j,w}.bib files.
The source snapshot is for initial review/local testing only; production CI requires
an explicitly configured upstream URL. No automatic deletions are performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import difflib
import html as htmlmod
import json
import os
from pathlib import Path
import re
import shutil
import sys
import unicodedata
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from bibtex_utils import fmt, normalize_title, parse_entries

ROOT = Path(__file__).resolve().parents[1]
GROUP_FILES = {"conferences": "biblio_c.bib", "journals": "biblio_j.bib", "workshops": "biblio_w.bib"}
ENTRY_TYPES = {"conferences": {"inproceedings", "conference"}, "journals": {"article"}, "workshops": {"inproceedings", "conference", "misc"}}
CITATION_FIELDS = {
    "author", "editor", "title", "booktitle", "journal", "year", "month", "volume", "number", "pages",
    "publisher", "series", "organization", "address", "doi", "url", "isbn", "issn", "note", "school", "edition", "chapter"
}
VENUE_MONTHS = (
    (r"neurips|neural information processing", 12),
    (r"corl|robot learning", 11),
    (r"ewrl|european workshop on reinforcement learning", 10),
    (r"ecml|knowledge discovery", 9),
    (r"rlc|reinforcement learning conference", 8),
    (r"ijcai|international joint conference on artificial intelligence", 8),
    (r"uncertainty in artificial intelligence|\buai\b", 8),
    (r"icml|international conference on machine learning", 7),
    (r"robotics: science and systems|\brss\b", 7),
    (r"ijcnn|international joint conference on neural networks", 7),
    (r"colt|conference on learning theory", 6),
    (r"american control conference|\bacc\b", 6),
    (r"aistats|artificial intelligence and statistics", 5),
    (r"iclr|learning representations", 4),  # actual 2026 dates: Apr ICLR, May AISTATS
    (r"aaai", 2),
)
MONTHS = {name.lower(): i for i, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}
KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
FIS2_PATTERN = re.compile(r"(?<![A-Za-z0-9])FIS2(?![A-Za-z0-9])", re.IGNORECASE)
BEGIN = '<!-- FIS2-PUBLICATIONS-START -->'
END = '<!-- FIS2-PUBLICATIONS-END -->'


def plain(value: str) -> str:
    """Display BibTeX text; keep original records unmodified."""
    txt = htmlmod.unescape(str(value or "")).replace("\n", " ")
    swaps = {r"\&": "&", r"\%": "%", r"\textquoteright": "’", r"\epsilon": "ε", r"\varepsilon": "ε", r"\textendash": "–"}
    for old, new in swaps.items():
        txt = txt.replace(old, new)
    txt = re.sub(r"\\(?:textbf|emph|textit|mathrm|mathbf)\s*\{([^{}]*)\}", r"\1", txt)
    accents = {"a`": "à", "e`": "è", "i`": "ì", "o`": "ò", "u`": "ù",
               "a'": "á", "e'": "é", "i'": "í", "o'": "ó", "u'": "ú",
               'a"': "ä", 'e"': "ë", 'i"': "ï", 'o"': "ö", 'u"': "ü",
               "a^": "â", "e^": "ê", "i^": "î", "o^": "ô", "u^": "û",
               "a~": "ã", "n~": "ñ", "o~": "õ"}
    for accent in ("'", "`", '"', "^", "~"):
        pattern = r"\\" + re.escape(accent) + r"\s*\{?([A-Za-z])\}?"
        def convert(m, mark=accent):
            letter = m.group(1)
            translated = accents.get(letter.lower() + mark, letter)
            return translated.upper() if letter.isupper() else translated
        txt = re.sub(pattern, convert, txt)
    txt = txt.replace("{", "").replace("}", "").replace("$", "")
    return re.sub(r"\s+", " ", txt).strip()


def authors(value):
    result = []
    for raw in re.split(r"\s+and\s+", value or ""):
        name = plain(raw)
        if "," in name:
            last, first = name.split(",", 1)
            name = f"{first.strip()} {last.strip()}"
        if name:
            result.append(name)
    return result


def human_authors(names):
    return ", and ".join((", ".join(names[:-1]), names[-1])) if len(names) > 2 else (" and ".join(names))


def venue_of(entry):
    f = entry["fields"]
    return plain(f.get("booktitle") or f.get("journal") or "")


def occurrence_month(venue, month_value):
    value = plain(month_value).lower().rstrip(".")
    if value in MONTHS:
        return MONTHS[value]
    if value.isdigit() and 1 <= int(value) <= 12:
        return int(value)
    for patt, number in VENUE_MONTHS:
        if re.search(patt, venue, re.I):
            return number
    return 0


def sort_key(entry):
    f = entry["fields"]
    match = re.search(r"(?:19|20)\d{2}", f.get("year", ""))
    year = int(match.group()) if match else 0
    venue = venue_of(entry)
    month = occurrence_month(venue, f.get("month", ""))
    # Following the source bibliographic ordering: 'To Appear' ahead of published entries.
    to_appear = bool(re.search(r"\bto appear\b", f.get("note", ""), re.I))
    return (-year, -int(to_appear), -month, normalize_title(f.get("title", "")), entry["key"])


def https_url(value):
    url = str(value or "").strip()
    if not url:
        return ""
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.netloc or re.search(r"[\s<>]", url):
        raise ValueError(f"Invalid publication link: {url!r}")
    return url


def get_source(args):
    if args.source_dir:
        source = Path(args.source_dir)
        if not source.is_dir():
            raise ValueError(f"Missing BibTeX source directory: {source}")
        return {group: (source / filename).read_text(encoding="utf-8-sig")
                for group, filename in GROUP_FILES.items()}
    base = (args.source_base_url or os.environ.get("FIS2_BIBTEX_BASE_URL") or "").strip().rstrip("/")
    if not base:
        raise ValueError(
            "Remote source missing: configure repository variable FIS2_BIBTEX_BASE_URL with "
            "the raw URL of the annotated bibliography folder. See BIBTEX_SYNC.md. "
            "For local testing use --source-dir bibliography/source-snapshot."
        )
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("FIS2_BIBTEX_BASE_URL must be an https:// URL")
    token = os.environ.get("FIS2_SOURCE_TOKEN", "")
    out = {}
    for group, filename in GROUP_FILES.items():
        url = base + "/" + filename
        req = Request(url, headers={"User-Agent": "humlrn-fis2-bibliography-sync/1.0",
                                    "Accept": "application/vnd.github.raw+json" if parsed.netloc == "api.github.com" else "text/plain"})
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urlopen(req, timeout=25) as response:
                data = response.read(4_000_001)
        except Exception as exc:
            raise RuntimeError(f"Cannot retrieve {filename} from the configured upstream; "
                               "the published bibliography remains untouched. "
                               f"({type(exc).__name__})") from exc
        if len(data) > 4_000_000:
            raise ValueError(f"Source file {filename} is unexpectedly large")
        try:
            out[group] = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{filename} is not valid UTF-8") from exc
    return out


def load_annotated(text_by_group):
    """Parse all sources before writing anything; eliminate accidental exports without acks."""
    selected = {}
    seen_all = {}
    count_all = 0
    for group, source in text_by_group.items():
        entries = parse_entries(source)
        if not entries:
            raise ValueError(f"Source {GROUP_FILES[group]} has no parseable BibTeX entries")
        for entry in entries:
            key = entry["key"]
            if not KEY_PATTERN.fullmatch(key):
                raise ValueError(f"Unsafe BibTeX key: {key!r}")
            if key in seen_all:
                raise ValueError(f"Repeated BibTeX key {key} in {group} and {seen_all[key]}")
            seen_all[key] = group
            if not FIS2_PATTERN.search(entry["fields"].get("acks", "")):
                continue
            if entry["type"] not in ENTRY_TYPES[group]:
                raise ValueError(f"Type {entry['type']} is unexpected in {GROUP_FILES[group]} for {key}")
            year = entry["fields"].get("year", "")
            if not re.search(r"(?:19|20)\d{2}", year):
                raise ValueError(f"Missing publication year for {key}")
            entry["group"] = group
            selected[key] = entry
            count_all += 1
    if count_all == 0:
        raise ValueError("No FIS2 records found; canonical sources may have been replaced by public downloads without acks")
    return selected


def load_previous(path):
    if not path.exists():
        return {}
    entries = parse_entries(path.read_text(encoding="utf-8"))
    result = {}
    for entry in entries:
        key = entry["key"]
        if key in result:
            raise ValueError(f"Duplicate key in current HUmLrn bibliography: {key}")
        entry["group"] = {"article": "journals", "inproceedings": "conferences"}.get(entry["type"], "workshops")
        # For workshop inproceedings, use existing website category if available, or venue heuristic.
        venue = venue_of(entry).lower()
        if "workshop" in venue or "ewrl" in venue:
            entry["group"] = "workshops"
        result[key] = entry
    return result


def check_duplicates(entries):
    signatures = {}
    for entry in entries.values():
        sig = normalize_title(entry["fields"].get("title", ""))
        if not sig:
            raise ValueError(f"Empty title in {entry['key']}")
        if sig in signatures and signatures[sig] != entry["key"]:
            raise ValueError(f"Possible duplicate title: {signatures[sig]} / {entry['key']} (review before merging)")
        signatures[sig] = entry["key"]


def tag(soup, name, css_class=None, value=None, **attrs):
    attributes = {"class": css_class} if css_class else {}
    attributes.update({k.replace("_", "-"): v for k, v in attrs.items()})
    element = soup.new_tag(name, attrs=attributes)
    if value is not None:
        element.string = str(value)
    return element


def append_link(soup, parent, label, url, *, download=False):
    if not url:
        return
    el = tag(soup, "a", value=label, href=url)
    if download:
        el.attrs["download"] = ""
    else:
        el.attrs.update({"target": "_blank", "rel": "noopener noreferrer"})
    parent.append(el)
    parent.append(" ")


def render_article(soup, entry):
    f = entry["fields"]
    group = entry["group"]
    title = plain(f.get("title", ""))
    if not title:
        raise ValueError(f"Missing title in {entry['key']}")
    person_names = authors(f.get("author", ""))
    venue = venue_of(entry)
    year = re.search(r"(?:19|20)\d{2}", f.get("year", "")).group()
    article = tag(soup, "article", "publication", **{"data-category": group, "data-key": entry["key"]})
    article.append(tag(soup, "span", "publication-year", year))
    body = tag(soup, "div", "publication-body")
    body.append(tag(soup, "div", "publication-kind", {"journals": "Journal", "conferences": "Conference", "workshops": "Workshop"}[group]))
    body.append(tag(soup, "h3", value=title))
    body.append(tag(soup, "p", "pub-authors", human_authors(person_names)))
    meta = tag(soup, "div", "publication-meta")
    meta.append(tag(soup, "span", "pub-venue", venue))
    body.append(meta)
    details = []
    note = f.get("note", "")
    if note:
        details.append("To Appear" if "to appear" in note.lower() else plain(note))
    for field in ("recognition", "acceptance", "rankcore", "rankggs", "ranksjr", "distinction"):

        if f.get(field):
            details.append(plain(f[field]))
    if details:
        tags = tag(soup, "div", "publication-details")
        for detail in details:
            tags.append(tag(soup, "span", "publication-tag", detail))
        body.append(tags)
    links = tag(soup, "div", "publication-links")
    paper_url = https_url(f.get("url", ""))
    if not paper_url and f.get("doi"):
        paper_url = https_url("https://doi.org/" + f["doi"].strip())
    append_link(soup, links, "Paper ↗", paper_url)
    for field, label in (("slides", "Slides ↗"), ("poster", "Poster ↗"), ("code", "Code ↗"), ("video", "Video ↗"), ("presentation", "Presentation ↗"), ("arxiv", "arXiv ↗")):
        if f.get(field):
            append_link(soup, links, label, https_url(f[field]))
    append_link(soup, links, "BibTeX ↓", f"bibliography/entries/{entry['key']}.bib", download=True)
    citation = f"{', '.join(person_names)} ({year}). {title}. {venue}." + (f" {paper_url}" if paper_url else "")
    copy = tag(soup, "button", "citation-copy", "Copy citation", type="button")
    copy.attrs["data-citation"] = citation
    copy.attrs["aria-label"] = f"Copy citation for {title}"
    links.append(copy)
    body.append(links)
    article.append(body)
    return article


def render_publications(index_path, ordered, counts):
    html = index_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("#publications")
    if not section:
        raise ValueError("Missing #publications section in index.html")
    pub_list = section.select_one(".publication-list")
    if pub_list is None:
        raise ValueError("Missing .publication-list in index.html")
    pub_list.clear()
    for entry in ordered:
        pub_list.append("\n")
        pub_list.append(render_article(soup, entry))
    pub_list.append("\n")
    counter = section.select_one("#publication-total-count")
    if counter is None:
        raise ValueError("Missing total publication counter")
    counter.string = f"{len(ordered)} publications"
    for button in section.select(".publication-filter"):
        filt = button.get("data-filter")
        badge = button.select_one(".publication-filter-count")
        if badge is not None:
            badge.string = str(len(ordered) if filt == "all" else counts.get(filt, 0))
    # Surgical replacement: preserve all HTML outside Publications, including scripts, layout, news.
    original_section = re.search(r"(?s)<section\s+[^>]*id=\"publications\"[^>]*>.*?</section>", html)
    if original_section is None:
        raise ValueError("Cannot identify Publications section in index.html")
    rendered = str(section)
    return html[:original_section.start()] + rendered + html[original_section.end():]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", help="Local source bibliography directory (for tests/manual runs)")
    parser.add_argument("--source-base-url", help="HTTPS base URL to the three annotated BibTeX files")
    parser.add_argument("--check", action="store_true", help="Validate that generated outputs already match disk")
    args = parser.parse_args(argv)
    sources = get_source(args)
    current = load_annotated(sources)
    outbib = ROOT / "bibliography" / "humlrn-fis2.bib"
    previous = load_previous(outbib)
    # Existing entries not in the current source (deleted or lost FIS2) are kept for review.
    removed = sorted(set(previous) - set(current))
    for key in removed:
        current[key] = previous[key]
    check_duplicates(current)
    ordered = sorted(current.values(), key=sort_key)
    counts = Counter(entry["group"] for entry in ordered)
    before = {key: fmt(entry) for key, entry in previous.items()}
    after = {key: fmt(entry) for key, entry in current.items()}
    additions = sorted(set(after) - set(before))
    edits = sorted(k for k in set(after) & set(before) if after[k] != before[k])
    docs = {}
    docs[outbib] = "% Selected from the annotated Metelli bibliography; generated, do not edit.\n" + "\n".join(fmt(e).rstrip() for e in ordered) + "\n"
    docs[ROOT / "bibliography" / "FIS2-selection.txt"] = (
        "Selected from Alberto Maria Metelli annotated BibTeX (acks = {FIS2}), conferences, journals and workshops only.\n"
        + "".join(f"{e['fields'].get('year', '')} | {e['group']} | {e['key']} | {plain(e['fields'].get('title', ''))}\n" for e in ordered)
    )
    for entry in ordered:
        clean = dict(entry)
        clean["fields"] = {name: value for name, value in entry["fields"].items() if name in CITATION_FIELDS}
        docs[ROOT / "bibliography" / "entries" / (entry["key"] + ".bib")] = fmt(clean)
    docs[ROOT / "index.html"] = render_publications(ROOT / "index.html", ordered, counts)
    preview = ROOT / "exports" / "humlrn-static-preview"
    if preview.is_dir():
        docs[preview / "index.html"] = docs[ROOT / "index.html"]
        for path, value in list(docs.items()):
            if path.parent == ROOT / "bibliography" / "entries":
                docs[preview / "bibliography" / "entries" / path.name] = value
    summary = {
        "total": len(ordered), "conferences": counts["conferences"], "journals": counts["journals"],
        "workshops": counts["workshops"], "added": additions, "updated": edits,
        "retained_for_review": removed,
    }
    previous_report = ROOT / "bibliography" / "sync-report.json"
    try:
        prev_removed = json.loads(previous_report.read_text("utf-8")).get("retained_for_review", [])
    except (OSError, ValueError):
        prev_removed = []
    # Do not open a second PR just to reset last week's added/updated counters.
    if additions or edits or prev_removed != removed or not previous_report.exists():
        docs[previous_report] = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
        report_lines = ["## FIS2 bibliography sync", "",
                        f"Publications: {len(ordered)} ({counts['conferences']} conferences, "
                        f"{counts['journals']} journals, {counts['workshops']} workshops)", "",
                        f"Added: {', '.join(additions) or 'none'}", f"Updated: {', '.join(edits) or 'none'}",
                        f"Retained for review (missing or no longer tagged FIS2): {', '.join(removed) or 'none'}", ""]
        docs[ROOT / "bibliography" / "sync-report.md"] = "\n".join(report_lines)
    # Check generated links before writing, ensure the link sets are complete.
    check_soup = BeautifulSoup(docs[ROOT / "index.html"], "html.parser")
    parsed_articles = check_soup.select("#publications .publication")
    if len(parsed_articles) != len(ordered):
        raise ValueError("Generated publication count does not match BibTeX entry count")
    if {el.get("data-key") for el in parsed_articles} != set(current):
        raise ValueError("Generated HTML bibliography keys do not match BibTeX")
    mismatches = [str(path.relative_to(ROOT)) for path, contents in docs.items() if not path.exists() or path.read_text("utf-8") != contents]
    if args.check:
        if mismatches:
            raise ValueError("Out-of-sync generated files: " + ", ".join(mismatches[:15]))
    else:
        for path, contents in docs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
    print("FIS2 publication sync:", json.dumps(summary, ensure_ascii=False))
    print("Changed files:", len(mismatches))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
