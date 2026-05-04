"""
NeuroUrbanism-DB: Database (browse + filter + plots) page.

Two tabs, both driven by the same sidebar filters:
  1. Data overview: descriptives + browsable table + per-paper detail.
  2. Plots: publication trends, methodology distributions, mobility heatmap.
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
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
    for col in ("year", "num_participants", "num_channels", "sampling_rate_hz",
                "participant_mobility_score", "system_mobility_score",
                "replicability_score"):
        if col in df.columns:
            df[col + "_num"] = pd.to_numeric(df[col], errors="coerce")
    return df


SAMPLE_LABELS = {"1": "Architecture", "2": "Urbanism", "3": "Nature"}
LAB_LABELS = {"1": "Lab", "2": "Real-world", "3": "Mixed"}
MOBILE_LABELS = {"stat": "Stationary", "mob": "Mobile"}


# --------------------------------------------------------------------------
# Helpers for the Plots tab
# --------------------------------------------------------------------------

def _explode_sample_category(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (paper, sample_category code). Multi-coded papers (e.g. '1, 2')
    are counted in every category they belong to, which is the right behaviour
    for category breakdowns: a paper studying both architecture and urbanism
    should appear in both bars."""
    if "sample_category" not in df.columns:
        return df.assign(sample_label="Unknown")
    rows = []
    for _, r in df.iterrows():
        codes = [c.strip() for c in str(r.get("sample_category", "")).split(",") if c.strip()]
        if not codes:
            rows.append({**r.to_dict(), "sample_label": "Uncoded"})
        else:
            for c in codes:
                rows.append({**r.to_dict(), "sample_label": SAMPLE_LABELS.get(c, c)})
    return pd.DataFrame(rows)


def _by_year(df: pd.DataFrame, group_col: str | None = None,
             group_label_map: dict | None = None) -> pd.DataFrame:
    """Counts of papers per year, optionally split by another column.
    For sample_category we use the exploded long-form so multi-coded papers
    contribute to each of their categories."""
    if group_col == "sample_category":
        long = _explode_sample_category(df)
        long = long[long["year_num"].notna()]
        out = (long.groupby(["year_num", "sample_label"])
                    .size().reset_index(name="count"))
        out = out.rename(columns={"sample_label": "group"})
    elif group_col and group_col in df.columns:
        sub = df[df["year_num"].notna()].copy()
        sub["group"] = sub[group_col].map(group_label_map or {}).fillna(sub[group_col])
        sub = sub[sub["group"].astype(str).str.strip() != ""]
        out = sub.groupby(["year_num", "group"]).size().reset_index(name="count")
    else:
        sub = df[df["year_num"].notna()]
        out = sub.groupby("year_num").size().reset_index(name="count")
        out["group"] = "All"
    out = out.rename(columns={"year_num": "year"})
    out["year"] = out["year"].astype(int)
    return out


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------

