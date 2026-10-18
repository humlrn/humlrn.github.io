# HUmLrn — website prototype

A one-page academic website in English with a light institutional layout, Inter-based typography and the B1 logo with a strong gradient connecting AI and the human figure.

## Open the website

Open `index.html` in a modern browser, or upload `index.html` and the `assets/` directory to a static host. No build step is required. The design uses `Inter`/`Inter Display` when installed, with system font fallbacks; no font files are bundled.

## Editing content

Edit `index.html` for the homepage and `privacy.html` for the privacy notice. Publications are included only when the attached source BibTeX has `acks = {FIS2}` in `biblio_c.bib`, `biblio_w.bib`, or `biblio_j.bib`. The displayed publications are generated from the canonical annotated BibTeX in `bibliography/humlrn-fis2.bib` by `scripts/sync_fis2.py`, retaining publisher links and academic metadata. Synchronization is automated by the weekly GitHub Action once the original annotated source URL has been configured. See [BIBTEX_SYNC.md](BIBTEX_SYNC.md) for setup and manual operation. Add release rows under the relevant GitHub or Hugging Face resource list when verified resources become available.
