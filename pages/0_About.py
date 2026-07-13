"""
NeuroUrbanism-DB: About / landing page.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from utils import load_csv

DATA_PATH = Path(__file__).parent.parent / "data" / "papers.csv"


@st.cache_data(show_spinner=False)
def _stats() -> dict:
    """Quick counts to display on the welcome page; cached so the CSV is read once."""
    df = load_csv(DATA_PATH)
    df["year_num"] = pd.to_numeric(df["year"], errors="coerce")
    return {
        "n_papers": len(df),
        "year_min": int(df["year_num"].min(skipna=True))
        if df["year_num"].notna().any()
        else None,
        "year_max": int(df["year_num"].max(skipna=True))
        if df["year_num"].notna().any()
        else None,
        "n_arch": int((df["sample_category"].str.contains("1", na=False)).sum()),
        "n_urban": int((df["sample_category"].str.contains("2", na=False)).sum()),
        "n_nature": int((df["sample_category"].str.contains("3", na=False)).sum()),
    }


def main() -> None:
    s = _stats()

    st.title("🧠 NeuroUrbanism-DB")
    st.subheader(
        "A living, open-access database of EEG studies on architecture, urbanism, and nature"
    )

    st.markdown(
        "This tool tracks empirical EEG research on how built and natural "
        "environments shape human neurophysiology. The following features are included:"
    )

    st.markdown(
        "- **Displaying studies:** browse and filter the catalogue by year, "
        "sample type, EEG hardware, lab vs. real-world setting, and free-text "
        "search over titles and authors.\n"
        "- **Categorization:** every record is coded along ~60 dimensions covering "
        "sample, paradigm, EEG acquisition, analysis approach, mobility, and replicability.\n"
        "- **Submission system:** new papers can be added through the website "
        "form: submissions become Pull Requests on GitHub, reviewed and merged "
        "by maintainers, then go live within a minute.\n"
        "- **Replication of original review:** each tagged release is a citable "
        "snapshot with a Zenodo DOI, so manuscripts can cite the exact version "
        "they used while the live database keeps growing."
    )

    st.divider()

    # ---------- Snapshot stats ----------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Papers in database", s["n_papers"])
    if s["year_min"] and s["year_max"]:
        c2.metric("Year range", f"{s['year_min']}–{s['year_max']}")
    c3.metric("Architecture / Urbanism", f"{s['n_arch']} / {s['n_urban']}")
    c4.metric("Nature", s["n_nature"])

    st.divider()

    st.markdown("## Purpose")
    st.markdown(
        "Neuro-urbanism, the study of how cities, buildings, and nature affect "
        "the brain, has grown rapidly across architecture, environmental "
        "psychology, neuroergonomics, and public health. The literature is "
        "scattered across disciplines and journals, with heterogeneous "
        "methodology and inconsistent reporting. NeuroUrbanism-DB is built on "
        "a systematic review of EEG studies in this space, presented as a "
        "queryable, continuously growing database rather than a frozen "
        "appendix in a paper. The aim is to give researchers, designers, and "
        "policy-makers an honest map of what has been measured, where, with "
        "what method, and how robustly."
    )

    st.markdown("## Adding new articles")
    st.markdown(
        "A living review only stays alive if the community keeps it fed. If "
        "we missed a paper, or you have published new results, please submit "
        "your article through the **Submit a paper** page in the sidebar. "
        "The form opens a Pull Request on GitHub; a maintainer reviews and "
        "merges, and the addition appears on the live site automatically. "
        "Contributors are credited in the `contributor` column of the CSV "
        "and named in release notes."
    )

    st.markdown(
        "If you would rather edit the CSV directly, see "
        "[CONTRIBUTING.md](https://github.com/Randomidous/NeuroUrbanism-DB/blob/main/CONTRIBUTING.md) "
        "for the manual PR workflow and full schema documentation."
    )

    st.markdown("## Citation")
    st.markdown(
        "If you use NeuroUrbanism-DB in your work, please cite the **specific "
        "release version** you used (e.g. `v1.0`), not `main`. Each tagged "
        "release has its own Zenodo DOI; the latest version is listed in the "
        "[repository README](https://github.com/Randomidous/NeuroUrbanism-DB#readme). "
        "Citing a fixed version makes your results reproducible while letting "
        "the database itself keep evolving."
    )

    st.markdown("## Related")
    st.markdown(
        "NeuroUrbanism-DB is a fork-style sibling of "
        "[InterBrainDB](https://websites.fraunhofer.de/interbraindb/) (Fraunhofer IAO), "
        "a living database of hyperscanning studies. We share the same "
        "structural design (Streamlit front-end, flat CSV source of truth, "
        "GitHub PRs as the submission pipeline) and apply it to "
        "neuro-urbanism literature."
    )


main()
