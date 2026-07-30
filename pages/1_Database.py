"""
EnvironBrainBase: Database (browse + filter + plots) page.

Two tabs, both driven by the same sidebar filters:
  1. Data overview: descriptives + browsable table + per-paper detail.
  2. Plots: publication trends, methodology distributions, mobility heatmap.
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_csv, load_eeg_systems, lookup_eeg_system  # noqa: E402

DATA_PATH = Path(__file__).parent.parent / "data" / "papers.csv"

# ---------------------------------------------------------------------------
# EEG system lookup (loaded once at import time)
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def _get_eeg_systems() -> dict:
    return load_eeg_systems()


# ---------------------------------------------------------------------------
# Replicability scoring
# ---------------------------------------------------------------------------

# Necessary fields (N, max = 9).
# Column names are the canonical CSV names (see data/schema_rename_map.json).
#
# Offline filter criterion: counted as ONE necessary item satisfied when
#   - offline_filters is present, OR
#   - both offline_highpass_hz AND offline_lowpass_hz are present.
# This "either/or" check is handled in _score_row; the three columns are
# NOT listed in _NECESSARY_COLS (which only contains simple single-field checks).
_NECESSARY_COLS: list[str] = [
    "sampling_rate_hz",  # SR_in_Hz
    "filters_amp",  # online / hardware filter settings
    "online_filters",  # were online filters applied?
    "num_channels",
    "electrode_type",
    "electrode_locations",
    "reference_electrode",  # reference
    "artifact_rejection",
]

_N_MAX: int = (
    len(_NECESSARY_COLS) + 1
)  # +1 for the offline-filter either/or criterion = 9

# Good-to-have fields (G, max = 4).
_GOOD_COLS: list[str] = [
    "channel_interpolation",
    "impedance",  # Impedance
    "eeg_company",  # EEG_company
    "eeg_system",  # EEG_system
]
_G_MAX: int = len(_GOOD_COLS)  # 4

# Values treated as absent (case-insensitive, after strip)
_ABSENT: frozenset[str] = frozenset(
    {
        "",
        "na",
        "n/a",
        "nan",
        "nr",
        "unknown",
        "none",
        "0",
        "0.0",
        "na / na",
        "na/na",
        "not reported",
        "not available",
        "not applicable",
    }
)


def _is_present(val: object) -> bool:
    """Return True when a field carries real information."""
    if pd.isna(val):
        return False
    return str(val).strip().lower() not in _ABSENT


def _offline_filter_present(row: "pd.Series") -> bool:
    """Offline filter criterion: offline_filters present OR both HP+LP cutoffs present."""
    if _is_present(row.get("offline_filters", "")):
        return True
    return _is_present(row.get("offline_highpass_hz", "")) and _is_present(
        row.get("offline_lowpass_hz", "")
    )


def _score_row(row: "pd.Series") -> tuple[float, str]:
    n = sum(_is_present(row.get(c, "")) for c in _NECESSARY_COLS)
    n += int(_offline_filter_present(row))  # add the offline-filter either/or criterion
    g = sum(_is_present(row.get(c, "")) for c in _GOOD_COLS)

    # Zone-locked scoring (N_MAX = 9, G_MAX = 4).
    #   N <= 3  ->  0-39   (zone 1)
    #   N 4-8   ->  40-79  (zone 2)
    #   N = 9   ->  80-100 (zone 3, "Replicable")
    if n <= 3:
        score = round((n / 3) * 39)
    elif n <= 8:
        score = round(40 + ((n - 4) / 4) * 39)
    else:  # n == 9
        score = round(80 + (g / _G_MAX) * 20)

    label = "Replicable" if n == _N_MAX else "Not Replicable"
    return float(score), label


def compute_replicability(df: pd.DataFrame) -> pd.DataFrame:
    """Compute replicability score/label dynamically and insert them as early columns."""
    scores, labels = zip(*df.apply(_score_row, axis=1))
    df = df.copy()
    df["replicability_score"] = scores
    df["replicability_label"] = labels
    # Move both columns to position 2 (right after authors_short and year)
    cols = [
        c for c in df.columns if c not in ("replicability_score", "replicability_label")
    ]
    cols = cols[:2] + ["replicability_score", "replicability_label"] + cols[2:]
    return df[cols]


@st.cache_data(show_spinner=False)
def load_papers() -> pd.DataFrame:
    df = load_csv(DATA_PATH)

    # Normalise eeg_system_mobile_stationary to "stat" / "mobile" / ""
    _MOB_NORM = {
        "stat": "stat",
        "stat - hmd": "stat",
        "mobile": "mobile",
        "mob": "mobile",
        "mobile & stat": "mobile",
    }
    df["eeg_system_mobile_stationary"] = (
        df["eeg_system_mobile_stationary"]
        .str.lower()
        .str.strip()
        .map(_MOB_NORM)
        .fillna("")
    )

    df = compute_replicability(df)

    # Preserve original editor replicability (1-3 scale)
    df["replicability_raw"] = df["replicability_score"]

    # Derive system_mobility_score from the canonical EEG system lookup.
    # Falls back to the CSV value only when the system name is not in the YAML.
    systems = _get_eeg_systems()

    def _lookup_score(row: pd.Series) -> str:
        info = lookup_eeg_system(str(row.get("eeg_system", "")), systems)
        if info:
            return str(info["mobility_score"])
        # Fallback: use the raw CSV score if present
        return str(row.get("system_mobility_score", ""))

    df["system_mobility_score"] = df.apply(_lookup_score, axis=1)

    for col in (
        "year",
        "num_participants",
        "num_channels",
        "sampling_rate_hz",
        "participant_mobility_score",
        "system_mobility_score",
        "replicability_score",
        "replicability_raw",
    ):
        if col in df.columns:
            df[col + "_num"] = pd.to_numeric(df[col], errors="coerce")
    return df


SAMPLE_LABELS = {"1": "Architecture", "2": "Urbanism", "3": "Nature"}
LAB_LABELS = {"1": "Lab", "2": "Real-world", "3": "Mixed"}
MOBILE_LABELS = {"stat": "Stationary", "mobile": "Mobile"}


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
        codes = [
            c.strip() for c in str(r.get("sample_category", "")).split(",") if c.strip()
        ]
        if not codes:
            rows.append({**r.to_dict(), "sample_label": "Uncoded"})
        else:
            for c in codes:
                rows.append({**r.to_dict(), "sample_label": SAMPLE_LABELS.get(c, c)})
    return pd.DataFrame(rows)


def _by_year(
    df: pd.DataFrame, group_col: str | None = None, group_label_map: dict | None = None
) -> pd.DataFrame:
    """Counts of papers per year, optionally split by another column.
    For sample_category we use the exploded long-form so multi-coded papers
    contribute to each of their categories."""
    if group_col == "sample_category":
        long = _explode_sample_category(df)
        long = long[long["year_num"].notna()]
        out = (
            long.groupby(["year_num", "sample_label"]).size().reset_index(name="count")
        )
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

    year_min = (
        int(df["year_num"].min(skipna=True)) if df["year_num"].notna().any() else 1980
    )
    year_max = (
        int(df["year_num"].max(skipna=True)) if df["year_num"].notna().any() else 2026
    )
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

    chan_min = (
        int(df["num_channels_num"].min(skipna=True))
        if df["num_channels_num"].notna().any()
        else 1
    )
    chan_max = (
        int(df["num_channels_num"].max(skipna=True))
        if df["num_channels_num"].notna().any()
        else 256
    )
    chan_range = st.sidebar.slider(
        "Number of EEG channels", chan_min, chan_max, (chan_min, chan_max)
    )

    text_query = st.sidebar.text_input("Title / authors search", "")

    # ---------- Apply filters ----------
    f = df.copy()
    f = f[f["year_num"].between(year_range[0], year_range[1]) | f["year_num"].isna()]

    if sample_pick:
        mask = f["sample_category"].apply(
            lambda s: any(p in [x.strip() for x in s.split(",")] for p in sample_pick)
            if s
            else False
        )
        f = f[mask]
    if lab_pick:
        f = f[f["lab_realworld_binary"].isin(lab_pick)]
    if mobile_pick:
        f = f[
            f["eeg_system_mobile_stationary"]
            .str.lower()
            .isin([m.lower() for m in mobile_pick])
        ]
    f = f[
        f["num_channels_num"].between(chan_range[0], chan_range[1])
        | f["num_channels_num"].isna()
    ]
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
    n_series = pd.to_numeric(
        f.get("num_participants", pd.Series(dtype=str)), errors="coerce"
    ).dropna()
    if len(n_series):
        sd = float(n_series.std(ddof=1)) if len(n_series) > 1 else 0.0
        sem = sd / (len(n_series) ** 0.5) if len(n_series) > 1 else 0.0
        desc = (
            f"Mean = {n_series.mean():.1f} ± {sd:.1f} "
            f"(SEM = {sem:.2f}), min: {int(n_series.min())}, max: {int(n_series.max())}"
        )
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
        c3.metric(
            "Architecture",
            int((f["sample_category"].str.contains("1", na=False)).sum()),
        )
        c4.metric(
            "Urbanism", int((f["sample_category"].str.contains("2", na=False)).sum())
        )

        st.divider()

        # ------------------------------------------------------------------
        # HTML table with inline EEG system hover tooltips
        # ------------------------------------------------------------------
        import html as _html
        import streamlit.components.v1 as _components

        _SCORE_COLOR = {
            0: "#c0392b",
            1: "#e67e22",
            2: "#f1c40f",
            3: "#27ae60",
            4: "#2980b9",
        }
        _SCORE_LABEL = {
            0: "Wired / stationary",
            1: "Waist-mounted + cables",
            2: "Waist-mounted, wireless",
            3: "Head-mounted + rucksack",
            4: "Fully head-mounted",
        }
        _sys_lk = _get_eeg_systems()

        def _mob_badge(score_str):
            try:
                s = int(float(score_str))
                c = _SCORE_COLOR.get(s, "#888")
                dots = "●" * (s + 1) + "○" * (4 - s)
                return f"<span style='background:{c};color:#fff;padding:1px 7px;border-radius:10px;font-size:0.78rem;font-weight:600'>{s} {dots}</span>"
            except (ValueError, TypeError):
                return f"<span style='color:#aaa'>{_html.escape(str(score_str))}</span>"

        def _eeg_cell(sys_name, score_str):
            if not sys_name or sys_name.lower() in ("na", "n/a", ""):
                return "<span style='color:#bbb'>—</span>"
            info = lookup_eeg_system(sys_name, _sys_lk)
            score_int = None
            try:
                score_int = int(info.get("mobility_score", "x"))
            except (ValueError, TypeError):
                pass
            dot_color = (
                _SCORE_COLOR.get(score_int, "#aaa") if score_int is not None else "#aaa"
            )
            mfr = _html.escape(str(info.get("manufacturer", "—")))
            ch = _html.escape(str(info.get("channels", "—")))
            link = info.get("link", "")
            notes = _html.escape(str(info.get("notes", "")))
            slabel = (
                _SCORE_LABEL.get(score_int, "unknown")
                if score_int is not None
                else "unknown"
            )
            link_part = (
                f"<a href='{link}' target='_blank' style='color:#93c5fd'>↗ product page</a>"
                if link
                else ""
            )
            notes_part = (
                f"<em style='color:#aaa;font-size:0.78rem'>{notes}</em><br>"
                if notes
                else ""
            )
            tip = (
                f"<strong>{_html.escape(sys_name)}</strong><br>"
                f"Manufacturer: {mfr}<br>"
                f"Channels: {ch}<br>"
                f"Mobility: {score_int if score_int is not None else '?'} – {slabel}<br>"
                f"{notes_part}{link_part}"
            )
            tip_escaped = tip.replace("'", "&#39;").replace('"', "&quot;")
            return (
                f"<span class='eeg-h' data-tip=\"{tip_escaped}\" "
                f"style='cursor:default;white-space:nowrap'>"
                f"<span style='display:inline-block;width:9px;height:9px;border-radius:50%;"
                f"background:{dot_color};margin-right:5px;vertical-align:middle'></span>"
                f"{_html.escape(sys_name)}</span>"
            )

        def _truncate(s, n=60):
            s = str(s)
            return _html.escape(s[:n] + "…") if len(s) > n else _html.escape(s)

        header = (
            "<tr style='position:sticky;top:0;background:#f4f4f2;z-index:2'>"
            "<th>Authors</th><th>Year</th><th>Title</th><th>Journal</th>"
            "<th>Cat</th><th>N</th><th>Ch</th>"
            "<th>EEG System</th><th>Setting</th><th>DOI</th></tr>"
        )
        _LAB = {
            "1": "Lab",
            "2": "Real-world",
            "3": "Mixed",
            "stat": "Stationary",
            "mob": "Mobile",
        }
        _CAT = {"1": "Arch", "2": "Urban", "3": "Nature"}
        rows_html = []
        for _, row in f.iterrows():
            cat_raw = str(row.get("sample_category", ""))
            cat_disp = "/".join(
                _CAT.get(c.strip(), c.strip()) for c in cat_raw.split(",") if c.strip()
            )
            doi = str(row.get("doi_link", "")).strip()
            doi_html = (
                f"<a href='{_html.escape(doi)}' target='_blank' style='color:#2980b9'>↗</a>"
                if doi and doi.lower() not in ("", "na")
                else ""
            )
            setting = _LAB.get(
                str(row.get("lab_realworld_binary", "")).strip(),
                str(row.get("lab_realworld_binary", "")),
            )
            rows_html.append(
                f"<tr>"
                f"<td style='white-space:nowrap'>{_truncate(row.get('authors_short', ''), 30)}</td>"
                f"<td>{_html.escape(str(row.get('year', '')))}</td>"
                f"<td class='title-cell'>{_truncate(row.get('title', ''), 70)}</td>"
                f"<td>{_truncate(row.get('journal', ''), 25)}</td>"
                f"<td style='text-align:center'>{_html.escape(cat_disp)}</td>"
                f"<td style='text-align:center'>{_html.escape(str(row.get('num_participants', '')))}</td>"
                f"<td style='text-align:center'>{_html.escape(str(row.get('num_channels', '')))}</td>"
                f"<td>{_eeg_cell(str(row.get('eeg_system', '')).strip(), str(row.get('system_mobility_score', '')))}</td>"
                f"<td style='white-space:nowrap'>{_html.escape(str(setting))}</td>"
                f"<td style='text-align:center'>{doi_html}</td>"
                f"</tr>"
            )

        table_html = (
            "<div id='float-tip'></div>"
            "<div style='max-height:540px;overflow-y:auto;overflow-x:auto'>"
            "<table style='width:100%;border-collapse:collapse;font-size:0.82rem'>"
            f"<thead>{header}</thead>"
            "<tbody style='line-height:1.4'>"
            + "".join(rows_html)
            + "</tbody></table></div>"
        )

        css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&display=swap');
*, body {
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI",
               Roboto, Helvetica, Arial, sans-serif;
  font-size: 14px;
  color: #1a1a1a;
  box-sizing: border-box;
  margin: 0; padding: 0;
}
body { background: transparent; padding: 4px 0; }
table { width: 100%; border-collapse: collapse; }
table td, table th {
  padding: 6px 10px;
  border-bottom: 1px solid #e8e8e8;
  vertical-align: middle;
}
table th {
  font-weight: 600;
  font-size: 13px;
  color: #444;
  border-bottom: 2px solid #ccc;
  padding: 8px 10px;
  background: #f4f4f2;
}
table tr:hover td { background: #f0f4ff; }
.title-cell { max-width: 340px; }
#float-tip {
  display: none;
  position: fixed;
  background: #1e1e2e;
  color: #f0f0f0;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  max-width: 280px;
  z-index: 9999;
  box-shadow: 0 4px 18px rgba(0,0,0,0.4);
  pointer-events: none;
}
</style>"""

        js = """
<script>
(function() {
  const tip = document.getElementById('float-tip');
  function attach() {
    document.querySelectorAll('.eeg-h').forEach(function(el) {
      if (el._tipBound) return;
      el._tipBound = true;
      el.addEventListener('mouseenter', function() {
        tip.innerHTML = this.dataset.tip;
        tip.style.display = 'block';
      });
      el.addEventListener('mousemove', function(e) {
        let x = e.clientX + 14, y = e.clientY - 10;
        if (x + 290 > window.innerWidth) x = e.clientX - 300;
        if (y + tip.offsetHeight > window.innerHeight) y = e.clientY - tip.offsetHeight - 6;
        tip.style.left = x + 'px';
        tip.style.top  = y + 'px';
      });
      el.addEventListener('mouseleave', function() { tip.style.display = 'none'; });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }
})();
</script>"""

        _components.html(css + table_html + js, height=560, scrolling=False)

        st.divider()
        st.subheader("Paper detail")
        if n_shown == 0:
            st.info("No papers match the current filters.")
        else:

            def _label(row: pd.Series) -> str:
                title = (row.get("title", "") or "").strip()
                return f"{row.get('authors_short', '')} ({row.get('year', '')}): {title[:80]}"

            options = f.index.tolist()
            chosen = st.selectbox(
                "Pick a paper to inspect",
                options=options,
                format_func=lambda i: _label(f.loc[i]),
            )
            if chosen is not None:
                row = f.loc[chosen]

                # EEG system info card
                sys_name = str(row.get("eeg_system", "")).strip()
                if sys_name and sys_name.lower() not in ("", "na", "n/a"):
                    systems_lookup = _get_eeg_systems()
                    info = lookup_eeg_system(sys_name, systems_lookup)
                    if info:
                        _SCORE_COLOR = {
                            0: "#c0392b",
                            1: "#e67e22",
                            2: "#f1c40f",
                            3: "#27ae60",
                            4: "#2980b9",
                        }
                        _SCORE_LABEL = {
                            0: "Wired / stationary",
                            1: "Waist-mounted + cables",
                            2: "Waist-mounted, wireless",
                            3: "Head-mounted + rucksack",
                            4: "Fully head-mounted",
                        }
                        score = info.get("mobility_score")
                        try:
                            score_int = int(score)
                            color = _SCORE_COLOR.get(score_int, "#888")
                            score_text = (
                                f"{score_int} – {_SCORE_LABEL.get(score_int, '')}"
                            )
                        except (TypeError, ValueError):
                            color = "#888"
                            score_text = "Unknown"

                        link = info.get("link", "")
                        link_html = (
                            f"<a href='{link}' target='_blank'>↗ Product page</a>"
                            if link
                            else ""
                        )
                        notes = info.get("notes", "")
                        st.markdown(
                            f"""
<div style='border-left:4px solid {color};padding:10px 16px;background:#f8f8ff;
            border-radius:0 8px 8px 0;margin-bottom:12px;font-size:0.88rem;'>
  <strong>🔬 EEG System: {info.get("name", sys_name)}</strong><br>
  Manufacturer: {info.get("manufacturer", "—")} &nbsp;|&nbsp;
  Channels: {info.get("channels", "—")} &nbsp;|&nbsp;
  <span style='background:{color};color:#fff;padding:1px 8px;border-radius:10px;
               font-weight:600'>&nbsp;Mobility {score_text}&nbsp;</span>
  {"&nbsp;|&nbsp;" + link_html if link_html else ""}
  {"<br><em style='color:#666'>" + notes + "</em>" if notes else ""}
</div>
""",
                            unsafe_allow_html=True,
                        )

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
            "Sample category (Architecture / Urbanism / Nature)": (
                "sample_category",
                None,
            ),
            "Setting (Lab / Real-world / Mixed)": ("lab_realworld_binary", LAB_LABELS),
            "EEG system (Stationary / Mobile)": (
                "eeg_system_mobile_stationary",
                MOBILE_LABELS,
            ),
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
            line = (
                alt.Chart(timeline)
                .mark_line(point=True)
                .encode(
                    x=alt.X("year:O", title="Year"),
                    y=alt.Y("count:Q", title="# of publications"),
                    tooltip=["year", "count"],
                )
                .properties(height=320)
            )
            st.altair_chart(line, use_container_width=True)
        else:
            bars = (
                alt.Chart(timeline)
                .mark_bar()
                .encode(
                    x=alt.X("year:O", title="Year"),
                    y=alt.Y("count:Q", title="# of publications", stack="zero"),
                    color=alt.Color("group:N", title=choice.split(" (")[0]),
                    tooltip=["year", "group", "count"],
                )
                .properties(height=320)
            )
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
        cat_counts = (
            long.groupby("sample_label")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        cat_chart = (
            alt.Chart(cat_counts)
            .mark_bar()
            .encode(
                x=alt.X("sample_label:N", title="Category", sort="-y"),
                y=alt.Y("count:Q", title="# of papers"),
                color=alt.Color("sample_label:N", legend=None),
                tooltip=["sample_label", "count"],
            )
            .properties(height=280)
        )
        st.altair_chart(cat_chart, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 3. Lab vs real-world (overall + over time)
        # ------------------------------------------------------------------
        st.subheader("Lab vs real-world settings")
        st.caption(
            "Tracks whether the field is moving from shielded-room studies into the wild."
        )
        if "lab_realworld_binary" in f.columns:
            lr = f.copy()
            lr["setting"] = lr["lab_realworld_binary"].map(LAB_LABELS).fillna("Unknown")
            lr = lr[lr["setting"].astype(str).str.strip() != ""]

            c1, c2 = st.columns([1, 2])
            with c1:
                overall = (
                    lr.groupby("setting")
                    .size()
                    .reset_index(name="count")
                    .sort_values("count", ascending=False)
                )
                ch = (
                    alt.Chart(overall)
                    .mark_bar()
                    .encode(
                        x=alt.X("setting:N", title=None, sort="-y"),
                        y=alt.Y("count:Q", title="# of papers"),
                        color=alt.Color("setting:N", legend=None),
                        tooltip=["setting", "count"],
                    )
                    .properties(height=260)
                )
                st.altair_chart(ch, use_container_width=True)
            with c2:
                lr_year = lr[lr["year_num"].notna()].copy()
                lr_year["year"] = lr_year["year_num"].astype(int)
                ts = (
                    lr_year.groupby(["year", "setting"])
                    .size()
                    .reset_index(name="count")
                )
                ch2 = (
                    alt.Chart(ts)
                    .mark_bar()
                    .encode(
                        x=alt.X("year:O", title="Year"),
                        y=alt.Y("count:Q", title="# of papers", stack="zero"),
                        color=alt.Color("setting:N", title="Setting"),
                        tooltip=["year", "setting", "count"],
                    )
                    .properties(height=260)
                )
                st.altair_chart(ch2, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 4. EEG system: mobile vs stationary
        # ------------------------------------------------------------------
        st.subheader("EEG hardware: mobile vs stationary")
        st.caption(
            "A proxy for how far neuro-urbanism has moved beyond desktop amplifiers."
        )
        if "eeg_system_mobile_stationary" in f.columns:
            mob = f.copy()
            mob["system"] = (
                mob["eeg_system_mobile_stationary"]
                .str.lower()
                .map({"stat": "Stationary", "mob": "Mobile"})
                .fillna("Unknown")
            )
            mob = mob[mob["system"] != "Unknown"]
            if not mob.empty:
                mob_year = mob[mob["year_num"].notna()].copy()
                mob_year["year"] = mob_year["year_num"].astype(int)
                ts = (
                    mob_year.groupby(["year", "system"])
                    .size()
                    .reset_index(name="count")
                )
                ch = (
                    alt.Chart(ts)
                    .mark_bar()
                    .encode(
                        x=alt.X("year:O", title="Year"),
                        y=alt.Y("count:Q", title="# of papers", stack="zero"),
                        color=alt.Color("system:N", title="EEG system"),
                        tooltip=["year", "system", "count"],
                    )
                    .properties(height=280)
                )
                st.altair_chart(ch, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 5. Channel-count distribution
        # ------------------------------------------------------------------
        st.subheader("EEG channel count")
        st.caption("How many electrodes the field actually uses.")
        if f["num_channels_num"].notna().any():
            ch_df = (
                f[["num_channels_num"]]
                .dropna()
                .rename(columns={"num_channels_num": "channels"})
            )
            ch_df["channels"] = ch_df["channels"].astype(int)
            ch_chart = (
                alt.Chart(ch_df)
                .mark_bar()
                .encode(
                    x=alt.X("channels:Q", bin=alt.Bin(step=8), title="# of channels"),
                    y=alt.Y("count():Q", title="# of papers"),
                    tooltip=[
                        alt.Tooltip("channels:Q", bin=alt.Bin(step=8)),
                        "count():Q",
                    ],
                )
                .properties(height=260)
            )
            st.altair_chart(ch_chart, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 6. Mobility heatmap (participant x system)
        # ------------------------------------------------------------------
        st.subheader("Mobility profile: participant x system")
        st.caption(
            "Each cell counts papers with that combination of participant mobility "
            "(0 = still, 4 = free locomotion) and EEG system mobility "
            "(0 = wired desktop, 4 = head-mounted with smartphone). "
        )
        if {"participant_mobility_score_num", "system_mobility_score_num"}.issubset(
            f.columns
        ):
            heat = f.dropna(
                subset=["participant_mobility_score_num", "system_mobility_score_num"]
            ).copy()
            heat = heat[heat["system_mobility_score_num"].between(0, 4)]
            heat = heat[heat["participant_mobility_score_num"].between(0, 4)]
            if not heat.empty:
                heat["participant"] = heat["participant_mobility_score_num"].astype(int)
                heat["system"] = heat["system_mobility_score_num"].astype(int)
                grid = (
                    heat.groupby(["participant", "system"])
                    .size()
                    .reset_index(name="count")
                )
                heat_chart = (
                    alt.Chart(grid)
                    .mark_rect()
                    .encode(
                        x=alt.X("system:O", title="System mobility (0-4)"),
                        y=alt.Y(
                            "participant:O",
                            title="Participant mobility (0-4)",
                            sort="descending",
                        ),
                        color=alt.Color(
                            "count:Q",
                            title="# of papers",
                            scale=alt.Scale(scheme="blues"),
                        ),
                        tooltip=["participant", "system", "count"],
                    )
                    .properties(height=320)
                )
                text_layer = (
                    alt.Chart(grid)
                    .mark_text(baseline="middle")
                    .encode(
                        x="system:O",
                        y=alt.Y("participant:O", sort="descending"),
                        text="count:Q",
                        color=alt.condition(
                            "datum.count > 8", alt.value("white"), alt.value("black")
                        ),
                    )
                )
                st.altair_chart(heat_chart + text_layer, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 7. Replicability score
        # ------------------------------------------------------------------
        st.subheader("Replicability")
        st.caption(
            "Editor-assigned score: 1 = fully replicable, 2 = partially, 3 = not replicable from the paper alone. Lower is better."
        )
        if (
            "replicability_raw_num" in f.columns
            and f["replicability_raw_num"].notna().any()
        ):
            rep = f["replicability_raw_num"].dropna().astype(int).reset_index(drop=True)
            rep_df = rep.value_counts().sort_index().reset_index()
            rep_df.columns = ["replicability_score", "count"]
            rep_chart = (
                alt.Chart(rep_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "replicability_score:O", title="Replicability (1=best, 3=worst)"
                    ),
                    y=alt.Y("count:Q", title="# of papers"),
                    tooltip=["replicability_score", "count"],
                )
                .properties(height=260)
            )
            st.altair_chart(rep_chart, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # 8. Sample size distribution
        # ------------------------------------------------------------------
        st.subheader("Sample size distribution")
        st.caption("Long-tailed by design. Bins capped at N=200.")
        n_df = pd.to_numeric(f.get("num_participants"), errors="coerce").dropna()
        if len(n_df):
            n_df = n_df.clip(upper=200).astype(int).reset_index(drop=True)
            ndf = pd.DataFrame({"n_participants": n_df})
            n_chart = (
                alt.Chart(ndf)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "n_participants:Q",
                        bin=alt.Bin(step=10),
                        title="N participants (capped at 200)",
                    ),
                    y=alt.Y("count():Q", title="# of papers"),
                    tooltip=[
                        alt.Tooltip("n_participants:Q", bin=alt.Bin(step=10)),
                        "count():Q",
                    ],
                )
                .properties(height=260)
            )
            st.altair_chart(n_chart, use_container_width=True)


main()
