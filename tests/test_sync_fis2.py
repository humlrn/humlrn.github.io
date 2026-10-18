"""Offline regression tests for HUmLrn FIS2 publications sync."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sync_fis2 as sync


class BibSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = {name: (ROOT / "bibliography/source-snapshot" / filename).read_text(encoding="utf-8")
                      for name, filename in sync.GROUP_FILES.items()}

    def test_complete_source_snapshot(self):
        entries = sync.load_annotated(self.source)
        self.assertEqual(len(entries), 20)
        self.assertEqual(len([e for e in entries.values() if e["group"] == "conferences"]), 11)
        self.assertEqual(len([e for e in entries.values() if e["group"] == "journals"]), 1)
        self.assertEqual(len([e for e in entries.values() if e["group"] == "workshops"]), 8)
        self.assertIn("fiandri2026addressinga", entries)
        self.assertIn("lazzati2026closeda", entries)
        sync.check_duplicates(entries)

    def test_filter_only_exact_token(self):
        src = {group: f'@article{{ignored_{group}, title={{Ignore {group}}}, year={{2026}}, acks={{NOTFIS2X}}}}' for group in self.source}
        with self.assertRaisesRegex(ValueError, "No FIS2"):
            sync.load_annotated(src)

    def test_bad_url_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid publication link"):
            sync.https_url("javascript:alert(1)")

    def test_duplicate_titles_detected(self):
        entries = sync.load_annotated(self.source)
        duplicate = {"type": "article", "key": "otherkey", "group": "journals",
                     "fields": dict(next(iter(entries.values()))["fields"])}
        entries["otherkey"] = duplicate
        with self.assertRaisesRegex(ValueError, "duplicate title"):
            sync.check_duplicates(entries)

    def test_unavailable_remote_fails_closed(self):
        with patch.dict("os.environ", {"FIS2_BIBTEX_BASE_URL": ""}):
            with self.assertRaisesRegex(ValueError, "Remote source missing"):
                sync.get_source(sync.argparse.Namespace(source_dir=None, source_base_url=None))

    def test_render_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "bibliography/source-snapshot").mkdir(parents=True)
            shutil.copy2(ROOT / "index.html", folder / "index.html")
            for filename in sync.GROUP_FILES.values():
                shutil.copy2(ROOT / "bibliography/source-snapshot" / filename, folder / "bibliography/source-snapshot" / filename)
            oldroot = sync.ROOT
            sync.ROOT = folder
            try:
                self.assertEqual(sync.main(["--source-dir", str(folder / "bibliography/source-snapshot")]), 0)
                soup = BeautifulSoup((folder / "index.html").read_text(), "html.parser")
                items = soup.select("#publications .publication")
                self.assertEqual(len(items), 20)
                self.assertEqual(soup.select_one("#publication-total-count").get_text(strip=True), "20 publications")
                self.assertEqual({b.get("data-filter"): b.select_one(".publication-filter-count").get_text(strip=True)
                                  for b in soup.select(".publication-filter")},
                                 {"all": "20", "conferences": "11", "journals": "1", "workshops": "8"})
                self.assertEqual(len(soup.select("#publications .pub-authors strong")), 0)
                self.assertEqual(len(set(item["data-key"] for item in items)), 20)
                self.assertTrue(all((folder / "bibliography/entries" / (item["data-key"] + ".bib")).is_file()
                                    for item in items))
                self.assertEqual(sync.main(["--source-dir", str(folder / "bibliography/source-snapshot")]), 0)
                self.assertEqual(sync.main(["--source-dir", str(folder / "bibliography/source-snapshot"), "--check"]), 0)
                report = json.loads((folder / "bibliography/sync-report.json").read_text())
                self.assertEqual(len(report["added"]), 20)
                self.assertEqual(report["updated"], [])
                self.assertEqual(report["retained_for_review"], [])
                # Simulate a withdrawn upstream entry. Old record should remain with a warning.
                name = "lazzati2026closeda"
                file = folder / "bibliography/source-snapshot/biblio_w.bib"
                orig = file.read_text()
                file.write_text(orig.replace('acks = {FIS2}', 'acks = {OTHER}', 1))
                self.assertEqual(sync.main(["--source-dir", str(folder / "bibliography/source-snapshot")]), 0)
                report = json.loads((folder / "bibliography/sync-report.json").read_text())
                self.assertEqual(report["total"], 20)
                self.assertEqual(len(report["retained_for_review"]), 1)
                self.assertEqual(len(BeautifulSoup((folder / "index.html").read_text(), "html.parser").select("#publications .publication")), 20)
            finally:
                sync.ROOT = oldroot


if __name__ == "__main__":
    unittest.main()
