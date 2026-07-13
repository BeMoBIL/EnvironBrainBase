"""
EEG Systems lookup page.

Shows the canonical EEG system reference table: system name, manufacturer,
channel count, mobility score (0-4), and a link to the product page.

The mobility scores here drive the system_mobility_score column shown in the
Database page — no manual per-paper entry required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_eeg_systems  # noqa: E402


# ---------------------------------------------------------------------------
# Score metadata
# ---------------------------------------------------------------------------

SCORE_LABELS = {
    0: "Wired / stationary",
    1: "Waist-mounted + cables",
    2: "Waist-mounted, wireless",
    3: "Head-mounted + rucksack",
    4: "Fully head-mounted",
}

SCORE_COLOR = {
    0: "#c0392b",
    1: "#e67e22",
    2: "#f1c40f",
    3: "#27ae60",
    4: "#2980b9",
}

SCORE_DESCRIPTION = {
    0: "All equipment off-body; participant tethered via cabling.",
    1: "Amplifier waist- or back-mounted; cabled to EEG cap.",
    2: "All equipment waist-mounted; wireless link to EEG cap.",
    3: "Head-mounted EEG; additional equipment in rucksack or off-body.",
    4: "Fully head-mounted; wireless to smartphone / tablet only.",
}

# ---------------------------------------------------------------------------
# Score badge HTML
# ---------------------------------------------------------------------------


def _score_badge(score: int | None) -> str:
    if score is None:
        return "<span style='color:#aaa'>—</span>"
    color = SCORE_COLOR.get(score, "#888")
    label = SCORE_LABELS.get(score, str(score))
    dots = "●" * (score + 1) + "○" * (4 - score)
    return (
        f"<span style='background:{color};color:#fff;padding:2px 8px;"
        f"border-radius:12px;font-weight:600;font-size:0.85rem;'>"
        f"{score} &nbsp;{dots}</span>"
        f"<span style='color:#666;font-size:0.8rem;margin-left:6px'>{label}</span>"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    st.title("🔬 EEG Systems")
    st.markdown(
        "Canonical reference table of EEG systems used in neuro-urbanism research. "
        "The **mobility score** (0–4) is automatically applied to every paper in the "
        "Database that names that system — no manual per-paper entry needed."
    )

    # Score legend
    with st.expander("Mobility score key", expanded=False):
        cols = st.columns(5)
        for score, col in zip(range(5), cols):
            color = SCORE_COLOR[score]
            with col:
                st.markdown(
                    f"<div style='background:{color};color:#fff;border-radius:8px;"
                    f"padding:10px;text-align:center;font-weight:700;font-size:1.1rem'>"
                    f"{score}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(SCORE_DESCRIPTION[score])

    st.divider()

    # Load data
    systems = load_eeg_systems()
    rows = list(systems.values())

    if not rows:
        st.warning("No EEG systems found in data/eeg_systems.yaml.")
        return

    df = pd.DataFrame(rows)

    # Sidebar filters
    st.sidebar.header("Filter systems")
    score_filter = st.sidebar.multiselect(
        "Mobility score",
        options=list(range(5)),
        format_func=lambda s: f"{s} – {SCORE_LABELS[s]}",
    )
    manufacturer_options = sorted(df["manufacturer"].dropna().unique())
    mfr_filter = st.sidebar.multiselect("Manufacturer", options=manufacturer_options)
    name_query = st.sidebar.text_input("Search by name", "")

    fdf = df.copy()
    if score_filter:
        fdf = fdf[fdf["mobility_score"].isin(score_filter)]
    if mfr_filter:
        fdf = fdf[fdf["manufacturer"].isin(mfr_filter)]
    if name_query.strip():
        q = name_query.strip().lower()
        fdf = fdf[fdf["name"].str.lower().str.contains(q, na=False)]

    st.caption(f"Showing {len(fdf)} of {len(df)} systems")

    # Sort
    sort_col = st.selectbox(
        "Sort by",
        ["name", "manufacturer", "mobility_score", "channels"],
        index=2,
        format_func=lambda c: {
            "name": "Name",
            "manufacturer": "Manufacturer",
            "mobility_score": "Mobility score",
            "channels": "Channels",
        }.get(c, c),
    )
    fdf = fdf.sort_values(sort_col, ascending=(sort_col != "mobility_score"))

    # Render as HTML table with score badges and links
    rows_html = []
    for _, row in fdf.iterrows():
        name = row.get("name", "")
        mfr = row.get("manufacturer", "—")
        ch = row.get("channels", "—")
        score = row.get("mobility_score")
        link = row.get("link", "")
        notes = row.get("notes", "")

        try:
            score = int(score)
        except (TypeError, ValueError):
            score = None

        badge = _score_badge(score)
        link_html = (
            f"<a href='{link}' target='_blank' style='color:#2980b9'>↗ Product page</a>"
            if link
            else "<span style='color:#ccc'>—</span>"
        )
        notes_html = (
            f"<span style='color:#666;font-size:0.8rem'>{notes}</span>" if notes else ""
        )

        rows_html.append(
            f"<tr>"
            f"<td style='padding:8px 12px;font-weight:600'>{name}</td>"
            f"<td style='padding:8px 12px'>{mfr}</td>"
            f"<td style='padding:8px 12px;text-align:center'>{ch}</td>"
            f"<td style='padding:8px 12px'>{badge}</td>"
            f"<td style='padding:8px 12px'>{link_html}</td>"
            f"<td style='padding:8px 12px'>{notes_html}</td>"
            f"</tr>"
        )

    table_html = (
        "<table style='width:100%;border-collapse:collapse;font-size:0.9rem'>"
        "<thead><tr style='border-bottom:2px solid #e0e0e0;text-align:left'>"
        "<th style='padding:8px 12px'>System</th>"
        "<th style='padding:8px 12px'>Manufacturer</th>"
        "<th style='padding:8px 12px;text-align:center'>Channels</th>"
        "<th style='padding:8px 12px'>Mobility score</th>"
        "<th style='padding:8px 12px'>Link</th>"
        "<th style='padding:8px 12px'>Notes</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody></table>"
    )

    st.markdown(table_html, unsafe_allow_html=True)

    st.divider()
    st.info(
        "To add or update a system, edit **data/eeg_systems.yaml** and submit a pull request. "
        "Changes take effect immediately on the next app reload."
    )


main()
