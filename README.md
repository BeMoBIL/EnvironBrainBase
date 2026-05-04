# NeuroUrbanism-DB

A living, open-access database of EEG studies on architecture, urbanism, and
nature: the substrate for systematic and ongoing review.

- **Live app:** _replace this with your Streamlit Cloud URL after deploying_
- **Citation (latest snapshot):** _replace with Zenodo DOI after first release_
- **Submit a paper:** through the [website form](#) or via a [PR](CONTRIBUTING.md).

This database is a fork-style sibling of
[InterBrainDB](https://github.com/acv132/InterBrainDB) (Fraunhofer IAO), which
catalogues hyperscanning studies. We share the same structural idea
(Streamlit front-end, flat CSV source of truth, GitHub PRs as the
submission pipeline) and apply it to neuro-urbanism literature.

## Repo layout

```
NeuroUrbanism-DB/
├── app.py                       # Welcome / landing page (Streamlit entrypoint)
├── pages/
│   ├── 1_Database.py            # browse + filter
│   ├── 2_Submit_a_paper.py      # form that opens a PR via the GitHub API
│   └── 3_Legal.py               # licensing, privacy, disclaimer, contact
├── data/
│   ├── papers.csv               # canonical database (UTF-8 CSV, 295 rows seed)
│   ├── backlog.txt              # DOIs awaiting extraction
│   └── schema_rename_map.json   # provenance: source → canonical column names
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── .github/ISSUE_TEMPLATE/
│   └── paper_submission.yml
├── .zenodo.json                 # mints a DOI per GitHub release
├── CITATION.cff
├── CONTRIBUTING.md              # full schema + submission workflow
├── LICENSE                      # MIT for code; data is CC-BY-4.0 (see below)
├── requirements.txt
└── README.md
```

## Run locally

```bash
git clone https://github.com/Randomidous/NeuroUrbanism-DB.git
cd NeuroUrbanism-DB
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
streamlit run app.py
```

The app loads `data/papers.csv` directly. The submission page additionally
requires a GitHub token; copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and fill it in, or skip: the page renders without
a token, just with the submit button disabled.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (already done if you cloned from your origin).
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo,
   set entrypoint to `app.py`, branch to `main`.
3. In _Settings → Secrets_, paste:

   ```toml
   [github]
   token       = "github_pat_xxx"          # fine-grained PAT, see below
   repo        = "Randomidous/NeuroUrbanism-DB"
   base_branch = "main"
   ```

4. Generate the PAT at
   [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new):
   - Repository access: _Only select repositories_ → `NeuroUrbanism-DB`
   - Repository permissions: **Contents: Read & write**, **Pull requests: Read & write**
   - Expiration: 1 year (rotate annually)
5. Save secrets. Streamlit redeploys automatically; submissions now open PRs.

## Citing

Once you cut a GitHub release, Zenodo will mint a DOI for that snapshot. Use
the latest version's DOI in publications; cite the live app for everyday
links. Both are listed at the top of this README.

If you publish a manuscript that uses a particular database snapshot, cite the
_specific_ version (e.g. `v1.0`), not `main`: that's the entire point of the
release-tag workflow.

## Licensing

- **Code** (everything except `data/`): MIT.
- **Data** (`data/papers.csv` and ancillary): CC-BY-4.0. Attribution: cite the
  Zenodo DOI of the release you used. The fields recording study-level
  metadata are facts and not copyrightable, but the curation, normalization,
  and labeling work is: CC-BY-4.0 makes the boundary clear and permits all
  scholarly reuse.

## Provenance

Seed data extracted by the Zander Labs neuro-urbanism review team. The
canonical column names are derived from a working spreadsheet and harmonized
where ambiguous; the full source-to-canonical mapping is preserved at
`data/schema_rename_map.json` so every column has a verifiable lineage back
to the original extraction.
