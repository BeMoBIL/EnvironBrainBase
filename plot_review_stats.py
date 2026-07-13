"""
Publication-quality SVG figures for:
"Before the evidence is built: A credibility crisis in EEG Research
in Environmental Neuroscience"

Generates one SVG per thematic section into figures/

Usage:
    python plot_review_stats.py
    python plot_review_stats.py --csv data/papers.csv --out figures
"""

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

import plot_styles as S

# ── bootstrap colors that need viridis ───────────────────────────────────────
S.setup_research_topic_colors()
S.apply_style_small()

# ── replicability helpers (mirrors replicability_assessment.py) ──────────────
ABSENT = frozenset(
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
NECESSARY_COLS = {
    "SR_in_Hz": "Sample rate",
    "filters_amp": "Hardware filter settings",
    "online_filters": "Online filters applied",
    "num_channels": "Number of channels",
    "electrode_type": "Electrode type",
    "electrode_locations": "Electrode locations",
    "reference": "Reference scheme",
    "artifact_rejection": "Artifact rejection",
}
OFFLINE = {
    "flag": "offline_filters",
    "hp": "Offline_High-Pass_(Hz)",
    "lp": "Offline_Low-Pass_(Hz)",
}
N_MAX = 9

CONSUMER_CO = {
    "emotiv",
    "neurosky",
    "muse",
    "interaxon",
    "kingfar",
    "ergolab",
    "openbci",
    "neurosity",
    "brainlink",
    "mindmedia",
    "mindo",
}
RESEARCH_CO = {
    "brain products",
    "brainproducts",
    "compumedics",
    "neuroscan",
    "biosemi",
    "ant neuro",
    "g.tec",
    "gtec",
    "egi",
    "electrical geodesics",
    "nihon kohden",
    "natus",
    "biopac",
    "mitsar",
    "micromed",
    "xltek",
    "noldus",
    "acticap",
}


def _present(val):
    if pd.isna(val):
        return False
    return str(val).strip().lower() not in ABSENT


def _offline_ok(row):
    if _present(row.get(OFFLINE["flag"], "")):
        return True
    return _present(row.get(OFFLINE["hp"], "")) and _present(row.get(OFFLINE["lp"], ""))


def _score(row):
    n = sum(_present(row.get(c, "")) for c in NECESSARY_COLS)
    n += int(_offline_ok(row))
    return n


def _parse_pct(val):
    if pd.isna(val):
        return None
    try:
        v = float(str(val).strip().replace("%", ""))
        return v if v <= 100 else None
    except ValueError:
        return None


def _grade(company):
    c = str(company).lower().strip()
    if any(k in c for k in CONSUMER_CO):
        return "consumer"
    if any(k in c for k in RESEARCH_CO):
        return "research"
    return "other"


def _multicoded_primary(val):
    if pd.isna(val):
        return ""
    parts = [t.strip() for t in re.split(r"[,;/]", str(val)) if t.strip()]
    return parts[0] if parts else ""


def savefig(fig, path: Path, name: str):
    fp = path / f"{name}.svg"
    fig.savefig(fp, format="svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved → {fp.name}")


# =============================================================================
# 1  PUBLICATION TREND
# =============================================================================
def fig_publication_trend(df, out):
    years = df["Year"].dropna().astype(int)
    counts = years.value_counts().sort_index()

    fig, ax = plt.subplots(figsize=S.FIGSIZE_WIDE, facecolor="white")
    bars = ax.bar(
        counts.index, counts.values, color=S.PUBLICATION_BAR_COLOR, width=0.75, zorder=3
    )

    # shade post-2020
    for bar in bars:
        if bar.get_x() >= 2019.625:
            bar.set_color("#16324F")

    S.style_axes(ax)
    ax.set_xlabel("Publication year")
    ax.set_ylabel("Number of studies")
    ax.set_title("Publication trend (N = 463)", pad=10)
    ax.set_xlim(counts.index.min() - 0.8, counts.index.max() + 0.8)

    # annotation
    n_2020 = (years >= 2020).sum()
    ax.annotate(
        f"{n_2020} studies\nfrom 2020+\n({100 * n_2020 / len(years):.0f}%)",
        xy=(2022, counts.get(2023, 0)),
        xytext=(2016, counts.max() * 0.85),
        fontsize=7.5,
        color="#16324F",
        arrowprops=dict(arrowstyle="->", color="#888", lw=0.8),
    )

    legend_els = [
        mpatches.Patch(color=S.PUBLICATION_BAR_COLOR, label="Pre-2020"),
        mpatches.Patch(color="#16324F", label="2020+"),
    ]
    ax.legend(handles=legend_els, frameon=False, fontsize=8)
    fig.tight_layout()
    savefig(fig, out, "fig01_publication_trend")


# =============================================================================
# 2  CORPUS OVERVIEW  2 × 2
# =============================================================================
def fig_corpus_overview(df, out):
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), facecolor="white")
    fig.subplots_adjust(hspace=0.42, wspace=0.35)

    # ── 2.1  publication trend (compact) ─────────────────────────────────────
    ax = axes[0, 0]
    years = df["Year"].dropna().astype(int)
    counts = years.value_counts().sort_index()
    cols_bar = [
        "#16324F" if y >= 2020 else S.PUBLICATION_BAR_COLOR for y in counts.index
    ]
    ax.bar(counts.index, counts.values, color=cols_bar, width=0.8, zorder=3)
    S.style_axes(ax)
    ax.set_title("Publication trend")
    ax.set_xlabel("Year")
    ax.set_ylabel("N studies")
    ax.tick_params(axis="x", rotation=45, labelsize=6.5)

    # ── 2.2  age group distribution ───────────────────────────────────────────
    ax = axes[0, 1]
    age = pd.to_numeric(df["mean_age_participants"], errors="coerce").dropna()
    groups = ["<18", "18–29", "30–49", "50+"]
    counts_age = [
        (age < 18).sum(),
        ((age >= 18) & (age < 30)).sum(),
        ((age >= 30) & (age < 50)).sum(),
        (age >= 50).sum(),
    ]
    colors_age = [
        "#C1535C",
        S.AGE_COLORS["histogram"],
        S.AGE_COLORS["coverage"],
        "#16324F",
    ]
    wedges, texts, autotexts = ax.pie(
        counts_age,
        labels=groups,
        colors=colors_age,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.72,
        wedgeprops=dict(linewidth=0.6, edgecolor="white"),
    )
    for t in autotexts:
        t.set_fontsize(7)
    ax.set_title(f"Age groups (n = {len(age)} reporting)")

    # ── 2.3  sex distribution histogram ──────────────────────────────────────
    ax = axes[1, 0]
    sex = df["sex_perc_male"].apply(_parse_pct).dropna()
    ax.hist(
        sex,
        bins=20,
        color=S.SEX_HISTOGRAM_COLOR,
        edgecolor="white",
        linewidth=0.4,
        zorder=3,
    )
    ax.axvspan(0, 40, alpha=0.12, color="#C1535C", zorder=2)
    ax.axvspan(60, 100, alpha=0.12, color="#5E8CA8", zorder=2)
    ax.axvline(50, color="#444", linewidth=0.8, linestyle="--", zorder=4)
    S.style_axes(ax)
    ax.set_xlabel("% male participants")
    ax.set_ylabel("N studies")
    ax.set_title(f"Sex composition (n = {len(sex)} reporting)")
    ax.text(
        18,
        ax.get_ylim()[1] * 0.85,
        "Majority\nfemale",
        fontsize=6.5,
        color="#C1535C",
        ha="center",
    )
    ax.text(
        78,
        ax.get_ylim()[1] * 0.85,
        "Majority\nmale",
        fontsize=6.5,
        color="#5E8CA8",
        ha="center",
    )

    # ── 2.4  recording protocol ───────────────────────────────────────────────
    ax = axes[1, 1]
    proto_labels = [
        "Lab\n(stationary)",
        "Lab\n(HMD/VR)",
        "Real-world\n(mobile)",
        "Combined",
    ]
    proto_counts = [311, 76, 60, 8]
    proto_colors = ["#5E8CA8", "#8AC6E8", "#2A9D8F", "#A8E6CF"]
    wedges, texts, autotexts = ax.pie(
        proto_counts,
        labels=proto_labels,
        colors=proto_colors,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.72,
        wedgeprops=dict(linewidth=0.6, edgecolor="white"),
    )
    for t in autotexts:
        t.set_fontsize(7)
    ax.set_title("Recording protocol")

    fig.suptitle(
        "Corpus overview  (N = 463 studies)", fontsize=12, fontweight="bold", y=1.01
    )
    savefig(fig, out, "fig02_corpus_overview")


