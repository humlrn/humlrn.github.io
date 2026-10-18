# HUmLrn — website prototype

A one-page academic website in English with a light institutional layout, Inter-based typography and the B1 logo with a strong gradient connecting AI and the human figure.

## Open the website

Open `index.html` in a modern browser, or upload `index.html` and the `assets/` directory to a static host. No build step is required. The design uses `Inter`/`Inter Display` when installed, with system font fallbacks; no font files are bundled.

## Sections

- About: research question and interactive animated feedback diagram (Demonstrations, Preferences, Corrections, Proxy Rewards).
- Objectives: four research objectives, without work-package references.
- About: project duration, funding programme and an automatically updated progress indicator.
- People: project members with optimized portraits and available institutional or personal profiles. Maria Cristina Centorame and Caterina Motti (Research Assistants) appear after Riccardo Venturelli and before Costanza Arluno.
- Publications: 20 journal/conference/workshop contributions annotated `acks = {FIS2}` in the attached Alberto Maria Metelli v8 BibTeX bibliography, ordered from newest to oldest following the bibliography publication order for ties. Titles, authors, venues, paper/poster/slides links, status, rankings, acceptance rates and downloadable BibTeX follow the personal website. The old unacknowledged 2025 example was removed.
- Software and datasets: direct links to the HUmLrn GitHub and Hugging Face organizations, with counters generated from any release rows added to the page.
- News & Events: unified chronological list of project announcements and talks.
- Footer: exact funding acknowledgement, MUR/FIS/Politecnico high-resolution marks.
- Privacy & cookies: a dedicated notice for the static website, linked from the footer.

## Editing content

Edit `index.html` for the homepage and `privacy.html` for the privacy notice. Publications are included only when the attached source BibTeX has `acks = {FIS2}` in `biblio_c.bib`, `biblio_w.bib`, or `biblio_j.bib`. The displayed publications are generated from the canonical annotated BibTeX in `bibliography/humlrn-fis2.bib` by `scripts/sync_fis2.py`, retaining publisher links and academic metadata. Synchronization is automated by the weekly GitHub Action once the original annotated source URL has been configured. See [BIBTEX_SYNC.md](BIBTEX_SYNC.md) for setup and manual operation. Add release rows under the relevant GitHub or Hugging Face resource list when verified resources become available.

## Logos

The vector source `vector-logos/HUmLrn-primary-gradient.svg` retains the user's selected strong-gradient B1 drawing with vector glyph outlines, as do the variants for navigation, icon, monochrome and dark backgrounds. The institutional logos in `assets/mur.png`, `assets/fis.png` and `assets/polimi.png` preserve the supplied source artwork at high resolution. The supplied institution PDFs are retained for reference. MUR and FIS PDFs themselves contain raster images and are **not** native vector artwork; raster images have not been falsely labelled as vector.
