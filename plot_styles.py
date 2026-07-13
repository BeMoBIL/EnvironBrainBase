"""
Shared plot styles and color palettes for EEG paper visualizations.
This module contains all styling configurations for consistent plotting
across the project.
"""

import matplotlib.pyplot as plt
from matplotlib import cm

# ============================================================================
# FONT CONFIGURATION
# ============================================================================

FONT_STACK = [
    "Neue Haas Grotesk Text Pro",
    "Neue Haas Grotesk Display Pro",
    "Neue Haas Grotesk",
    "Avenir Next",
    "Helvetica Neue",
    "Futura",
    "DejaVu Sans",
]

# ============================================================================
# FONT SIZE SCHEMES
# ============================================================================

FONTSIZE_SMALL = {
    "axes.titlesize": 11,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
}

FONTSIZE_LARGE = {
    "axes.titlesize": 16,
    "axes.labelsize": 14,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "legend.fontsize": 15,
}

# ============================================================================
# COMPLETE STYLE CONFIGURATIONS
# ============================================================================

STYLE_SMALL = {
    "font.family": "sans-serif",
    "mathtext.fontset": "stix",
    "font.sans-serif": FONT_STACK,
    **FONTSIZE_SMALL,
}

STYLE_LARGE = {
    "font.family": "sans-serif",
    "mathtext.fontset": "stix",
    "font.sans-serif": FONT_STACK,
    **FONTSIZE_LARGE,
}

# ============================================================================
# COLOR PALETTES
# ============================================================================

# Research Topic / Environmental Focus
RESEARCH_TOPIC_PALETTE = {
    "nature": "#4C9A74",
    "architectural": None,  # viridis(0.18) - see setup_research_topic_colors()
    "urban": None,  # viridis(0.42)
    "ambient": None,  # viridis(0.68)
    "methods": None,  # viridis(0.90)
    "other": "#7C817A",
}

RESEARCH_TOPIC_CATEGORY_MAP = {
    "Nature & restorative environments": "nature",
    "Architectural & built interior spaces": "architectural",
    "Urban outdoor environments": "urban",
    "Multisensory & environmental stimuli": "ambient",
    "Methods & technology": "methods",
}

# Motivation Distribution
MOTIVATION_PALETTE = [
    "#16324F",  # deep navy
    "#1D5F7A",  # dark teal-blue
    "#2A9D8F",  # teal
    "#4CC9A6",  # bright sea green
    "#6ED8B5",  # light mint
    "#A8E6CF",  # pale mint
    "#D4F1EF",  # very light aqua
    "#8AC6E8",  # sky blue
    "#5E8CA8",  # slate blue
    "#C8DDE8",  # pale blue-gray
]

# Data Availability
AVAILABILITY_PALETTE = {
    "Not available": "#16324F",
    "Available upon request": "#2A9D8F",
    "Openly available": "#A8E6CF",
    "NA": "#C8DDE8",
}

# Age-related visualizations
AGE_COLORS = {
    "histogram": "#6BA8B8",
    "iqr_shade": "#0B3C5D",
    "line": "#0B3C5D",
    "coverage": "#0b7285",
    "density": "#d7dee8",
    "density_line": "#a3b8c4",
}

# Sex split visualization
SEX_HISTOGRAM_COLOR = "#2A9D8F"
SEX_FEMALE_DOMINANT_SHADE = "#E8D4D4"
SEX_MALE_DOMINANT_SHADE = "#D4E8E8"

# Publication year
PUBLICATION_BAR_COLOR = "#5E8CA8"

# Hardware grade colors
CONSUMER_COLOR = "#C1535C"
RESEARCH_COLOR = "#2A6496"
OTHER_COLOR = "#9EAAB5"

# Replicability
REPLICABLE_COLOR = "#4C9A74"
NON_REPLICABLE_COLOR = "#C1535C"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def apply_style(style_dict):
    """Apply a complete style configuration."""
    plt.rcParams.update(style_dict)


def apply_style_small():
    """Apply the small font size style."""
    apply_style(STYLE_SMALL)


def apply_style_large():
    """Apply the large font size style."""
    apply_style(STYLE_LARGE)


def setup_research_topic_colors():
    """
    Setup research topic colors using viridis colormap.
    Call this once before using RESEARCH_TOPIC_PALETTE.
    """
    viridis = cm.get_cmap("viridis")
    RESEARCH_TOPIC_PALETTE["architectural"] = viridis(0.18)
    RESEARCH_TOPIC_PALETTE["urban"] = viridis(0.42)
    RESEARCH_TOPIC_PALETTE["ambient"] = viridis(0.68)
    RESEARCH_TOPIC_PALETTE["methods"] = viridis(0.90)


def get_research_topic_color(category):
    """Get color for a research topic category."""
    if category in RESEARCH_TOPIC_CATEGORY_MAP:
        key = RESEARCH_TOPIC_CATEGORY_MAP[category]
        return RESEARCH_TOPIC_PALETTE.get(key, RESEARCH_TOPIC_PALETTE["other"])
    return RESEARCH_TOPIC_PALETTE["other"]


def style_axes(ax, grid=True):
    """Apply standard spine/grid/tick styling to an axes."""
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    if grid:
        ax.yaxis.grid(True, color="#D9D7D0", linestyle="-", linewidth=0.6, alpha=0.55)
        ax.set_axisbelow(True)
    ax.tick_params(axis="x", colors="#555555", length=0)
    ax.tick_params(axis="y", colors="#555555", length=0)
    ax.set_facecolor("white")


# ============================================================================
# STANDARD PLOT CONFIGURATIONS
# ============================================================================

SPINE_DEFAULTS = {
    "remove_spines": ["top", "right", "left", "bottom"],
}

GRID_DEFAULTS = {
    "axis": "y",
    "color": "#D9D7D0",
    "linestyle": "-",
    "linewidth": 0.6,
    "alpha": 0.55,
}

TICK_DEFAULTS_X = {
    "colors": "#555555",
    "length": 0,
}

TICK_DEFAULTS_Y = {
    "colors": "#555555",
    "length": 0,
}

# ============================================================================
# FIGURE DEFAULTS
# ============================================================================

FIGURE_DPI = 300
FIGURE_FACECOLOR = "white"
AXES_FACECOLOR = "white"

# ============================================================================
# PLOT DIMENSIONS
# ============================================================================

FIGSIZE_STANDARD = (7.2, 4.6)
FIGSIZE_WIDE = (8.2, 4.8)
FIGSIZE_PIE = (6.8, 4.8)
FIGSIZE_BAR_HORIZ = (7.0, 4.9)
FIGSIZE_DATA_AVAIL = (7.0, 4.5)
