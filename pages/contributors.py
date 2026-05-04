"""
NeuroUrbanism-DB: Contributors page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_csv  # noqa: E402

DATA_PATH = Path(__file__).parent.parent / "data" / "papers.csv"

# ---------------------------------------------------------------------------
# Core authors (from CITATION.cff)
# ---------------------------------------------------------------------------

CORE_AUTHORS = [
    {
        "name": "Klaus Gramann",
        "affiliation": "Technische Universität Berlin, Germany",
        "role": "Data curation & review, principal investigator",
    },
    {
        "name": "Roy Eric Wieske",
        "affiliation": "Technische Universität Berlin, Germany",
        "role": "Data curation & review, lead developer",
    },
    {
        "name": "Jorge Estudillo",
        "affiliation": "Technische Universität Berlin, Germany",
        "role": "Data curation & review",
    },
    {
        "name": "Isabelle Sander",
        "affiliation": "Technische Universität Berlin, Germany",
        "role": "Data curation & review",
    },
]


@st.cache_data(show_spinner=False)
def _contribution_stats() -> pd.DataFrame:
    """Return per-name contribution counts (submitted + edited)."""
    df = load_csv(DATA_PATH)

    submitted: dict[str, int] = {}
    edited: dict[str, int] = {}

    for _, row in df.iterrows():
        for name in str(row.get("contributor", "")).split(","):
            name = name.strip()
            if name:
                submitted[name] = submitted.get(name, 0) + 1
        for name in str(row.get("edited_by", "")).split(","):
            name = name.strip()
            if name:
                edited[name] = edited.get(name, 0) + 1

    all_names = sorted(set(submitted) | set(edited))
    rows = [
        {
            "Name": n,
            "Papers submitted": submitted.get(n, 0),
            "Papers edited / reviewed": edited.get(n, 0),
            "Total contributions": submitted.get(n, 0) + edited.get(n, 0),
        }
        for n in all_names
        if n  # skip empty strings
    ]
    return pd.DataFrame(rows).sort_values("Total contributions", ascending=False)


def main() -> None:
    st.title("👥 Contributors")
    st.markdown(
        "NeuroUrbanism-DB is built and maintained by a team at "
        "Technische Universität Berlin, with contributions from the wider "
        "neuro-urbanism community."
    )

    st.divider()

    # ── Core team ──────────────────────────────────────────────────────────
    st.subheader("Core team")
    cols = st.columns(len(CORE_AUTHORS))
    for col, author in zip(cols, CORE_AUTHORS):
        with col:
            st.markdown(
                f"<div style='border:1px solid #e0e0e0;border-radius:10px;"
                f"padding:16px;height:100%'>"
                f"<strong style='font-size:1rem'>{author['name']}</strong><br>"
                f"<span style='color:#555;font-size:0.82rem'>{author['role']}</span><br>"
                f"<span style='color:#888;font-size:0.78rem'>{author['affiliation']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Contribution stats ─────────────────────────────────────────────────
    st.subheader("Contribution log")
    st.caption(
        "Counts derived from the `contributor` and `edited_by` columns in "
        "papers.csv. Every submission and editorial review is credited."
    )
    stats = _contribution_stats()
    if not stats.empty:
        st.dataframe(
            stats,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Papers submitted": st.column_config.ProgressColumn(
                    "Papers submitted",
                    min_value=0,
                    max_value=int(stats["Papers submitted"].max()),
                    format="%d",
                ),
                "Papers edited / reviewed": st.column_config.ProgressColumn(
                    "Papers edited / reviewed",
                    min_value=0,
                    max_value=int(stats["Papers edited / reviewed"].max()),
                    format="%d",
                ),
            },
        )

    st.divider()

    # ── How to contribute ──────────────────────────────────────────────────
    st.subheader("How to contribute")
    st.markdown(
        "There are two ways to add to the database:\n\n"
        "- **Via the app:** use the *Submit a paper* page — it opens a GitHub "
        "Pull Request that a maintainer reviews and merges.\n"
        "- **Via GitHub:** fork the repository, add your entry to `data/papers.csv` "
        "following the schema in `CONTRIBUTING.md`, and open a PR directly.\n\n"
        "All contributors are credited in the `contributor` column of the CSV "
        "and listed on this page automatically once their PR is merged."
    )

    st.markdown(
        "**Repository:** "
        "[github.com/Randomidous/NeuroUrbanism-DB](https://github.com/Randomidous/NeuroUrbanism-DB)"
    )


main()