# =============================================================================
# 3  REPLICABILITY
# =============================================================================
def fig_replicability(df, out):
    df = df.copy()
    df["n_necessary"] = df.apply(_score, axis=1)
    df["replicable"] = df["n_necessary"] == N_MAX
    total = len(df)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), facecolor="white")
    fig.subplots_adjust(wspace=0.45)

    # ── 3a  donut ─────────────────────────────────────────────────────────────
    ax = axes[0]
    n_rep = df["replicable"].sum()
    n_nr = total - n_rep
    wedges, _, autotexts = ax.pie(
        [n_nr, n_rep],
        colors=[S.NON_REPLICABLE_COLOR, S.REPLICABLE_COLOR],
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=dict(width=0.55, linewidth=0.8, edgecolor="white"),
        pctdistance=0.78,
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.text(
        0, 0, f"{n_nr}\nnon-rep.", ha="center", va="center", fontsize=8.5, color="#333"
    )
    ax.set_title("Binary classification\n(all 9 criteria required)", pad=8)
    legend_els = [
        mpatches.Patch(color=S.NON_REPLICABLE_COLOR, label=f"Non-replicable ({n_nr})"),
        mpatches.Patch(color=S.REPLICABLE_COLOR, label=f"Replicable ({n_rep})"),
    ]
    ax.legend(
        handles=legend_els,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        fontsize=8,
    )

    # ── 3b  per-criterion bars (horizontal) ──────────────────────────────────
    ax = axes[1]
    labels, rates = [], []
    for col, label in NECESSARY_COLS.items():
        rates.append(df[col].apply(_present).mean() * 100)
        labels.append(label)
    rates.append(df.apply(_offline_ok, axis=1).mean() * 100)
    labels.append("Offline filter\n(either/or)")

    order = np.argsort(rates)
    labels_s = [labels[i] for i in order]
    rates_s = [rates[i] for i in order]
    bar_colors = [
        S.REPLICABLE_COLOR
        if r == max(rates_s)
        else S.NON_REPLICABLE_COLOR
        if r == min(rates_s)
        else "#5E8CA8"
        for r in rates_s
    ]

    bars = ax.barh(labels_s, rates_s, color=bar_colors, height=0.65, zorder=3)
    for bar, val in zip(bars, rates_s):
        ax.text(
            val + 0.8,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.0f}%",
            va="center",
            fontsize=7.5,
            color="#333",
        )

    ax.axvline(50, color="#888", linewidth=0.7, linestyle="--", zorder=4)
    S.style_axes(ax, grid=False)
    ax.xaxis.grid(True, color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_xlabel("% of studies reporting criterion")
    ax.set_xlim(0, 108)
    ax.set_title("Per-criterion reporting rate\n(sorted low → high)", pad=8)
    ax.tick_params(axis="y", labelsize=7.5)

    # ── 3c  score distribution ────────────────────────────────────────────────
    ax = axes[2]
    dist = df["n_necessary"].value_counts().sort_index()
    bar_cols = [
        S.NON_REPLICABLE_COLOR if n < N_MAX else S.REPLICABLE_COLOR for n in dist.index
    ]
    ax.bar(
        dist.index,
        dist.values,
        color=bar_cols,
        width=0.75,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    ax.axvline(
        N_MAX - 0.5,
        color="#333",
        linewidth=1.0,
        linestyle="--",
        zorder=4,
        label=f"Threshold = {N_MAX}",
    )
    S.style_axes(ax)
    ax.set_xlabel("Number of criteria met (0 – 9)")
    ax.set_ylabel("N studies")
    ax.set_title("Score distribution", pad=8)
    ax.set_xticks(range(N_MAX + 1))
    ax.legend(frameon=False, fontsize=7.5)

    ax.text(
        7.5,
        dist.max() * 0.88,
        f"n = {n_rep}\nreplicable",
        fontsize=7.5,
        color=S.REPLICABLE_COLOR,
        ha="center",
    )

    fig.suptitle(
        "Replicability assessment  (N = 463 studies, 9 criteria)",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )
    savefig(fig, out, "fig03_replicability")


# =============================================================================
# 4  ENVIRONMENTAL DOMAIN & PARADIGM
# =============================================================================
def fig_domain(df, out):
    dom_col = "architecture = 1 urbanism = 2 \nnature = 3"
    df = df.copy()
    df["_dom"] = df[dom_col].apply(_multicoded_primary)
    df["n_necessary"] = df.apply(_score, axis=1)
    df["replicable"] = df["n_necessary"] == N_MAX

    mob_norm = {
        "stat": "stat",
        "stat - hmd": "hmd",
        "mobile": "mobile",
        "mobile & stat": "mobile",
    }
    df["_mob"] = (
        df["EEG_system_mobile_stationary"]
        .str.lower()
        .str.strip()
        .map(mob_norm)
        .fillna("other")
    )

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), facecolor="white")
    fig.subplots_adjust(wspace=0.42)

    dom_map = {"1": "Architecture", "2": "Urbanism", "3": "Nature"}
    dom_colors = ["#5E8CA8", "#16324F", "#4C9A74"]

    # ── 4a  domain proportions donut ─────────────────────────────────────────
    ax = axes[0]
    dom_counts = [df["_dom"].eq(k).sum() for k in ("1", "2", "3")]
    ax.pie(
        dom_counts,
        labels=[f"{dom_map[k]}\n(n={c})" for k, c in zip(("1", "2", "3"), dom_counts)],
        colors=dom_colors,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.72,
        wedgeprops=dict(width=0.55, linewidth=0.7, edgecolor="white"),
    )
    ax.set_title("Environmental domain\n(primary coding)")

    # ── 4b  paradigm by domain stacked bars ──────────────────────────────────
    ax = axes[1]
    mob_labels = ["Stationary lab", "HMD/VR", "Mobile"]
    mob_keys = ["stat", "hmd", "mobile"]
    mob_colors = ["#5E8CA8", "#8AC6E8", "#2A9D8F"]
    x = np.arange(3)
    dom_keys = ("1", "2", "3")
    bottoms = np.zeros(3)
    for mob_key, mob_label, mob_color in zip(mob_keys, mob_labels, mob_colors):
        vals = [df[df["_dom"] == dk]["_mob"].eq(mob_key).sum() for dk in dom_keys]
        ax.bar(
            x,
            vals,
            bottom=bottoms,
            label=mob_label,
            color=mob_color,
            width=0.6,
            edgecolor="white",
            linewidth=0.5,
            zorder=3,
        )
        bottoms += np.array(vals)
    S.style_axes(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(["Architecture", "Urbanism", "Nature"])
    ax.set_ylabel("N studies")
    ax.set_title("Paradigm by domain")
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")

    # ── 4c  non-replicability by domain ──────────────────────────────────────
    ax = axes[2]
    nr_rates = []
    for dk in dom_keys:
        sub = df[df["_dom"] == dk]
        nr_rates.append(100 * (~sub["replicable"]).mean() if len(sub) else 0)
    bars = ax.bar(
        x,
        nr_rates,
        color=dom_colors,
        width=0.55,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    for bar, val in zip(bars, nr_rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.5,
            f"{val:.0f}%",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    S.style_axes(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(["Architecture", "Urbanism", "Nature"])
    ax.set_ylabel("Non-replicable (%)")
    ax.set_title("Non-replicability by domain")
    ax.set_ylim(0, 115)
    ax.axhline(100, color="#aaa", linewidth=0.6, linestyle=":")

    fig.suptitle(
        "Environmental domain analysis  (N = 463)",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )
    savefig(fig, out, "fig04_domain_paradigm")


# =============================================================================
# 5  RESEARCH FOCUS & MOTIVATION
# =============================================================================
def fig_research_focus(df, out):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), facecolor="white")
    fig.subplots_adjust(wspace=0.4)

    # ── 5a  research topic horizontal bars ───────────────────────────────────
    ax = axes[0]
    topic_counts = df["Research Topic"].value_counts()
    short_labels = {
        "Nature & restorative environments": "Nature & restorative",
        "Architectural & built interior spaces": "Architectural & built",
        "Urban outdoor environments": "Urban outdoor",
        "Multisensory & environmental stimuli": "Multisensory & sensory",
        "Methods & technology": "Methods & technology",
    }
    labels = [short_labels.get(t, t) for t in topic_counts.index[:5]]
    values = topic_counts.values[:5]
    colors = [S.get_research_topic_color(t) for t in topic_counts.index[:5]]

    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.6, zorder=3)
    for bar, val in zip(bars, values[::-1]):
        ax.text(
            val + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{val}  ({100 * val / len(df):.0f}%)",
            va="center",
            fontsize=7.5,
            color="#333",
        )
    S.style_axes(ax, grid=False)
    ax.xaxis.grid(True, color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_xlabel("Number of studies")
    ax.set_xlim(0, max(values) * 1.3)
    ax.set_title("Primary research focus")

    # ── 5b  motivation donut ──────────────────────────────────────────────────
    ax = axes[1]
    mot = df["Motivation"].str.strip().value_counts()
    mot_short = {
        "Design optimisation": "Design\noptimisation",
        "Planning & policy evidence": "Planning &\npolicy",
        "Fundamental understanding": "Fundamental\nunderstanding",
        "Methodological development": "Methods\ndevelopment",
        "Health & therapeutic applications": "Health &\ntherapeutic",
        "Theory testing": "Theory\ntesting",
    }
    mot_labels = [mot_short.get(k, k) for k in mot.index]
    mot_colors = S.MOTIVATION_PALETTE[: len(mot)]
    wedges, texts, autotexts = ax.pie(
        mot.values,
        labels=mot_labels,
        colors=mot_colors,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.78,
        wedgeprops=dict(width=0.55, linewidth=0.6, edgecolor="white"),
    )
    for t in texts:
        t.set_fontsize(7.5)
    for t in autotexts:
        t.set_fontsize(7)
    ax.set_title("Study motivation")

    fig.suptitle(
        "Research focus & motivation  (N = 463)", fontsize=11, fontweight="bold", y=1.02
    )
    savefig(fig, out, "fig05_research_focus")


# =============================================================================
# 6  EEG FEATURES & FREQUENCY BANDS
# =============================================================================
def fig_eeg_features(df, out):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), facecolor="white")
    fig.subplots_adjust(wspace=0.4)
    total = len(df)

    # ── 6a  analytic domain ───────────────────────────────────────────────────
    ax = axes[0]
    fc = df["EEG_features_cat"].astype(str)
    domain_data = {
        "Frequency domain": fc.str.contains(r"\b2\b", regex=True, na=False).sum(),
        "Time domain (ERP)": fc.str.contains(r"\b1\b", regex=True, na=False).sum(),
        "Proprietary output": fc.str.contains(
            r"(?:9|propriat)", regex=True, na=False
        ).sum(),
        "Connectivity": fc.str.contains(r"\b3\b", regex=True, na=False).sum(),
        "Source localisation": fc.str.contains(r"\b4\b", regex=True, na=False).sum(),
    }
    dom_colors = ["#16324F", "#5E8CA8", "#C1535C", "#2A9D8F", "#A8E6CF"]
    labels_d = list(domain_data.keys())
    vals_d = list(domain_data.values())
    order = np.argsort(vals_d)[::-1]

    bars = ax.bar(
        range(len(vals_d)),
        [vals_d[i] for i in order],
        color=[dom_colors[i] for i in order],
        width=0.6,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    ax.set_xticks(range(len(vals_d)))
    ax.set_xticklabels(
        [labels_d[i] for i in order], rotation=20, ha="right", fontsize=7.5
    )
    for bar, val in zip(bars, [vals_d[i] for i in order]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 1,
            f"{val}\n({100 * val / total:.0f}%)",
            ha="center",
            va="bottom",
            fontsize=7,
            color="#333",
        )
    S.style_axes(ax)
    ax.set_ylabel("N studies")
    ax.set_title("Analytic domain")

    # ── 6b  frequency bands ───────────────────────────────────────────────────
    ax = axes[1]
    ps = df["EEG_parameter_space"].astype(str)
    freq_mask = fc.str.contains(r"\b2\b", regex=True, na=False)
    ps_freq = ps[freq_mask]
    n_freq = freq_mask.sum()

    bands = {
        "Alpha": ps_freq.str.contains(r"[⍺α]|alpha", case=False, na=False).sum(),
        "Beta": ps_freq.str.contains(r"[𝛽β]|beta", case=False, na=False).sum(),
        "Theta": ps_freq.str.contains(r"[𝜃θ]|theta", case=False, na=False).sum(),
        "Gamma (λ)": ps_freq.str.contains(r"[λγ]|gamma", case=False, na=False).sum(),
        "Delta": ps_freq.str.contains(r"[δ]|delta", case=False, na=False).sum(),
    }
    band_colors = ["#16324F", "#1D5F7A", "#2A9D8F", "#4CC9A6", "#A8E6CF"]
    b_vals = list(bands.values())
    b_labels = list(bands.keys())

    bars2 = ax.barh(
        b_labels[::-1],
        [100 * v / n_freq for v in b_vals[::-1]],
        color=band_colors[::-1],
        height=0.6,
        zorder=3,
    )
    for bar, val in zip(bars2, [100 * v / n_freq for v in b_vals[::-1]]):
        ax.text(
            val + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.0f}%",
            va="center",
            fontsize=8,
        )
    S.style_axes(ax, grid=False)
    ax.xaxis.grid(True, color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_xlabel(f"% of frequency-domain studies (n = {n_freq})")
    ax.set_xlim(0, 115)
    ax.set_title("Frequency band prevalence\n(within freq-domain sub-corpus)")

    fig.suptitle(
        "EEG features & analytic domain  (N = 463)",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )
    savefig(fig, out, "fig06_eeg_features")


# =============================================================================
# 7  MULTIMODAL ACQUISITION & INTEGRATION
# =============================================================================
def fig_multimodal(df, out):
    total = len(df)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), facecolor="white")
    fig.subplots_adjust(wspace=0.45)

    # ── 7a  acquisition donut ─────────────────────────────────────────────────
    ax = axes[0]
    n_eeg_only = df["other_measures"].isna().sum()
    n_multi = total - n_eeg_only
    fusion_yes = df["Fusion EEG-Other Modalities"].eq(1.0).sum()
    fusion_no = n_multi - fusion_yes

    wedge_vals = [n_eeg_only, fusion_no, fusion_yes]
    wedge_labels = [
        f"EEG only\n(n={n_eeg_only})",
        f"Multi – not\nintegrated\n(n={fusion_no})",
        f"Multi –\nintegrated\n(n={fusion_yes})",
    ]
    wedge_colors = ["#C8DDE8", "#5E8CA8", "#2A9D8F"]
    ax.pie(
        wedge_vals,
        labels=wedge_labels,
        colors=wedge_colors,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.72,
        wedgeprops=dict(width=0.55, linewidth=0.7, edgecolor="white"),
    )
    ax.set_title("Acquisition vs. integration")

    # ── 7b  modality prevalence ───────────────────────────────────────────────
    ax = axes[1]
    om = df["other_measures"].dropna().astype(str).str.lower()
    modalities = {
        "ECG / HRV": om.str.contains(r"ecg|hrv|heart rate", na=False).sum(),
        "EDA": om.str.contains(r"\beda\b|galvanic|gsr", na=False).sum(),
        "Eye-tracking": om.str.contains(r"eye.?track", na=False).sum(),
        "Blood pressure": om.str.contains(r"blood.?press", na=False).sum(),
        "Skin temperature": om.str.contains(r"skin.?temp|temperature", na=False).sum(),
        "PPG": om.str.contains(r"\bppg\b|photopleth", na=False).sum(),
        "Respiration": om.str.contains(r"resp|breath", na=False).sum(),
        "EMG": om.str.contains(r"\bemg\b", na=False).sum(),
        "EOG": om.str.contains(r"\beog\b", na=False).sum(),
        "Motion / GPS": om.str.contains(r"gps|motion|accel", na=False).sum(),
    }
    order = sorted(modalities, key=modalities.get, reverse=True)
    vals = [modalities[k] for k in order]
    pcts = [100 * v / n_multi for v in vals]
    bar_cols = [
        S.MOTIVATION_PALETTE[i % len(S.MOTIVATION_PALETTE)] for i in range(len(order))
    ]

    bars = ax.barh(order[::-1], pcts[::-1], color=bar_cols[::-1], height=0.65, zorder=3)
    for bar, val in zip(bars, pcts[::-1]):
        ax.text(
            val + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.0f}%",
            va="center",
            fontsize=7.5,
        )
    S.style_axes(ax, grid=False)
    ax.xaxis.grid(True, color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_xlabel(f"% of multimodal studies (n = {n_multi})")
    ax.set_xlim(0, 80)
    ax.set_title("Modality prevalence\n(multimodal subset)")
    ax.tick_params(axis="y", labelsize=7.5)

    fig.suptitle(
        "Multimodal acquisition & analytical integration  (N = 463)",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )
    savefig(fig, out, "fig07_multimodal")


# =============================================================================
# 8  HARDWARE: CHANNELS & DEVICE FAMILIES
# =============================================================================
def fig_hardware(df, out):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), facecolor="white")
    fig.subplots_adjust(wspace=0.45)
    total = len(df)

    # ── 8a  channel count distribution ───────────────────────────────────────
    ax = axes[0]
    ch = pd.to_numeric(df["num_channels"], errors="coerce").dropna()
    bins = [0, 4, 8, 12, 16, 20, 24, 28, 32, 48, 64, 96, 128, 256, 512]
    counts_ch, edges = np.histogram(ch, bins=bins)
    tick_labels = [f"{edges[i]:.0f}–{edges[i + 1]:.0f}" for i in range(len(counts_ch))]
    bar_cols_ch = [
        S.CONSUMER_COLOR
        if edges[i + 1] <= 20
        else "#8AC6E8"
        if edges[i + 1] <= 32
        else S.RESEARCH_COLOR
        for i in range(len(counts_ch))
    ]

    ax.bar(
        range(len(counts_ch)),
        counts_ch,
        color=bar_cols_ch,
        width=0.75,
        edgecolor="white",
        linewidth=0.4,
        zorder=3,
    )
    ax.set_xticks(range(len(counts_ch)))
    ax.set_xticklabels(tick_labels, rotation=40, ha="right", fontsize=6.5)
    ax.axvline(3.5, color="#888", linewidth=0.8, linestyle="--")  # ~20 ch
    S.style_axes(ax)
    ax.set_ylabel("N studies")
    ax.set_title(
        f"Channel count distribution\n(n = {len(ch)} reporting; "
        f"median = {ch.median():.0f}, mean = {ch.mean():.1f})"
    )

    legend_els = [
        mpatches.Patch(color=S.CONSUMER_COLOR, label="≤20 ch (consumer-grade)"),
        mpatches.Patch(color="#8AC6E8", label="21–32 ch"),
        mpatches.Patch(color=S.RESEARCH_COLOR, label=">32 ch (research-grade)"),
    ]
    ax.legend(handles=legend_els, frameon=False, fontsize=7.5)

    # ── 8b  device families ───────────────────────────────────────────────────
    ax = axes[1]
    comp = df["EEG_company"].dropna().astype(str).str.strip()
    top12 = comp.value_counts().head(12)
    grade_col = {
        "consumer": S.CONSUMER_COLOR,
        "research": S.RESEARCH_COLOR,
        "other": S.OTHER_COLOR,
    }
    colors_dev = [grade_col[_grade(c)] for c in top12.index]
    pcts_dev = [100 * v / total for v in top12.values]

    bars = ax.barh(
        top12.index[::-1], pcts_dev[::-1], color=colors_dev[::-1], height=0.65, zorder=3
    )
    for bar, val in zip(bars, pcts_dev[::-1]):
        ax.text(
            val + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%",
            va="center",
            fontsize=7.5,
        )
    S.style_axes(ax, grid=False)
    ax.xaxis.grid(True, color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_xlabel("% of full corpus")
    ax.set_xlim(0, max(pcts_dev) * 1.35)
    ax.set_title("EEG device families (top 12)\ncoloured by hardware grade")
    ax.tick_params(axis="y", labelsize=8)

    legend_els = [
        mpatches.Patch(color=S.CONSUMER_COLOR, label="Consumer-grade"),
        mpatches.Patch(color=S.RESEARCH_COLOR, label="Research-grade"),
        mpatches.Patch(color=S.OTHER_COLOR, label="Other / unknown"),
    ]
    ax.legend(handles=legend_els, frameon=False, fontsize=7.5, loc="lower right")

    fig.suptitle("EEG hardware  (N = 463)", fontsize=11, fontweight="bold", y=1.02)
    savefig(fig, out, "fig08_hardware")


# =============================================================================
# 9  GEOGRAPHY
# =============================================================================
def fig_geography(df, out):
    df = df.copy()
    df["n_necessary"] = df.apply(_score, axis=1)
    df["replicable"] = df["n_necessary"] == N_MAX
    total = len(df)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0), facecolor="white")
    fig.subplots_adjust(wspace=0.45)

    country = df["Country first Author Affiliation"].str.lower().str.strip()
    top15 = country.value_counts().head(15)

    # ── 9a  country bar chart ─────────────────────────────────────────────────
    ax = axes[0]
    WESTERN = {
        "usa",
        "uk",
        "germany",
        "australia",
        "canada",
        "netherlands",
        "sweden",
        "norway",
        "denmark",
        "finland",
        "france",
        "italy",
        "spain",
        "portugal",
        "switzerland",
        "austria",
        "belgium",
        "new zealand",
        "ireland",
        "greece",
        "poland",
    }
    bar_cols_geo = [
        S.PUBLICATION_BAR_COLOR if c in WESTERN else "#16324F" for c in top15.index
    ]
    pcts_geo = [100 * v / total for v in top15.values]

    bars = ax.barh(
        top15.index[::-1],
        pcts_geo[::-1],
        color=bar_cols_geo[::-1],
        height=0.65,
        zorder=3,
    )
    for bar, val in zip(bars, pcts_geo[::-1]):
        ax.text(
            val + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%",
            va="center",
            fontsize=7.5,
        )
    S.style_axes(ax, grid=False)
    ax.xaxis.grid(True, color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_xlabel("% of corpus")
    ax.set_xlim(0, max(pcts_geo) * 1.3)
    ax.set_title("First-author country (top 15)")
    ax.tick_params(axis="y", labelsize=8)

    legend_els = [
        mpatches.Patch(color="#16324F", label="Non-Western"),
        mpatches.Patch(color=S.PUBLICATION_BAR_COLOR, label="Western"),
    ]
    ax.legend(handles=legend_els, frameon=False, fontsize=7.5)

    # ── 9b  non-replicability by country ─────────────────────────────────────
    ax = axes[1]
    top8 = country.value_counts().head(8)
    nr_rates_geo, ns = [], []
    for c in top8.index:
        sub = df[country == c]
        nr_rates_geo.append(100 * (~sub["replicable"]).mean())
        ns.append(len(sub))

    bar_cols_nr = [
        S.NON_REPLICABLE_COLOR if r >= 95 else "#5E8CA8" for r in nr_rates_geo
    ]
    bars2 = ax.bar(
        range(len(top8)),
        nr_rates_geo[::-1],
        color=bar_cols_nr[::-1],
        width=0.6,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    ax.set_xticks(range(len(top8)))
    ax.set_xticklabels(
        [c.title() for c in top8.index[::-1]], rotation=30, ha="right", fontsize=8
    )
    for bar, val in zip(bars2, nr_rates_geo[::-1]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.5,
            f"{val:.0f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    S.style_axes(ax)
    ax.set_ylabel("Non-replicable (%)")
    ax.set_title("Non-replicability rate\nby top-8 countries")
    ax.set_ylim(0, 115)
    ax.axhline(100, color="#aaa", linewidth=0.6, linestyle=":")

    fig.suptitle(
        "Geographic distribution  (N = 463)", fontsize=11, fontweight="bold", y=1.02
    )
    savefig(fig, out, "fig09_geography")


# =============================================================================
# 10  OPEN SCIENCE
# =============================================================================
def fig_open_science(df, out):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), facecolor="white")
    fig.subplots_adjust(wspace=0.4)

    # ── 10a  data availability donut ─────────────────────────────────────────
    ax = axes[0]
    da = df["Data Availability"]
    n_open = da.eq(2.0).sum()
    n_req = da.eq(1.0).sum()
    n_none = da.eq(0.0).sum()
    n_na = da.isna().sum()
    vals_da = [n_open, n_req, n_none, n_na]
    labs_da = [
        f"Openly available\n({n_open})",
        f"On request\n({n_req})",
        f"No statement\n({n_none})",
        f"Not coded\n({n_na})",
    ]
    pal = S.AVAILABILITY_PALETTE
    cols_da = [
        pal["Openly available"],
        pal["Available upon request"],
        pal["Not available"],
        pal["NA"],
    ]

    wedges, texts, autotexts = ax.pie(
        vals_da,
        labels=labs_da,
        colors=cols_da,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.72,
        wedgeprops=dict(width=0.55, linewidth=0.7, edgecolor="white"),
    )
    for t in texts:
        t.set_fontsize(7.5)
    for t in autotexts:
        t.set_fontsize(7)
    ax.set_title("Data availability statement")

    # ── 10b  data availability over time ─────────────────────────────────────
    ax = axes[1]
    df2 = df.copy()
    df2["year_bin"] = pd.cut(
        df2["Year"],
        bins=[1980, 2009, 2014, 2019, 2022, 2026],
        labels=["≤2009", "2010–14", "2015–19", "2020–22", "2023–26"],
    )
    avail_by_year = (
        df2.groupby("year_bin", observed=True)["Data Availability"]
        .apply(
            lambda s: pd.Series(
                {
                    "open": s.eq(2.0).sum(),
                    "request": s.eq(1.0).sum(),
                    "none": s.eq(0.0).sum() + s.isna().sum(),
                    "total": len(s),
                }
            )
        )
        .unstack()
    )

    x = np.arange(len(avail_by_year))
    w = 0.26
    totals = avail_by_year["total"]
    ax.bar(
        x - w,
        100 * avail_by_year["open"] / totals,
        width=w,
        color=pal["Openly available"],
        label="Openly available",
        zorder=3,
    )
    ax.bar(
        x,
        100 * avail_by_year["request"] / totals,
        width=w,
        color=pal["Available upon request"],
        label="On request",
        zorder=3,
    )
    ax.bar(
        x + w,
        100 * avail_by_year["none"] / totals,
        width=w,
        color=pal["Not available"],
        label="No statement / not coded",
        zorder=3,
    )

    S.style_axes(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(avail_by_year.index, fontsize=8)
    ax.set_ylabel("% of studies in period")
    ax.set_title("Data availability over time")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")

    fig.suptitle(
        "Open science practices  (N = 463)", fontsize=11, fontweight="bold", y=1.02
    )
    savefig(fig, out, "fig10_open_science")


# =============================================================================
# MAIN
# =============================================================================


def main(csv_path: Path, out_path: Path):
    out_path.mkdir(parents=True, exist_ok=True)

    df_raw = pd.read_csv(csv_path)
    df = df_raw.dropna(subset=["Title"]).copy()
    df = df[df["Title"].str.strip().ne("")]
    print(f"Loaded {len(df)} papers → generating SVGs in {out_path}/\n")

    fig_publication_trend(df, out_path)
    fig_corpus_overview(df, out_path)
    fig_replicability(df, out_path)
    fig_domain(df, out_path)
    fig_research_focus(df, out_path)
    fig_eeg_features(df, out_path)
    fig_multimodal(df, out_path)
    fig_hardware(df, out_path)
    fig_geography(df, out_path)
    fig_open_science(df, out_path)

    print(f"\nDone — {len(list(out_path.glob('*.svg')))} SVGs written to {out_path}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate review figures as SVG")
    parser.add_argument(
        "--csv", type=Path, default=Path(__file__).parent / "data" / "papers.csv"
    )
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "figures")
    args = parser.parse_args()
    if not args.csv.exists():
        raise FileNotFoundError(f"CSV not found: {args.csv}")
    main(args.csv, args.out)
