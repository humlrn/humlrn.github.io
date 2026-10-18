# HUmLrn — automatic FIS2 publications synchronization

**Status:** implemented in the website repository, ready to enable on GitHub. An upstream annotated bibliography URL must be configured after it is published. The ZIP of Alberto Maria Metelli v8 provided for this work contains the files, but the currently public `albertometelli/albertometelli.github.io` repository is a different, older website and does not currently expose them at `bibliography/biblio_{c,j,w}.bib`.

## First-time setup

1. Upload the curated annotated files `bibliography/biblio_c.bib`, `bibliography/biblio_j.bib` and `bibliography/biblio_w.bib` from Alberto Maria Metelli v8 to a GitHub repository accessible to this workflow. **Use annotated originals**, not `bibliography/downloads/`, which omit the FIS2 acknowledgements. The repository can be public or private.
2. Under the **HUmLrn website repository** (`humlrn/humlrn.github.io`) → **Settings → Secrets and variables → Actions → Variables**, add `FIS2_BIBTEX_BASE_URL` pointing to the folder, e.g. `https://raw.githubusercontent.com/<owner>/<repo>/main/bibliography` (public GitHub), or `https://api.github.com/repos/<owner>/<repo>/contents/bibliography` (GitHub API, default branch).
3. If the source is private, set the Actions secret `FIS2_SOURCE_TOKEN` to a **read-only fine-grained GitHub token** with **Contents: read** access *only* to the source repository. Do not put the token in variables or source files. `GITHUB_TOKEN` is normally sufficient to create PRs in the **HUmLrn** repository; it does not grant access to other private repositories.
4. In **Settings → Actions → General → Workflow permissions**, grant **Read and write permissions** to the workflow token and enable **Allow GitHub Actions to create and approve pull requests**, if this setting is available to the organization.
5. Upload this website ZIP to the root of `humlrn/humlrn.github.io`. The workflow file must be on its default branch. Open **Actions → Synchronize FIS2 publications → Run workflow** to test. It also runs weekly on Mondays at 05:15 UTC.
6. Review and merge the Pull Request titled **Bibliography: synchronize FIS2 publications**. The website changes only after that merge (via your existing GitHub Pages deployment). If nothing changed, no PR is opened.

**Without step 1–2, remote weekly runs intentionally fail with a clear error and will not modify the bibliography.** The included snapshot is for local testing and initial publication, **not** a silently substituted live data feed.

## How the pipeline works

- `scripts/sync_fis2.py` downloads all three source BibTeX files before writing changes. It recognizes `FIS2` as a separate token in `acks`, and includes only conferences, journals and workshops.
- Reconciles entries by stable BibTeX key, with a normalized-title check to flag accidental duplicate keys under different names.
- **No automatic deletion**: if a previously published item disappears upstream or loses its FIS2 tag, it is kept and listed in `bibliography/sync-report.md` for manual review.
- Produces the canonical, annotated `bibliography/humlrn-fis2.bib`, public per-entry BibTeX downloads, regenerated publication HTML and filter counts, and a machine-readable report. Updates the static preview copy as well.
- Preserves paper URLs, slides, posters, code, notes and academic metadata present in the annotated source; editorial metadata remains in the canonical aggregate file. The website keeps neutral author styling and the existing publication filter UI.
- Sorts by descending publication year, 'To Appear' status and venue calendar (NeurIPS, CoRL, EWRL, ICML, AISTATS, ICLR, etc.), with explicit year/month fields taking precedence. Venue dates are indicative when a BibTeX entry has no month.
- Any failed source read, invalid file, suspicious duplicate, zero-result selection or invalid link **stops the workflow before publication**.
- Generated `sync-report.json` and `sync-report.md` record additions, updates and retained source removals. The PR contains all resulting changes and requires maintainer approval.

## Run locally

Install dependencies: `python -m pip install -r scripts/requirements-sync.txt`.

For an offline run against the supplied, authoritative **snapshot**:

```sh
python scripts/sync_fis2.py --source-dir bibliography/source-snapshot
```

For remote sync:

```sh
FIS2_BIBTEX_BASE_URL=https://raw.githubusercontent.com/OWNER/REPO/main/bibliography python scripts/sync_fis2.py
```

Check for any differences without writing:

```sh
python scripts/sync_fis2.py --source-dir bibliography/source-snapshot --check
```

Run tests: `python -m unittest discover -s tests -v`.

## Editing and curation

To change the website's publications, **edit the upstream annotated BibTeX**. Do not manually edit generated `bibliography/humlrn-fis2.bib`, `bibliography/entries/*.bib` or `#publications` in `index.html`; the next approved sync would overwrite those edits.

If a previously listed entry must be removed, do so with a *separate manual PR* after verifying its removal or loss of funding acknowledgement, because the synchronizer intentionally preserves existing records.

The output HTML is static and works on GitHub Pages without a server, API call or build step.
