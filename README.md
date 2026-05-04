# NeuroUrbanism-DB

A living, open-access database of EEG studies on architecture, urbanism, and
nature: the substrate for systematic and ongoing review.

- **Live app:** <https://neurourbanism-db.streamlit.app/>
- **Citation (latest snapshot):** _replace with Zenodo DOI after first release_
- **Submit a paper:** through the [website form](https://neurourbanism-db.streamlit.app/Submit_a_paper) or via a [PR](https://github.com/Randomidous/NeuroUrbanism-DB/pulls).

This database is a fork-style sibling of
[InterBrainDB](https://github.com/acv132/InterBrainDB) (Fraunhofer IAO), which
catalogues hyperscanning studies. We share the same structural idea
(Streamlit front-end, flat CSV source of truth, GitHub PRs as the
submission pipeline) and apply it to neuro-urbanism literature.

## Citing

Use the latest Zenodo version's DOI in publications; cite the live app for everyday
links. Both are listed at the top of this README.

If you publish a manuscript that uses a particular database snapshot, cite the
_specific_ version (e.g. `v1.0`), not `main`.

## Licensing

- **Code** (everything except `data/`): MIT.
- **Data** (`data/papers.csv` and ancillary): CC-BY-4.0. Attribution: cite the
  Zenodo DOI of the release you used. The fields recording study-level
  metadata are facts and not copyrightable, but the curation, normalization,
  and labeling work is: CC-BY-4.0 makes the boundary clear and permits all
  scholarly reuse.
