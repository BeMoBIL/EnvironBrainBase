"""
NeuroUrbanism-DB: Database (browse + filter) page.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent.parent / "data" / "papers.csv"

st.set_page_config(
    page_title="Database: NeuroUrbanism-DB",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_papers() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, dtype=str).fillna("")
    for col in ("year", "num_participants", "num_channels", "sampling_rate_hz"):
        if col in df.columns:
            df[col + "_num"] = pd.to_numeric(df[col], errors="coerce")
    return df


SAMPLE_LABELS = {"1": "Architecture", "2": "Urbanism", "3": "Nature"}
LAB_LABELS = {"1": "Lab", "2": "Real-world", "3": "Mixed"}
MOBILE_LABELS = {"stat": "Stationary", "mob": "Mobile"}


def main() -> None:
    df = load_papers()

    st.title("📚 Database")
    st.caption(
        f"{len(df)} EEG studies on architecture, urbanism, and nature. "
        "Use the sidebar to filter; pick a row below for the full record."
    )

    st.sidebar.header("Filters")

    year_min = int(df["year_num"].min(skipna=True)) if df["year_num"].notna().any() else 1980
    year_max = int(df["year_num"].max(skipna=True)) if df["year_num"].notna().any() else 2026
    year_range = st.sidebar.slider("Year", year_min, year_max, (year_min, year_max))

    sample_pick = st.sidebar.multiselect(
        "Sample category",
        options=list(SAMPLE_LABELS.keys()),
        format_func=lambda v: SAMPLE_LABELS.get(v, v),
        help="1 = Architecture, 2 = Urbanism, 3 = Nature.",
    )
    lab_pick = st.sidebar.multiselect(
        "Setting (lab vs real-world)",
        options=list(LAB_LABELS.keys()),
        format_func=lambda v: LAB_LABELS.get(v, v),
    )
    mobile_pick = st.sidebar.multiselect(
        "EEG system",
        options=list(MOBILE_LABELS.keys()),
        format_func=lambda v: MOBILE_LABELS.get(v, v),
    )

    chan_min = int(df["num_channels_num"].min(skipna=True)) if df["num_channels_num"].notna().any() else 1
    chan_max = int(df["num_channels_num"].max(skipna=True)) if df["num_channels_num"].notna().any() else 256
    chan_range = st.sidebar.slider("Number of EEG channels", chan_min, chan_max, (chan_min, chan_max))

    text_query = st.sidebar.text_input("Title / authors search", "")

    f = df.copy()
    f = f[f["year_num"].between(year_range[0], year_range[1]) | f["year_num"].isna()]

    if sample_pick:
        mask = f["sample_category"].apply(
            lambda s: any(p in [x.strip() for x in s.split(",")] for p in sample_pick) if s else False
        )
        f = f[mask]
    if lab_pick:
        f = f[f["lab_realworld_binary"].isin(lab_pick)]
    if mobile_pick:
        f = f[f["eeg_system_mobile_stationary"].str.lower().isin([m.lower() for m in mobile_pick])]
    f = f[f["num_channels_num"].between(chan_range[0], chan_range[1]) | f["num_channels_num"].isna()]
    if text_query.strip():
        q = text_query.strip().lower()
        mask = (
            f["title"].str.lower().str.contains(q, na=False)
            | f["authors_short"].str.lower().str.contains(q, na=False)
            | f["authors_full"].str.lower().str.contains(q, na=False)
        )
        f = f[mask]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Papers shown", len(f))
    c2.metric("Years", f"{year_range[0]}–{year_range[1]}")
    c3.metric("Architecture", int((f["sample_category"].str.contains("1", na=False)).sum()))
    c4.metric("Urbanism", int((f["sample_category"].str.contains("2", na=False)).sum()))

    st.divider()

    display_cols = [
        "authors_short", "year", "title", "journal", "sample_category",
        "num_participants", "num_channels", "lab_realworld_binary", "doi_link",
    ]
    display_cols = [c for c in display_cols if c in f.columns]

    st.dataframe(
        f[display_cols].rename(columns={
            "authors_short": "Authors", "year": "Year", "title": "Title",
            "journal": "Journal", "sample_category": "Cat.",
            "num_participants": "N", "num_channels": "Channels",
            "lab_realworld_binary": "Setting", "doi_link": "DOI / Link",
        }),
        hide_index=True, use_container_width=True, height=520,
        column_config={"DOI / Link": st.column_config.LinkColumn("DOI / Link")},
    )

    st.divider()
    st.subheader("Paper detail")
    if len(f) == 0:
        st.info("No papers match the current filters.")
        return

    def _label(row: pd.Series) -> str:
        title = (row.get("title", "") or "").strip()
        return f"{row.get('authors_short','')} ({row.get('year','')}): {title[:80]}"

    options = f.index.tolist()
    chosen = st.selectbox(
        "Pick a paper to inspect",
        options=options,
        format_func=lambda i: _label(f.loc[i]),
    )
    if chosen is not None:
        row = f.loc[chosen]
        with st.expander("Full record", expanded=True):
            cols = st.columns(2)
            for i, (k, v) in enumerate(row.items()):
                if k.endswith("_num"):
                    continue
                if v == "" or v is None:
                    continue
                with cols[i % 2]:
                    st.markdown(f"**{k}**: {v}")


if __name__ == "__main__":
    main()