def main() -> None:
    df = load_papers()

    st.title("📚 Database")
    st.caption(
        f"{len(df)} EEG studies on architecture, urbanism, and nature. "
        "Use the sidebar to filter; both tabs respond to the same filters."
    )

    # ---------- Sidebar filters (shared by both tabs) ----------
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

    # ---------- Apply filters ----------
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

    # ---------- Top-line descriptives (above the tabs, like InterBrainDB) ----------
    n_total = len(df)
    n_shown = len(f)
    n_series = pd.to_numeric(f.get("num_participants", pd.Series(dtype=str)), errors="coerce").dropna()
    if len(n_series):
        sd = float(n_series.std(ddof=1)) if len(n_series) > 1 else 0.0
        sem = sd / (len(n_series) ** 0.5) if len(n_series) > 1 else 0.0
        desc = (f"Mean = {n_series.mean():.1f} ± {sd:.1f} "
                f"(SEM = {sem:.2f}), min: {int(n_series.min())}, max: {int(n_series.max())}")
    else:
        desc = "no participant counts available for the current selection"

    st.markdown(f"**Total studies in database:** N = {n_total}")
    st.markdown(f"**Currently included studies:** N = {n_shown}")
    st.markdown(f"**Descriptives of sample size:** {desc}")

    st.divider()

    tab_overview, tab_plots = st.tabs(["📋 Data overview", "📈 Plots"])

    # ======================================================================
    # Tab 1: Data overview (table + per-paper detail)
    # ======================================================================
    with tab_overview:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Papers shown", n_shown)
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
        if n_shown == 0:
            st.info("No papers match the current filters.")
        else:
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

    # ======================================================================
    # Tab 2: Plots
    # ======================================================================
    with tab_plots:
        if n_shown == 0:
            st.info("No papers match the current filters: nothing to plot.")
            return

        st.caption(
            "💡 **Tip:** all charts respond to the sidebar filters. "
            "To save a figure, right-click the chart and choose *Save image as…* "
            "(menu wording varies by browser)."
        )

        # ------------------------------------------------------------------
        # 1. Publications over time (with optional stacked-bars by category)
        # ------------------------------------------------------------------
        st.subheader("Publications over time")
        split_options = {
            "None": (None, None),
            "Sample category (Architecture / Urbanism / Nature)": ("sample_category", None),
            "Setting (Lab / Real-world / Mixed)": ("lab_realworld_binary", LAB_LABELS),
            "EEG system (Stationary / Mobile)": ("eeg_system_mobile_stationary", MOBILE_LABELS),
        }
        choice = st.selectbox(
            "Choose a category to display as stacked bars:",
            options=list(split_options.keys()),
        )
        col_name, label_map = split_options[choice]
        timeline = _by_year(f, col_name, label_map)

        if timeline.empty:
            st.info("No year information for the current selection.")
        elif choice == "None":
            line = (alt.Chart(timeline)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("year:O", title="Year"),
                        y=alt.Y("count:Q", title="# of publications"),
                        tooltip=["year", "count"],
                    )
                    .properties(height=320))
            st.altair_chart(line, use_container_width=True)
        else:
            bars = (alt.Chart(timeline)
                    .mark_bar()
                    .encode(
                        x=alt.X("year:O", title="Year"),
                        y=alt.Y("count:Q", title="# of publications", stack="zero"),
                        color=alt.Color("group:N", title=choice.split(" (")[0]),
                        tooltip=["year", "group", "count"],
                    )
                    .properties(height=320))
            st.altair_chart(bars, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 2. Sample categories (multi-coded papers contribute to each)
        # ------------------------------------------------------------------
        st.subheader("Sample categories")
        st.caption(
            "Papers coded as more than one category (e.g. *Architecture + Urbanism*) "
            "are counted under each, so the bars sum to ≥ N."
        )
        long = _explode_sample_category(f)
        cat_counts = (long.groupby("sample_label").size()
                          .reset_index(name="count")
                          .sort_values("count", ascending=False))
        cat_chart = (alt.Chart(cat_counts)
                     .mark_bar()
                     .encode(
                         x=alt.X("sample_label:N", title="Category", sort="-y"),
                         y=alt.Y("count:Q", title="# of papers"),
                         color=alt.Color("sample_label:N", legend=None),
                         tooltip=["sample_label", "count"],
                     )
                     .properties(height=280))
        st.altair_chart(cat_chart, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 3. Lab vs real-world (overall + over time)
        # ------------------------------------------------------------------
        st.subheader("Lab vs real-world settings")
        st.caption("Tracks whether the field is moving from shielded-room studies into the wild.")
        if "lab_realworld_binary" in f.columns:
            lr = f.copy()
            lr["setting"] = lr["lab_realworld_binary"].map(LAB_LABELS).fillna("Unknown")
            lr = lr[lr["setting"].astype(str).str.strip() != ""]

            c1, c2 = st.columns([1, 2])
            with c1:
                overall = (lr.groupby("setting").size()
                              .reset_index(name="count")
                              .sort_values("count", ascending=False))
                ch = (alt.Chart(overall).mark_bar()
                      .encode(
                          x=alt.X("setting:N", title=None, sort="-y"),
                          y=alt.Y("count:Q", title="# of papers"),
                          color=alt.Color("setting:N", legend=None),
                          tooltip=["setting", "count"],
                      ).properties(height=260))
                st.altair_chart(ch, use_container_width=True)
            with c2:
                lr_year = lr[lr["year_num"].notna()].copy()
                lr_year["year"] = lr_year["year_num"].astype(int)
                ts = lr_year.groupby(["year", "setting"]).size().reset_index(name="count")
                ch2 = (alt.Chart(ts).mark_bar()
                       .encode(
                           x=alt.X("year:O", title="Year"),
                           y=alt.Y("count:Q", title="# of papers", stack="zero"),
                           color=alt.Color("setting:N", title="Setting"),
                           tooltip=["year", "setting", "count"],
                       ).properties(height=260))
                st.altair_chart(ch2, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 4. EEG system: mobile vs stationary
        # ------------------------------------------------------------------
        st.subheader("EEG hardware: mobile vs stationary")
        st.caption("A proxy for how far neuro-urbanism has moved beyond desktop amplifiers.")
        if "eeg_system_mobile_stationary" in f.columns:
            mob = f.copy()
            mob["system"] = (mob["eeg_system_mobile_stationary"].str.lower()
                                  .map({"stat": "Stationary", "mob": "Mobile"}).fillna("Unknown"))
            mob = mob[mob["system"] != "Unknown"]
            if not mob.empty:
                mob_year = mob[mob["year_num"].notna()].copy()
                mob_year["year"] = mob_year["year_num"].astype(int)
                ts = mob_year.groupby(["year", "system"]).size().reset_index(name="count")
                ch = (alt.Chart(ts).mark_bar()
                      .encode(
                          x=alt.X("year:O", title="Year"),
                          y=alt.Y("count:Q", title="# of papers", stack="zero"),
                          color=alt.Color("system:N", title="EEG system"),
                          tooltip=["year", "system", "count"],
                      ).properties(height=280))
                st.altair_chart(ch, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 5. Channel-count distribution
        # ------------------------------------------------------------------
        st.subheader("EEG channel count")
        st.caption("How many electrodes the field actually uses.")
        if f["num_channels_num"].notna().any():
            ch_df = f[["num_channels_num"]].dropna().rename(columns={"num_channels_num": "channels"})
            ch_df["channels"] = ch_df["channels"].astype(int)
            ch_chart = (alt.Chart(ch_df)
                        .mark_bar()
                        .encode(
                            x=alt.X("channels:Q", bin=alt.Bin(step=8), title="# of channels"),
                            y=alt.Y("count():Q", title="# of papers"),
                            tooltip=[alt.Tooltip("channels:Q", bin=alt.Bin(step=8)), "count():Q"],
                        )
                        .properties(height=260))
            st.altair_chart(ch_chart, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 6. Mobility heatmap (participant × system)
        # ------------------------------------------------------------------
        st.subheader("Mobility profile: participant × system")
        st.caption(
            "Each cell counts papers with that combination of participant mobility "
            "(0 = still, 4 = free locomotion) and EEG system mobility "
            "(0 = wired desktop, 4 = head-mounted with smartphone). "
            "Sparse top-right means few studies are doing free real-world recording with truly mobile gear."
        )
        if {"participant_mobility_score_num", "system_mobility_score_num"}.issubset(f.columns):
            heat = f.dropna(subset=["participant_mobility_score_num",
                                    "system_mobility_score_num"]).copy()
            if not heat.empty:
                heat["participant"] = heat["participant_mobility_score_num"].astype(int)
                heat["system"] = heat["system_mobility_score_num"].astype(int)
                grid = (heat.groupby(["participant", "system"])
                              .size().reset_index(name="count"))
                heat_chart = (alt.Chart(grid)
                              .mark_rect()
                              .encode(
                                  x=alt.X("system:O", title="System mobility (0–4)"),
                                  y=alt.Y("participant:O", title="Participant mobility (0–4)",
                                          sort="descending"),
                                  color=alt.Color("count:Q", title="# of papers",
                                                  scale=alt.Scale(scheme="blues")),
                                  tooltip=["participant", "system", "count"],
                              )
                              .properties(height=320))
                text = (alt.Chart(grid)
                        .mark_text(baseline="middle")
                        .encode(
                            x="system:O",
                            y=alt.Y("participant:O", sort="descending"),
                            text="count:Q",
                            color=alt.condition("datum.count > 8",
                                                alt.value("white"), alt.value("black")),
                        ))
                st.altair_chart(heat_chart + text, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 7. Replicability score
        # ------------------------------------------------------------------
        st.subheader("Replicability")
        st.caption(
            "Editor-assigned score from the rubric in CONTRIBUTING.md "
            "(0 = code+data+methods all available, 3 = not replicable from the paper alone). "
            "Lower is better."
        )
        if "replicability_score_num" in f.columns and f["replicability_score_num"].notna().any():
            rep = f["replicability_score_num"].dropna().astype(int).reset_index(drop=True)
            rep_df = rep.value_counts().sort_index().reset_index()
            rep_df.columns = ["replicability_score", "count"]
            rep_chart = (alt.Chart(rep_df)
                         .mark_bar()
                         .encode(
                             x=alt.X("replicability_score:O", title="Replicability score"),
                             y=alt.Y("count:Q", title="# of papers"),
                             tooltip=["replicability_score", "count"],
                         )
                         .properties(height=260))
            st.altair_chart(rep_chart, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 8. Sample size distribution
        # ------------------------------------------------------------------
        st.subheader("Sample size distribution")
        st.caption("Long-tailed by design: a few large studies, many small ones. "
                   "Bins capped at N = 200; anything larger lives in the rightmost bin.")
        n_df = pd.to_numeric(f.get("num_participants"), errors="coerce").dropna()
        if len(n_df):
            n_df = n_df.clip(upper=200).astype(int).reset_index(drop=True)
            ndf = pd.DataFrame({"n_participants": n_df})
            n_chart = (alt.Chart(ndf)
                       .mark_bar()
                       .encode(
                           x=alt.X("n_participants:Q",
                                   bin=alt.Bin(step=10),
                                   title="N participants (capped at 200)"),
                           y=alt.Y("count():Q", title="# of papers"),
                           tooltip=[alt.Tooltip("n_participants:Q", bin=alt.Bin(step=10)),
                                    "count():Q"],
                       )
                       .properties(height=260))
            st.altair_chart(n_chart, use_container_width=True)


if __name__ == "__main__":
    main()
