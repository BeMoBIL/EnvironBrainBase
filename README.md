# EnvironBrainBase

A living, open-access database of EEG studies on architecture, urbanism, and
nature: the substrate for systematic and ongoing review.

- **Live app:** <https://EnvironBrainBase.streamlit.app/>
- **Citation (latest snapshot):** [10.5281/zenodo.22753385](https://doi.org/10.5281/zenodo.22753385)
- **Submit a paper:** through the [website form](https://EnvironBrainBase.streamlit.app/Submit_a_paper) or via a [PR](https://github.com/BeMoBIL/EnvironBrainBase/pulls).

This database is a fork-style sibling of
[InterBrainDB](https://github.com/acv132/InterBrainDB) (Fraunhofer IAO), which
catalogues hyperscanning studies. We share the same structural idea
(Streamlit front-end, flat CSV source of truth, GitHub PRs as the
submission pipeline) and apply it to neuro-urbanism literature.

## What's in this repository

- `app.py`, `pages/`: the Streamlit web app (browse, filter, submit papers)
- `data/papers.csv`: the coded corpus (single source of truth)
- `analysis.py`, `plots.py`: compute every statistic and figure reported in
  Gramann, Wieske, Estudillo López & Sander (2026), *Before the evidence is
  built: A credibility crisis in EEG Research in Environmental Neuroscience*

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/BeMoBIL/EnvironBrainBase.git
cd EnvironBrainBase
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app locally

```bash
streamlit run app.py
```

The submission form requires GitHub App credentials and is disabled locally;
browsing and filtering work without them.

## Reproduce the paper

```bash
git checkout v1.1.0
python analysis.py --csv data/papers.csv
```

All reported statistics are printed to the console by manuscript section, and
figures are written to `./exports/` (SVG and PNG). Use `--no-plots` for
statistics only. The `v1.1.0` tag (Zenodo DOI: <https://doi.org/[DOI]>) <--- rewrite history once Zenodo minted new DOI
contains exactly the 462 studies analysed in the paper; later versions may
include studies added since.

## Citing

Use the latest Zenodo version's DOI in publications; cite the live app for everyday
links. Both are listed at the top of this README.

If you publish a manuscript that uses a particular database snapshot, cite the
*specific* version (e.g. `v1.0.0`), not `main`.

## Licensing

- **Code** (everything except `data/`): MIT.
- **Data** (`data/papers.csv` and ancillary): CC-BY-4.0. Attribution: cite the
  Zenodo DOI of the release you used. The fields recording study-level
  metadata are facts and not copyrightable, but the curation, normalization,
  and labeling work is: CC-BY-4.0 makes the boundary clear and permits all
  scholarly reuse.

## Contact

For questions about the database, the code, or the analyses, please open a
[GitHub issue](https://github.com/BeMoBIL/EnvironBrainBase/issues).
