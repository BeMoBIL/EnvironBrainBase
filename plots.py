"""Plot generation utilities for the Neuro-Urbanism corpus analysis."""

import csv
import re
from io import StringIO
from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from scipy import stats

# Replicability labels used by reporting-rate plots.
NECESSARY_COLS: dict[str, str] = {
    "SR_in_Hz":            "Sample rate",
    "online_filters":      "Online filters applied",
    "num_channels":        "Number of channels",
    "electrode_type":      "Electrode type",
    "electrode_locations": "Electrode locations",
    "reference":           "Reference scheme",
    "artifact_rejection":  "Artifact rejection",
}

# Journal venue classification (keyword-based).
VENUE_KEYWORDS = {
    "Architecture / Built-environment / Design": [
        "building", "architect", "construction", "facility", "facilities",
        "habitat", "indoor", "interior", "structural", "built environment",
        "design stud", "design research",
    ],
    "Nature / Environment / Landscape / Health": [
        "environment", "nature", "landscape", "forest", "urban forest",
        "green", "ecological", "ecology", "land", "public health",
        "health promot", "epidemi", "preventive", "environ res",
        "sustainability", "sustainable", "cities", "urban plan",
        "frontiers in public", "int j environ",
    ],
    "Engineering / Acoustics / Technology": [
        "engineer", "acoustic", "applied sci", "sensor", "ieee",
        "signal process", "measurement", "instrum", "comput",
        "simulation", "technolog",
    ],
    "Neuroscience / Psychology": [
        "neurosci", "psychol", "brain", "cognit", "neural", "behav",
        "neuroimag", "psychophysiol", "neuroergon", "affect",
        "front hum neurosci", "front psychol", "j environ psychol",
        "sci rep", "scientific reports", "plos one", "elife",
        "j cog neurosci", "psychophysiology", "neuroimage",
        "j neurosci", "pnas", "euro j neurosci", "cerebral cortex",
        "eneuro", "brain sci",
    ],
}


def classify_venue(journal: str) -> str:
    j = str(journal).lower().strip()
    for label, kws in [
        ("Neuroscience / Psychology", VENUE_KEYWORDS["Neuroscience / Psychology"]),
        ("Architecture / Built-environment / Design",
             VENUE_KEYWORDS["Architecture / Built-environment / Design"]),
        ("Nature / Environment / Landscape / Health",
             VENUE_KEYWORDS["Nature / Environment / Landscape / Health"]),
        ("Engineering / Acoustics / Technology",
             VENUE_KEYWORDS["Engineering / Acoustics / Technology"]),
    ]:
        if any(kw in j for kw in kws):
            return label
    return "Other / Unclassified"

mpl.rcParams["svg.fonttype"] = "path"
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42

EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

FONT_STACK = [
    "Neue Haas Grotesk Text Pro", "Neue Haas Grotesk Display Pro",
    "Neue Haas Grotesk", "Avenir Next", "Helvetica Neue", "Futura", "DejaVu Sans",
]


def export_figure(fig: plt.Figure, stem: str) -> None:
    """Export a figure in SVG, PDF, and EPS formats."""
    fig.savefig(EXPORT_DIR / f"{stem}.svg", format="svg", bbox_inches="tight", facecolor="white")
    fig.savefig(EXPORT_DIR / f"{stem}.pdf", format="pdf", bbox_inches="tight", facecolor="white")
    # fig.savefig(EXPORT_DIR / f"{stem}.eps", format="eps", bbox_inches="tight", facecolor="white")
    fig.savefig(EXPORT_DIR / f"{stem}.png", format="png", bbox_inches="tight", facecolor="white")

    print(f"  Saved plot: {stem}")


def split_values(text: object) -> list[str]:
    if pd.isna(text):
        return []
    row = next(csv.reader(StringIO(str(text)), skipinitialspace=True))
    return [item.strip().strip('"').strip("'").strip() for item in row if item.strip()]


def set_plot_style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "mathtext.fontset": "stix",
        "font.sans-serif": FONT_STACK,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
    })


def plot_research_topic(df: pd.DataFrame) -> None:
    broad_values = []
    for raw in df["Research Topic"].dropna():
        broad_values.extend(split_values(raw))

    broad_counts = pd.Series(broad_values).value_counts()
    bar_total = broad_counts.sum()

    set_plot_style()

    viridis = plt.get_cmap("viridis")
    family_palette = {
        "nature": "#4C9A74",
        "architectural": viridis(0.18),
        "urban": viridis(0.42),
        "ambient": viridis(0.68),
        "methods": viridis(0.90),
        "other": "#7C817A",
    }
    category_color_map = {
        "Nature & restorative environments": family_palette["nature"],
        "Architectural & built interior spaces": family_palette["architectural"],
        "Urban outdoor environments": family_palette["urban"],
        "Multisensory & environmental stimuli": family_palette["ambient"],
        "Methods & technology": family_palette["methods"],
    }

    def color_for_category(cat: str):
        return category_color_map.get(cat, family_palette["other"])

    pie_counts = broad_counts
    pie_colors = [color_for_category(cat) for cat in pie_counts.index]

    fig1, ax1 = plt.subplots(figsize=(6.8, 4.8), dpi=300)
    wedges, texts, autotexts = ax1.pie(
        pie_counts.values,
        labels=pie_counts.index,
        colors=pie_colors,
        startangle=105,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",
        pctdistance=0.78,
        labeldistance=1.04,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
        textprops={"color": "#2A2A2A", "fontsize": 5.5},
    )
    for wedge, t in zip(wedges, autotexts):
        r, g, b, _ = wedge.get_facecolor()
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        t.set_color("white" if luminance < 0.52 else "#3A3A3A")
        t.set_fontsize(5.5)
    ax1.set_title("Research Object Distribution", loc="left", pad=8, color="#1F1F1F")
    plt.tight_layout()
    export_figure(fig1, "research_object_distribution")
    plt.close(fig1)

    bar_counts = broad_counts.sort_values()
    bar_colors = [color_for_category(cat) for cat in bar_counts.index]

    fig2, ax2 = plt.subplots(figsize=(7.0, 4.9), dpi=300)
    bars = ax2.barh(bar_counts.index, bar_counts.values, color=bar_colors, height=0.62)
    ax2.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax2.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax2.spines[spine].set_visible(False)
    ax2.set_title("Environmental Focus Distribution", pad=8, loc="left", color="#1F1F1F")
    ax2.set_xlabel("Number of Papers", color="#3A3A3A", labelpad=6)
    ax2.set_ylabel("")
    ax2.tick_params(axis="x", colors="#555555", length=0)
    ax2.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)
    for bar in bars:
        width = bar.get_width()
        pct = width / bar_total * 100
        ax2.text(
            width + max(bar_counts.values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{pct:.1f}%",
            va="center", ha="left", fontsize=8, color="#4A4A4A",
        )
    legend_handles = [
        mpatches.Patch(color=family_palette["nature"], label="Nature"),
        mpatches.Patch(color=family_palette["architectural"], label="Architectural"),
        mpatches.Patch(color=family_palette["urban"], label="Urban"),
        mpatches.Patch(color=family_palette["ambient"], label="Multisensory/Ambient"),
        mpatches.Patch(color=family_palette["methods"], label="Methods"),
    ]
    ax2.legend(handles=legend_handles, frameon=False, loc="lower right", fontsize=8, labelcolor="#4A4A4A")
    fig2.tight_layout()
    export_figure(fig2, "research_topic_distribution")
    plt.close(fig2)


def plot_motivation(df: pd.DataFrame) -> None:
    motivation_values = []
    for raw in df["Motivation"].dropna():
        motivation_values.extend(split_values(raw))

    motivation_counts = pd.Series(motivation_values).value_counts()

    set_plot_style()

    palette = [
        "#16324F", "#1D5F7A", "#2A9D8F", "#4CC9A6", "#6ED8B5",
        "#A8E6CF", "#D4F1EF", "#8AC6E8", "#5E8CA8", "#C8DDE8",
    ]
    pie_counts = motivation_counts
    pie_colors = [palette[i % len(palette)] for i in range(len(pie_counts))]

    fig, ax = plt.subplots(figsize=(6.8, 4.8), dpi=300)
    wedges, texts, autotexts = ax.pie(
        pie_counts.values,
        labels=pie_counts.index,
        colors=pie_colors,
        startangle=105,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",
        pctdistance=0.78,
        labeldistance=1.04,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
        textprops={"color": "#2A2A2A", "fontsize": 8},
    )
    for wedge, t in zip(wedges, autotexts):
        r, g, b, _ = wedge.get_facecolor()
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        t.set_color("white" if luminance < 0.55 else "#1F1F1F")
        t.set_fontsize(8)
    ax.set_title("Motivation Distribution", loc="left", pad=8, color="#1F1F1F")
    plt.tight_layout()
    export_figure(fig, "motivation_distribution")
    plt.close(fig)


def plot_study_design(df: pd.DataFrame) -> None:
    total = len(df)
    design_counts = pd.Series({
        "Lab (incl. HMD/VR)": df["lab_realworld_binary"].eq(1).sum(),
        "Real-world (mobile)": df["lab_realworld_binary"].eq(2).sum(),
        "Combined lab+field": df["lab_realworld_binary"].eq(3).sum(),
    })

    if design_counts.sum() == 0:
        print("  No study design data found; skipping study_design plot.")
        return

    set_plot_style()

    palette = ["#0B3C5D", "#2A9D8F", "#A8E6CF"]
    fig, ax = plt.subplots(figsize=(6.8, 4.8), dpi=300)
    wedges, texts, autotexts = ax.pie(
        design_counts.values,
        labels=design_counts.index,
        colors=palette,
        startangle=105,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",
        pctdistance=0.78,
        labeldistance=1.04,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
        textprops={"color": "#2A2A2A", "fontsize": 8},
    )
    for wedge, t in zip(wedges, autotexts):
        r, g, b, _ = wedge.get_facecolor()
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        t.set_color("white" if luminance < 0.55 else "#1F1F1F")
        t.set_fontsize(8)

    ax.set_title("Study Design Distribution", loc="left", pad=8, color="#1F1F1F")
    ax.text(
        0.5, -0.08,
        f"N = {total}",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    plt.tight_layout()
    export_figure(fig, "study_design_distribution")
    plt.close(fig)


def plot_paradigm_by_research_object(df: pd.DataFrame) -> None:
    topic_labels = [
        "Nature & restorative environments",
        "Architectural & built interior spaces",
        "Urban outdoor environments",
        "Multisensory & environmental stimuli",
        "Methods & technology",
    ]

    rows = []
    for _, row in df.iterrows():
        raw_topics = split_values(row.get("Research Topic"))
        mapped_topics = [topic for topic in raw_topics if topic in topic_labels]
        if not mapped_topics:
            continue

        mobility = str(row.get("EEG_system_mobile_stationary", "")).strip().lower()
        for topic in mapped_topics:
            rows.append({"topic": topic, "mobility": mobility})

    if not rows:
        print("  No research-object paradigm data found; skipping paradigm_by_research_object plot.")
        return

    topic_frame = pd.DataFrame(rows)
    summary = topic_frame.groupby("topic", sort=False).agg(
        total=("mobility", "size"),
        stationary=("mobility", lambda s: s.eq("stat").sum()),
        hmd=("mobility", lambda s: s.eq("stat - hmd").sum()),
        mobile=("mobility", lambda s: s.str.contains("mobile", na=False).sum()),
    )

    summary = summary.reindex([topic for topic in topic_labels if topic in summary.index])
    summary = summary.dropna(subset=["total"])

    if summary.empty:
        print("  No research-object paradigm data found; skipping paradigm_by_research_object plot.")
        return

    count_table = pd.DataFrame({
        "Stationary lab": summary["stationary"],
        "HMD/VR": summary["hmd"],
        "Mobile": summary["mobile"],
    })
    count_table["Other/NA"] = (
        summary["total"] - (summary["stationary"] + summary["hmd"] + summary["mobile"])
    ).clip(lower=0)

    set_plot_style()

    colors = {
        "Stationary lab": "#0B3C5D",
        "HMD/VR": "#2A9D8F",
        "Mobile": "#A8E6CF",
        "Other/NA": "#D7DEE3",
    }

    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=300)
    left = np.zeros(len(count_table))
    y_labels = count_table.index.tolist()
    totals = summary["total"].to_numpy()

    for column in ["Stationary lab", "HMD/VR", "Mobile", "Other/NA"]:
        values = count_table[column].to_numpy()
        bars = ax.barh(y_labels, values, left=left, color=colors[column], height=0.62, label=column)
        for bar, value, total in zip(bars, values, totals):
            pct_value = (value / total * 100) if total > 0 else 0
            if pct_value >= 9:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{pct_value:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if column in {"Stationary lab", "HMD/VR"} else "#1F1F1F",
                )
        left += values

    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("Paradigm Choice by Research Object", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of studies", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    max_total = int(summary["total"].max())
    ax.set_xlim(0, max_total * 1.12)
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    for i, (topic, total) in enumerate(summary["total"].items()):
        ax.text(total + max_total * 0.01, i, f"n={int(total)}", va="center", ha="left", fontsize=8, color="#555555")

    ax.legend(frameon=False, loc="lower right", ncol=2)
    fig.tight_layout()
    export_figure(fig, "paradigm_by_research_object")
    plt.close(fig)


def plot_study_design_by_research_object(df: pd.DataFrame) -> None:
    topic_labels = [
        "Nature & restorative environments",
        "Architectural & built interior spaces",
        "Urban outdoor environments",
        "Multisensory & environmental stimuli",
        "Methods & technology",
    ]

    design_map = {
        1: "Lab",
        2: "Real-world",
        3: "Combined lab+field",
    }

    rows = []
    for _, row in df.iterrows():
        raw_topics = split_values(row.get("Research Topic"))
        mapped_topics = [topic for topic in raw_topics if topic in topic_labels]
        if not mapped_topics:
            continue

        design_code = pd.to_numeric(row.get("lab_realworld_binary"), errors="coerce")
        if pd.notna(design_code):
            design_label = design_map.get(int(design_code), "Other/NA")
        else:
            design_label = "Other/NA"

        for topic in mapped_topics:
            rows.append({"topic": topic, "design": design_label})

    if not rows:
        print("  No research-object study-design data found; skipping study_design_by_research_object plot.")
        return

    topic_frame = pd.DataFrame(rows)
    summary = topic_frame.groupby("topic", sort=False).agg(
        total=("design", "size"),
        lab=("design", lambda s: s.eq("Lab").sum()),
        real_world=("design", lambda s: s.eq("Real-world").sum()),
        combined=("design", lambda s: s.eq("Combined lab+field").sum()),
    )

    summary = summary.reindex([topic for topic in topic_labels if topic in summary.index])
    summary = summary.dropna(subset=["total"])

    if summary.empty:
        print("  No research-object study-design data found; skipping study_design_by_research_object plot.")
        return

    count_table = pd.DataFrame({
        "Lab": summary["lab"],
        "Real-world": summary["real_world"],
        "Combined lab+field": summary["combined"],
    })
    count_table["Other/NA"] = (
        summary["total"] - (summary["lab"] + summary["real_world"] + summary["combined"])
    ).clip(lower=0)

    set_plot_style()

    colors = {
        "Lab": "#0B3C5D",
        "Real-world": "#2A9D8F",
        "Combined lab+field": "#A8E6CF",
        "Other/NA": "#D7DEE3",
    }

    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=300)
    left = np.zeros(len(count_table))
    y_labels = count_table.index.tolist()
    totals = summary["total"].to_numpy()

    for column in ["Lab", "Real-world", "Combined lab+field", "Other/NA"]:
        values = count_table[column].to_numpy()
        bars = ax.barh(y_labels, values, left=left, color=colors[column], height=0.62, label=column)
        for bar, value, total in zip(bars, values, totals):
            pct_value = (value / total * 100) if total > 0 else 0
            if pct_value >= 9:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{pct_value:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if column in {"Lab", "Real-world"} else "#1F1F1F",
                )
        left += values

    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("Study Design by Research Object", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of studies", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    max_total = int(summary["total"].max())
    ax.set_xlim(0, max_total * 1.12)
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    for i, (topic, total) in enumerate(summary["total"].items()):
        ax.text(total + max_total * 0.01, i, f"n={int(total)}", va="center", ha="left", fontsize=8, color="#555555")

    ax.legend(frameon=False, loc="lower right", ncol=2)
    fig.tight_layout()
    export_figure(fig, "study_design_by_research_object")
    plt.close(fig)


def plot_non_replicability_by_topic(df: pd.DataFrame) -> None:
    topic_labels = {
        "Nature & restorative environments",
        "Architectural & built interior spaces",
        "Urban outdoor environments",
        "Multisensory & environmental stimuli",
        "Methods & technology",
    }

    topic_rows = []
    for _, row in df.iterrows():
        raw_topics = split_values(row.get("Research Topic"))
        mapped_topics = [topic for topic in raw_topics if topic in topic_labels]
        if not mapped_topics:
            continue
        for topic in mapped_topics:
            topic_rows.append({
                "topic": topic,
                "replicable": bool(row.get("replicable", False)),
            })

    if not topic_rows:
        print("  No research topic data found; skipping non_replicability_by_topic plot.")
        return

    topic_frame = pd.DataFrame(topic_rows)
    summary = topic_frame.groupby("topic", sort=False).agg(
        total=("replicable", "size"),
        non_replicable=("replicable", lambda s: (~s).sum()),
    )
    summary["non_replicability_pct"] = summary["non_replicable"] / summary["total"] * 100
    summary = summary.sort_values("non_replicability_pct", ascending=True)

    set_plot_style()

    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)
    bars = ax.barh(summary.index, summary["non_replicability_pct"], color="#0B3C5D", height=0.62)

    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("Non-replicability by Research Topic", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Non-replicable share (%)", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    max_pct = float(summary["non_replicability_pct"].max()) if not summary.empty else 0.0
    for bar, (_, row) in zip(bars, summary.iterrows()):
        ax.text(
            bar.get_width() + max_pct * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{row['non_replicability_pct']:.1f}%",
            va="center",
            ha="left",
            fontsize=8,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "non_replicability_by_topic")
    plt.close(fig)


def plot_analytic_domain(df: pd.DataFrame) -> None:
    total = len(df)
    domain_counts = pd.Series({
        "Frequency domain": df["EEG_features_cat"].astype(str).str.contains(r"\b2\b", regex=True, na=False).sum(),
        "Time domain (ERP)": df["EEG_features_cat"].astype(str).str.contains(r"\b1\b", regex=True, na=False).sum(),
        "Functional connectivity": df["EEG_features_cat"].astype(str).str.contains(r"\b3\b", regex=True, na=False).sum(),
        "Source localisation": df["EEG_features_cat"].astype(str).str.contains(r"\b4\b", regex=True, na=False).sum(),
        "Proprietary output": df["EEG_features_cat"].astype(str).str.contains(r"(?:9|propriat)", regex=True, na=False).sum(),
    }).sort_values(ascending=True)

    if domain_counts.sum() == 0:
        print("  No EEG feature data found; skipping analytic_domain plot.")
        return

    set_plot_style()

    palette = {
        "Frequency domain": "#0B3C5D",
        "Time domain (ERP)": "#2A9D8F",
        "Functional connectivity": "#4CC9A6",
        "Source localisation": "#6BA8B8",
        "Proprietary output": "#A8E6CF",
    }

    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)
    bars = ax.barh(domain_counts.index, domain_counts.values, color=[palette[k] for k in domain_counts.index], height=0.62)
    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    ax.set_title("Analytic Domain Distribution", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of papers", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    max_count = int(domain_counts.max()) if not domain_counts.empty else 0
    for bar, count in zip(bars, domain_counts.values):
        ax.text(
            bar.get_width() + max_count * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{count / total * 100:.1f}%",
            va="center",
            ha="left",
            fontsize=8,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "analytic_domain_distribution")
    plt.close(fig)


def plot_frequency_bands(df: pd.DataFrame) -> None:
    ps = df["EEG_parameter_space"].astype(str)
    freq_mask = df["EEG_features_cat"].astype(str).str.contains(r"\b2\b", regex=True, na=False)
    ps_freq = df.loc[freq_mask, "EEG_parameter_space"].astype(str)
    freq_total = len(ps_freq)

    band_patterns = [
        ("Alpha", r"[⍺α]|alpha"),
        ("Beta", r"[𝛽β]|beta"),
        ("Theta", r"[𝜃θ]|theta"),
        ("Gamma", r"[λγ]|gamma"),
        ("Delta", r"[δ]|delta"),
    ]
    band_counts = pd.Series({
        label: ps_freq.str.contains(pattern, case=False, regex=True, na=False).sum()
        for label, pattern in band_patterns
    }).sort_values(ascending=True)

    if band_counts.sum() == 0:
        print("  No EEG parameter-space data found; skipping frequency_bands plot.")
        return

    set_plot_style()

    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)
    bars = ax.barh(band_counts.index, band_counts.values, color="#0B7285", height=0.62)
    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    ax.set_title("Frequency Band Prevalence", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of frequency-domain papers", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    max_count = int(band_counts.max()) if not band_counts.empty else 0
    for bar, count in zip(bars, band_counts.values):
        ax.text(
            bar.get_width() + max_count * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{count / freq_total * 100:.1f}%",
            va="center",
            ha="left",
            fontsize=8,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "frequency_band_prevalence")
    plt.close(fig)


def plot_multimodal_prevalence(df: pd.DataFrame) -> None:
    multimodal_df = df[df["other_measures"].notna()].copy()
    multimodal_total = len(multimodal_df)

    if multimodal_total == 0:
        print("  No multimodal studies found; skipping multimodal_prevalence plot.")
        return

    om = multimodal_df["other_measures"].astype(str).str.lower()
    modalities = {
        "ECG / HRV":       om.str.contains(r"ecg|hrv|heart rate", na=False),
        "EDA":             om.str.contains(r"\beda\b|galvanic|gsr|skin conduct", na=False),
        "Eye-tracking":    om.str.contains(r"eye.?track|eyetrack", na=False),
        "Blood pressure":  om.str.contains(r"blood.?press", na=False),
        "Skin temperature":om.str.contains(r"skin.?temp|temperature", na=False),
        "PPG":             om.str.contains(r"\bppg\b|photopleth", na=False),
        "Respiration":     om.str.contains(r"resp|breath", na=False),
        "EMG":             om.str.contains(r"\bemg\b|electromyo", na=False),
        "Motion / GPS":    om.str.contains(r"\bgps\b|motion|accel|inertial", na=False),
        "EOG":             om.str.contains(r"\beog\b|electrooculo", na=False),
        "Cortisol":        om.str.contains(r"cortisol", na=False),
    }
    modality_counts = pd.Series({name: mask.sum() for name, mask in modalities.items() if mask.sum() > 0}).sort_values(ascending=True)

    if modality_counts.empty:
        print("  No multimodal modality matches found; skipping multimodal_prevalence plot.")
        return

    set_plot_style()

    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)
    bars = ax.barh(modality_counts.index, modality_counts.values, color="#2A9D8F", height=0.62)
    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("Modality Prevalence in Multimodal Studies", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of multimodal studies", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    max_count = int(modality_counts.max()) if not modality_counts.empty else 0
    for bar, count in zip(bars, modality_counts.values):
        ax.text(
            bar.get_width() + max_count * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{count / multimodal_total * 100:.1f}%",
            va="center",
            ha="left",
            fontsize=8,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "multimodal_modality_prevalence")
    plt.close(fig)


def plot_multimodal_integration_pie(df: pd.DataFrame) -> None:
    eeg_only = df["other_measures"].isna().sum()
    multimodal = len(df) - eeg_only
    integrated = df["Fusion EEG-Other Modalities"].eq(1.0).sum()
    non_integrated = multimodal - integrated

    if multimodal == 0:
        print("  No multimodal studies found; skipping multimodal_integration plot.")
        return

    counts = pd.Series({
        "EEG only": eeg_only,
        "Multimodal without integration": non_integrated,
        "Integrated multimodal": integrated,
    })

    set_plot_style()

    palette = ["#16324F", "#A8E6CF", "#2A9D8F"]
    fig, ax = plt.subplots(figsize=(6.8, 4.8), dpi=300)
    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=counts.index,
        colors=palette,
        startangle=105,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",
        pctdistance=0.78,
        labeldistance=1.04,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
        textprops={"color": "#2A2A2A", "fontsize": 8},
    )
    for wedge, t in zip(wedges, autotexts):
        r, g, b, _ = wedge.get_facecolor()
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        t.set_color("white" if luminance < 0.55 else "#1F1F1F")
        t.set_fontsize(8)

    ax.set_title("EEG-only vs Multimodal Integration", loc="left", pad=8, color="#1F1F1F")
    ax.text(
        0.5, -0.08,
        f"N = {len(df)}",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    plt.tight_layout()
    export_figure(fig, "multimodal_integration_pie")
    plt.close(fig)


def plot_consumer_grade_distribution(df: pd.DataFrame) -> None:
    total = len(df)
    grade_col = "System grade (medical vs consumer)"
    if grade_col not in df.columns:
        print(f"  Column '{grade_col}' not found; skipping consumer_grade_distribution plot.")
        return

    grades = df[grade_col].fillna("NA").astype(str).str.strip().str.lower().value_counts()
    counts = pd.Series({
        "Consumer-grade": int(grades.get("consumer", 0)),
        "Medical-grade": int(grades.get("medical", 0)),
        "NA / Not reported": int(grades.get("na", 0) + grades.get("nan", 0)),
    })

    if counts.sum() == 0:
        print("  No EEG system grade data found; skipping consumer_grade_distribution plot.")
        return

    set_plot_style()
    plt.rcParams.update({
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
    })

    colors = ["#0B3C5D", "#2A9D8F", "#D7DEE3"]
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)
    bars = ax.barh(counts.index, counts.values, color=colors, height=0.62)

    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("EEG System Grade Distribution", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of studies", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    max_count = int(counts.max()) if not counts.empty else 0
    for bar, count in zip(bars, counts.values):
        pct_value = (count / total * 100) if total > 0 else 0
        ax.text(
            bar.get_width() + max_count * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{pct_value:.1f}%",
            va="center",
            ha="left",
            fontsize=10,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "consumer_grade_distribution")
    plt.close(fig)


def plot_top_eeg_systems(df: pd.DataFrame, top_n: int = 12) -> None:
    sys_counts = df["EEG_system"].dropna().astype(str).str.strip()
    sys_counts = sys_counts[sys_counts != ""].value_counts()

    if sys_counts.empty:
        print("  No EEG system data found; skipping top_eeg_systems plot.")
        return

    top_counts = sys_counts.head(top_n).sort_values(ascending=True)
    total = int(len(df))

    set_plot_style()
    plt.rcParams.update({
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 10,
    })

    fig, ax = plt.subplots(figsize=(8.2, 5.6), dpi=300)
    bars = ax.barh(top_counts.index, top_counts.values, color="#5E8CA8", height=0.62)

    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("Top EEG Systems", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of studies", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    max_count = int(top_counts.max()) if not top_counts.empty else 0
    for bar, count in zip(bars, top_counts.values):
        pct_value = (count / total * 100) if total > 0 else 0
        ax.text(
            bar.get_width() + max_count * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{pct_value:.1f}%",
            va="center",
            ha="left",
            fontsize=10,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "top_eeg_systems")
    plt.close(fig)


def plot_data_availability(df: pd.DataFrame) -> None:
    availability_col = "Data Availability"
    year_col = "Year"
    availability_map = {0: "Not available", 1: "Available upon request", 2: "Openly available"}

    availability_frame = df[[year_col, availability_col]].copy()
    availability_frame[year_col] = pd.to_numeric(availability_frame[year_col], errors="coerce")
    availability_frame = availability_frame.dropna(subset=[year_col])
    availability_frame = availability_frame[availability_frame[year_col] >= 2010]
    availability_frame[year_col] = availability_frame[year_col].astype(int)
    availability_frame[availability_col] = pd.to_numeric(availability_frame[availability_col], errors="coerce")
    availability_frame["availability_label"] = availability_frame[availability_col].map(availability_map)
    availability_frame["availability_label"] = availability_frame["availability_label"].fillna("NA")

    availability_counts = pd.crosstab(
        availability_frame[year_col],
        availability_frame["availability_label"],
    ).sort_index()

    category_order = ["Not available", "Available upon request", "Openly available", "NA"]
    availability_counts = availability_counts.reindex(columns=category_order, fill_value=0)
    availability_percent = availability_counts.div(availability_counts.sum(axis=1), axis=0) * 100

    set_plot_style()

    availability_palette = {
        "Not available": "#16324F",
        "Available upon request": "#2A9D8F",
        "Openly available": "#A8E6CF",
        "NA": "#C8DDE8",
    }

    fig, ax = plt.subplots(figsize=(7.0, 4.5), dpi=300)
    bottom = pd.Series(0, index=availability_percent.index, dtype=float)
    for category in category_order:
        values = availability_percent[category]
        bars = ax.bar(
            availability_percent.index, values, bottom=bottom,
            color=availability_palette[category], width=0.72, label=category,
        )
        for bar, value in zip(bars, values):
            if value >= 10:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{value:.0f}%",
                    ha="center", va="center", fontsize=8,
                    color="white" if category in {"Not available", "Available upon request"} else "#1F1F1F",
                )
        bottom = bottom + values.fillna(0)

    ax.set_title("Data Availability by Year", pad=8, loc="left", color="#1F1F1F")
    ax.set_xlabel("Year", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("Within-year share (%)", color="#3A3A3A", labelpad=6)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#555555", length=0)
    ax.grid(axis="y", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    legend_handles = [
        mpatches.Patch(color=availability_palette["Not available"], label="Not available"),
        mpatches.Patch(color=availability_palette["Available upon request"], label="Available upon request"),
        mpatches.Patch(color=availability_palette["Openly available"], label="Openly available"),
        mpatches.Patch(color=availability_palette["NA"], label="NA"),
    ]
    ax.legend(handles=legend_handles, frameon=True, loc="upper left", ncol=2)
    fig.tight_layout()
    export_figure(fig, "data_availability_by_year")
    plt.close(fig)


def plot_mean_age(df: pd.DataFrame) -> None:
    mean_age = pd.to_numeric(df["mean_age_participants"], errors="coerce").dropna()

    age_median = mean_age.median()
    age_q1 = mean_age.quantile(0.25)
    age_q3 = mean_age.quantile(0.75)

    set_plot_style()
    plt.rcParams.update({"axes.titlesize": 16, "axes.labelsize": 14, "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 15})

    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.hist(mean_age, bins=24, color="#6BA8B8", edgecolor="white", linewidth=0.8, alpha=0.9)
    ax.axvspan(age_q1, age_q3, alpha=0.15, color="#0B3C5D", label=f"IQR: {age_q1:.1f}–{age_q3:.1f}")
    ax.axvline(age_median, color="#0B3C5D", linestyle="--", linewidth=1.5,
               label=f"Median: {age_median:.1f}", zorder=3)

    ax.set_title("Distribution of mean participant age", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Mean age participants", color="#3A3A3A")
    ax.set_ylabel("Number of studies", color="#3A3A3A")
    ax.grid(axis="y", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#555555", length=0)
    ax.legend(frameon=False, loc="upper right", fontsize=15)
    ax.set_ylim(0, 120)

    fig.tight_layout()
    export_figure(fig, "mean_age_participants_distribution")
    plt.close(fig)


def plot_age_ranges(df: pd.DataFrame) -> None:
    def parse_age_interval(value: object):
        text = str(value).strip()
        if not text or text.upper() == "NA":
            return None
        if "-" in text:
            start_text, end_text = [p.strip() for p in text.split("-", 1)]
            start_match = re.search(r"\d+", start_text)
            end_match = re.search(r"\d+", end_text)
            if not start_match or not end_match:
                return None
            return {"label": f"{start_match.group(0)}-{end_match.group(0)}",
                    "start": int(start_match.group(0)),
                    "end": int(end_match.group(0))}
        return None

    age_col = next(col for col in df.columns if col.lower() == "age_range")
    age_series = df[age_col].dropna().astype(str).str.strip()
    interval_records = [iv for iv in age_series.apply(parse_age_interval) if iv is not None]

    if not interval_records:
        print("  No age interval data found; skipping age_ranges plot.")
        return

    study_intervals = pd.DataFrame(interval_records)
    interval_table = study_intervals.copy()
    interval_counts = interval_table["label"].value_counts().to_dict()
    interval_table = interval_table.drop_duplicates(subset=["label"]).copy()
    interval_table["count"] = interval_table["label"].map(interval_counts).fillna(1).astype(int)
    interval_table = interval_table.assign(midpoint=(interval_table["start"] + interval_table["end"]) / 2)
    interval_table = interval_table.sort_values(
        ["midpoint", "start", "end", "label"], ascending=[False, False, False, False]
    ).reset_index(drop=True)

    expanded_ages = []
    for _, row in interval_table.iterrows():
        expanded_ages.extend(range(int(row["start"]), int(row["end"]) + 1))

    fig, ax = plt.subplots(figsize=(8.2, 4.8), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    kde = stats.gaussian_kde(expanded_ages)
    x_range = np.linspace(min(expanded_ages) - 2, max(expanded_ages) + 2, 200)
    density = kde(x_range)
    num_ranges = len(interval_table)
    density_scaled = density / density.max() * max(1.0, num_ranges - 1)

    ax.fill_between(x_range, 0, density_scaled, color="#d7dee8", alpha=0.65, label="Age density", zorder=0)
    ax.plot(x_range, density_scaled, color="#a3b8c4", linewidth=1.2, alpha=0.75, zorder=1)

    x_left = min(expanded_ages) - 2
    x_right = max(expanded_ages) + 2
    y_top = num_ranges - 0.5
    ax.axvspan(x_left, 21, color="#cfcfcf", alpha=0.3, zorder=0.5)
    ax.axvspan(60, x_right, color="#c4c4c4", alpha=0.3, zorder=0.5)
    ax.text((x_left + 21) / 2, y_top * 0.96, "<21", ha="center", va="top", fontsize=7, color="#6d6d6d")
    ax.text((60 + x_right) / 2, y_top * 0.96, ">60", ha="center", va="top", fontsize=7, color="#6d6d6d")

    segments = [[(row["start"], idx), (row["end"], idx)] for idx, row in interval_table.iterrows()]
    lc = LineCollection(segments, colors="#0b7285", linewidths=2.2, alpha=0.75, zorder=2)
    ax.add_collection(lc)

    ax.set_xlim(x_left, x_right)
    ax.set_ylim(-0.5, y_top)
    ax.set_yticks([])
    ax.set_xlabel("Age", fontsize=8)
    ax.set_ylabel("Reported age ranges", fontsize=8)
    ax.set_title("Age ranges with distribution", fontsize=10, pad=10)
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.6, alpha=0.7)
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend_handles = [
        mpatches.Patch(color="#d7dee8", label="Age coverage density"),
        mpatches.Patch(color="#0b7285", label="Reported ranges"),
    ]
    ax.legend(handles=legend_handles, frameon=True, loc="upper right", fontsize=7)
    fig.tight_layout()
    export_figure(fig, "age_ranges_distribution")
    plt.close(fig)


def plot_age_coverage(df: pd.DataFrame) -> None:
    def parse_age_interval(value: object):
        text = str(value).strip()
        if not text or text.upper() == "NA" or "-" not in text:
            return None
        start_text, end_text = [p.strip() for p in text.split("-", 1)]
        start_match = re.search(r"\d+", start_text)
        end_match = re.search(r"\d+", end_text)
        if not start_match or not end_match:
            return None
        return int(start_match.group(0)), int(end_match.group(0))

    age_col = next(col for col in df.columns if col.lower() == "age_range")
    age_series = df[age_col].dropna().astype(str).str.strip()
    intervals = [iv for iv in age_series.apply(parse_age_interval) if iv is not None]

    if not intervals:
        print("  No age interval data found; skipping age_coverage plot.")
        return

    ages = []
    for start, end in intervals:
        ages.extend(range(start, end + 1))

    coverage = pd.Series(ages).value_counts().sort_index()
    age_axis = np.arange(int(coverage.index.min()), int(coverage.index.max()) + 1)
    coverage = coverage.reindex(age_axis, fill_value=0)

    fig, ax = plt.subplots(figsize=(8.2, 4.8), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.fill_between(age_axis, coverage.values, color="#0b7285", alpha=0.18)
    ax.plot(age_axis, coverage.values, color="#0b7285", linewidth=2.0)
    ax.scatter(age_axis, coverage.values, s=10, color="#0b7285", alpha=0.65, linewidths=0)

    ax.set_title("Age coverage across reported ranges", fontsize=11, pad=10)
    ax.set_xlabel("Age", fontsize=8)
    ax.set_ylabel("Number of ranges covering age", fontsize=8)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6, alpha=0.7)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    export_figure(fig, "age_coverage_curve")
    plt.close(fig)


def plot_publication_year(df: pd.DataFrame) -> None:
    set_plot_style()
    plt.rcParams.update({
        "axes.titlesize": 16,
        "axes.labelsize": 14,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "legend.fontsize": 15,
    })

    years = pd.to_numeric(df["Year"], errors="coerce").dropna()
    if years.empty:
        print("  No year data found; skipping publication_year plot.")
        return
    year_median = years.median()

    BREAK_START = 1984
    BREAK_END = 2005

    years_left = years[years < BREAK_START]
    years_right = years[years >= BREAK_END]

    if years_left.empty or years_right.empty:
        print("  Year distribution does not span the intended break; skipping publication_year plot.")
        return

    left_min, left_max = int(years_left.min()), BREAK_START - 1
    right_min, right_max = BREAK_END, int(years.max())

    bins_left = np.arange(left_min - 0.5, left_max + 1.5, 1)
    bins_right = np.arange(right_min - 0.5, right_max + 1.5, 1)

    left_span = left_max - left_min + 1
    right_span = right_max - right_min + 1

    fig, (ax_l, ax_r) = plt.subplots(
        1, 2, figsize=(7.2, 4.6), dpi=300,
        gridspec_kw={"width_ratios": [left_span, right_span], "wspace": 0.04},
    )
    fig.patch.set_facecolor("white")

    bar_kw = dict(color="#5E8CA8", edgecolor="white", linewidth=0.8, alpha=0.9)
    ax_l.hist(years_left, bins=bins_left, **bar_kw)
    ax_r.hist(years_right, bins=bins_right, **bar_kw)

    if ax_r.patches:
        ax_r.patches[-1].set_hatch("///")

    y_max = 120
    ax_l.set_ylim(0, y_max)
    ax_r.set_ylim(0, y_max)
    ax_r.set_yticklabels([])
    ax_r.tick_params(axis="y", length=0)

    if year_median < BREAK_START:
        ax_l.axvline(year_median, color="#0B3C5D", linestyle="--", linewidth=1.5,
                     label=f"Median: {int(year_median)}", zorder=3)
    else:
        ax_r.axvline(year_median, color="#0B3C5D", linestyle="--", linewidth=1.5,
                     label=f"Median: {int(year_median)}", zorder=3)

    ax_l.set_ylabel("Number of studies", color="#3A3A3A")
    ax_l.set_xlabel("")
    ax_r.set_xlabel("")
    fig.text(0.5, 0.01, "Year", ha="center", va="bottom", fontsize=14, color="#3A3A3A")
    ax_l.set_title("Publication year distribution", loc="left", pad=8, color="#1F1F1F")
    ax_l.set_xticks([1981])

    ax_l.margins(y=0.12)
    ax_r.margins(y=0.12)
    ax_l.set_ylim(0, y_max)
    ax_r.set_ylim(0, y_max)

    for ax in (ax_l, ax_r):
        ax.grid(axis="y", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
        ax.set_axisbelow(True)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(axis="x", colors="#555555", length=0)
        ax.tick_params(axis="y", colors="#555555", length=0)

    ax_l.spines["right"].set_visible(False)
    ax_r.spines["left"].set_visible(False)

    ax_l.text(1981, 8, "Ulrich, 1981", ha="center", va="bottom",
              fontsize=11, color="#555555", zorder=5, clip_on=False)

    d_x, d_y = 0.008, 0.025

    def add_break_marks(ax, side):
        x_fig, _ = ax.transAxes.transform((1.0 if side == "right" else 0.0, 0.0))
        x_fig /= fig.bbox.width
        _, y_fig = ax.transAxes.transform((0.0, 0.0))
        y_fig /= fig.bbox.height
        for x_offset in (-0.012, 0.0):
            x0 = x_fig + x_offset - d_x
            x1 = x_fig + x_offset + d_x
            y0 = y_fig - d_y
            y1 = y_fig + d_y
            fig.lines.append(plt.Line2D(
                [x0, x1], [y0, y1],
                transform=fig.transFigure,
                color="#888888", linewidth=1.1, clip_on=False, zorder=10,
            ))

    add_break_marks(ax_l, "right")
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.13, top=0.90, wspace=0.04)
    export_figure(fig, "publication_year_distribution")
    plt.close(fig)


def plot_sex_split(df: pd.DataFrame) -> None:
    sex_raw = df["sex_perc_male"].astype(str).str.strip()
    sex_clean = sex_raw.str.replace("%", "", regex=False).str.strip()
    sex = pd.to_numeric(sex_clean, errors="coerce").dropna()

    if sex.empty:
        print("  No sex data found; skipping sex_split plot.")
        return

    sex_min = sex.min()
    sex_max = sex.max()
    sex_median = sex.median()

    set_plot_style()
    plt.rcParams.update({"axes.titlesize": 16, "axes.labelsize": 14, "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 15})

    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.hist(sex, bins=24, color="#2A9D8F", edgecolor="white", linewidth=0.8, alpha=0.9)
    ax.axvspan(sex_min - 5, 50, color="#E8D4D4", alpha=0.2, zorder=0)
    ax.axvspan(50, sex_max + 5, color="#D4E8E8", alpha=0.2, zorder=0)

    y_top = ax.get_ylim()[1]
    ax.text(25, y_top * 0.92, "Female majority", ha="center", fontsize=9, color="#8B5A5A")
    ax.text(75, y_top * 0.92, "Male majority", ha="center", fontsize=9, color="#5A8B8B")

    ax.set_title("Distribution of sex split (% male)", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Percentage male", color="#3A3A3A")
    ax.set_ylabel("Number of studies", color="#3A3A3A")
    ax.set_xlim(sex_min - 5, sex_max + 5)
    ax.grid(axis="y", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#555555", length=0)

    fig.tight_layout()
    export_figure(fig, "sex_split_distribution")
    plt.close(fig)


def plot_replicability_criteria(df: pd.DataFrame) -> None:
    required_rates: list[tuple[str, float]] = []
    for col, label in NECESSARY_COLS.items():
        required_rates.append((label, df[f"rep_{col}"].mean()))
    required_rates.append(("Offline filters", df["rep_offline_filter"].mean()))
    required_rates.sort(key=lambda item: item[1])

    if not required_rates:
        print("  No replicability criteria found; skipping replicability_criteria plot.")
        return

    set_plot_style()

    labels = [label for label, _ in required_rates]
    values = [rate * 100 for _, rate in required_rates]
    fig, ax = plt.subplots(figsize=(7.4, 4.8), dpi=300)
    bars = ax.barh(labels, values, color="#0B3C5D", height=0.62)
    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    ax.set_title("Replicability Criteria Reporting Rates", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Papers reporting the criterion (%)", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.set_xlim(0, 100)
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    for bar, value in zip(bars, values):
        ax.text(
            min(bar.get_width() + 1.5, 99.0),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%",
            va="center",
            ha="left",
            fontsize=8,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "replicability_criteria_reporting")
    plt.close(fig)


def plot_replicability_summary(df: pd.DataFrame) -> None:
    if "replicable" not in df.columns:
        print("  Replicability scores not available; skipping replicability_summary plot.")
        return

    replicable = int(df["replicable"].sum())
    non_replicable = int(len(df) - replicable)

    if len(df) == 0:
        print("  No studies found; skipping replicability_summary plot.")
        return

    set_plot_style()

    counts = pd.Series({
        "Replicable": replicable,
        "Non-replicable": non_replicable,
    })

    fig, ax = plt.subplots(figsize=(6.2, 4.8), dpi=300)
    colors = ["#2A9D8F", "#16324F"]
    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=counts.index,
        colors=colors,
        startangle=105,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",
        pctdistance=0.78,
        labeldistance=1.04,
        wedgeprops={"linewidth": 0.9, "edgecolor": "white"},
        textprops={"color": "#2A2A2A", "fontsize": 9},
    )
    for wedge, autotext in zip(wedges, autotexts):
        r, g, b, _ = wedge.get_facecolor()
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        autotext.set_color("white" if luminance < 0.52 else "#3A3A3A")
        autotext.set_fontsize(9)

    ax.set_title("Replicable vs Non-replicable Studies", loc="left", pad=8, color="#1F1F1F")
    ax.text(
        0,
        -1.15,
        f"Replicable: {replicable}  |  Non-replicable: {non_replicable}",
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout()
    export_figure(fig, "replicability_summary")
    plt.close(fig)


def plot_replicability_by_venue(df: pd.DataFrame) -> None:
    if "replicable" not in df.columns:
        print("  Replicability scores not available; skipping replicability_by_venue plot.")
        return

    venue_frame = df.copy()
    venue_frame["_venue"] = venue_frame["Journal"].apply(classify_venue)
    venue_counts = venue_frame["_venue"].value_counts()
    venue_summary = venue_frame.groupby("_venue")["replicable"].agg(total="size", replicable="sum")
    venue_summary["replicable_pct"] = venue_summary["replicable"] / venue_summary["total"] * 100
    venue_summary = venue_summary.reindex(venue_counts.index).dropna(subset=["replicable_pct"])

    if venue_summary.empty:
        print("  No venue groups found; skipping replicability_by_venue plot.")
        return

    venue_summary = venue_summary.sort_values("replicable_pct", ascending=True)

    set_plot_style()

    palette = {
        "Architecture / Built-environment / Design": "#0B3C5D",
        "Nature / Environment / Landscape / Health": "#2A9D8F",
        "Engineering / Acoustics / Technology": "#4CC9A6",
        "Neuroscience / Psychology": "#6BA8B8",
        "Other / Unclassified": "#A8E6CF",
    }

    labels = venue_summary.index.tolist()
    values = venue_summary["replicable_pct"].tolist()
    colors = [palette.get(label, "#7C817A") for label in labels]

    fig, ax = plt.subplots(figsize=(7.6, 4.8), dpi=300)
    bars = ax.barh(labels, values, color=colors, height=0.62)
    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("Replicable Studies by Publishing Venue", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Replicable share within venue group (%)", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.set_xlim(0, 100)
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    for bar, (_, row) in zip(bars, venue_summary.iterrows()):
        ax.text(
            min(bar.get_width() + 1.5, 99.0),
            bar.get_y() + bar.get_height() / 2,
            f"{row['replicable_pct']:.1f}%",
            va="center",
            ha="left",
            fontsize=8,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "replicability_by_venue")
    plt.close(fig)


def plot_top_journals(df: pd.DataFrame, top_n: int = 10) -> None:
    journal_counts = df["Journal"].dropna().astype(str).str.strip()
    journal_counts = journal_counts[journal_counts != ""].value_counts()

    if journal_counts.empty:
        print("  No journal data found; skipping top_journals plot.")
        return

    top_counts = journal_counts.head(top_n)
    other_count = int(journal_counts.iloc[top_n:].sum()) if len(journal_counts) > top_n else 0
    if other_count > 0:
        top_counts.loc["Other"] = other_count

    top_counts = top_counts.sort_values(ascending=True)
    total = int(top_counts.sum())

    set_plot_style()

    colors = ["#6BA8B8" if label != "Other" else "#A8E6CF" for label in top_counts.index]
    fig, ax = plt.subplots(figsize=(8.0, 5.2), dpi=300)
    bars = ax.barh(top_counts.index, top_counts.values, color=colors, height=0.62)
    ax.grid(axis="x", color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.set_title("Top Journals (Remaining as Other)", loc="left", pad=8, color="#1F1F1F")
    ax.set_xlabel("Number of papers", color="#3A3A3A", labelpad=6)
    ax.set_ylabel("")
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#2A2A2A", length=0, pad=6)

    max_count = int(top_counts.max())
    for bar, count in zip(bars, top_counts.values):
        pct_value = count / total * 100 if total > 0 else 0
        ax.text(
            bar.get_width() + max_count * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{pct_value:.1f}%",
            va="center",
            ha="left",
            fontsize=8,
            color="#4A4A4A",
        )

    fig.tight_layout()
    export_figure(fig, "top_journals_distribution")
    plt.close(fig)


def plot_journal_category_pie(df: pd.DataFrame) -> None:
    venue_labels = df["Journal"].apply(classify_venue)
    venue_counts = venue_labels.value_counts()

    if venue_counts.empty:
        print("  No journal category data found; skipping journal_category_pie plot.")
        return

    set_plot_style()

    palette = {
        "Architecture / Built-environment / Design": "#0B3C5D",
        "Nature / Environment / Landscape / Health": "#2A9D8F",
        "Engineering / Acoustics / Technology": "#4CC9A6",
        "Neuroscience / Psychology": "#6BA8B8",
        "Other / Unclassified": "#A8E6CF",
    }
    colors = [palette.get(label, "#7C817A") for label in venue_counts.index]

    fig, ax = plt.subplots(figsize=(7.0, 4.8), dpi=300)
    wedges, texts, autotexts = ax.pie(
        venue_counts.values,
        labels=venue_counts.index,
        colors=colors,
        startangle=105,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",
        pctdistance=0.78,
        labeldistance=1.04,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
        textprops={"color": "#2A2A2A", "fontsize": 8},
    )
    for wedge, autotext in zip(wedges, autotexts):
        r, g, b, _ = wedge.get_facecolor()
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        autotext.set_color("white" if luminance < 0.52 else "#3A3A3A")
        autotext.set_fontsize(8)

    ax.set_title("Journal Category Distribution", loc="left", pad=8, color="#1F1F1F")
    fig.tight_layout()
    export_figure(fig, "journal_category_distribution")
    plt.close(fig)


