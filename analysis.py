"""
Corpus analysis for: "Before the evidence is built: A credibility crisis in
EEG Research in Environmental Neuroscience"

Computes every metric reported in the review paper, organised by section.
Reads papers.csv directly (raw column names, no rename map dependency).

Usage:
    python replicability_assessment.py
    python replicability_assessment.py --csv path/to/papers.csv
"""

# %% Imports

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

# %%
# =============================================================================
# CONFIGURATION
# =============================================================================

# --- Replicability criteria (raw CSV column names) ---
NECESSARY_COLS: dict[str, str] = {
    "SR_in_Hz": "Sample rate",
    "filters_amp": "Hardware filter settings",
    "online_filters": "Online filters applied",
    "num_channels": "Number of channels",
    "electrode_type": "Electrode type",
    "electrode_locations": "Electrode locations",
    "reference": "Reference scheme",
    "artifact_rejection": "Artifact rejection",
    # offline filter handled separately as either/or (see offline_filter_present)
}
OFFLINE_COLS = {
    "flag": "offline_filters",
    "highpass": "Offline_High-Pass_(Hz)",
    "lowpass": "Offline_Low-Pass_(Hz)",
}
GOOD_COLS: dict[str, str] = {
    "channel_interpolation": "Channel interpolation",
    "Impedance": "Impedance",
    "EEG_company": "EEG company",
    "EEG_system": "EEG system",
}
N_MAX = len(NECESSARY_COLS) + 1  # 9 (8 simple + 1 offline either/or)

ABSENT: frozenset[str] = frozenset(
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

# --- EEG feature category codes ---
FEAT_LABELS = {
    "1": "Time domain (ERP)",
    "2": "Frequency domain",
    "3": "Connectivity",
    "4": "Source localisation",
    "9": "Proprietary",
}

# --- Consumer vs research-grade EEG companies ---
CONSUMER_COMPANIES = {
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
RESEARCH_COMPANIES = {
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

# --- Journal venue classification (keyword-based) ---
VENUE_KEYWORDS = {
    "Architecture / Built-environment / Design": [
        "building",
        "architect",
        "construction",
        "facility",
        "facilities",
        "habitat",
        "indoor",
        "interior",
        "structural",
        "built environment",
        "design stud",
        "design research",
    ],
    "Nature / Environment / Landscape / Health": [
        "environment",
        "nature",
        "landscape",
        "forest",
        "urban forest",
        "green",
        "ecological",
        "ecology",
        "land",
        "public health",
        "health promot",
        "epidemi",
        "preventive",
        "environ res",
        "sustainability",
        "sustainable",
        "cities",
        "urban plan",
        "frontiers in public",
        "int j environ",
    ],
    "Engineering / Acoustics / Technology": [
        "engineer",
        "acoustic",
        "applied sci",
        "sensor",
        "ieee",
        "signal process",
        "measurement",
        "instrum",
        "comput",
        "simulation",
        "technolog",
    ],
    "Neuroscience / Psychology": [
        "neurosci",
        "psychol",
        "brain",
        "cognit",
        "neural",
        "behav",
        "neuroimag",
        "psychophysiol",
        "neuroergon",
        "affect",
        "front hum neurosci",
        "front psychol",
        "j environ psychol",
        "sci rep",
        "scientific reports",
        "plos one",
        "elife",
        "j cog neurosci",
        "psychophysiology",
        "neuroimage",
        "j neurosci",
        "pnas",
        "euro j neurosci",
        "cerebral cortex",
        "eneuro",
        "brain sci",
    ],
}

# Western countries (for geographic analysis)
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
    "czech republic",
    "hungary",
    "israel",
}


# %%
# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def sep(title: str, width: int = 70) -> None:
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print("=" * width)


def pct(n: int, total: int) -> str:
    return f"{n} ({100 * n / total:.1f}%)"


def is_present(val: object) -> bool:
    if pd.isna(val):
        return False
    return str(val).strip().lower() not in ABSENT


def offline_filter_present(row: pd.Series) -> bool:
    """Satisfied if offline_filters is present OR both HP+LP cutoffs are present."""
    if is_present(row.get(OFFLINE_COLS["flag"], "")):
        return True
    return is_present(row.get(OFFLINE_COLS["highpass"], "")) and is_present(
        row.get(OFFLINE_COLS["lowpass"], "")
    )


def score_row(row: pd.Series) -> dict:
    # Prefix with "rep_" to avoid colliding with original CSV columns
    flags = {f"rep_{col}": is_present(row.get(col, "")) for col in NECESSARY_COLS}
    flags["rep_offline_filter"] = offline_filter_present(row)
    good = {f"good_{col}": is_present(row.get(col, "")) for col in GOOD_COLS}
    n = sum(flags.values())
    g = sum(good.values())
    return {**flags, **good, "n_necessary": n, "n_good": g, "replicable": n == N_MAX}


def parse_pct(val: object) -> float | None:
    """Parse '50%' or '0.5' style values to a 0–100 float."""
    if pd.isna(val):
        return None
    s = str(val).strip().replace("%", "")
    try:
        v = float(s)
        return v if v <= 100 else None
    except ValueError:
        return None


def classify_venue(journal: str) -> str:
    j = str(journal).lower().strip()
    # Neuroscience/Psychology checked first (takes priority over generic keywords)
    for label, kws in [
        ("Neuroscience / Psychology", VENUE_KEYWORDS["Neuroscience / Psychology"]),
        (
            "Architecture / Built-environment / Design",
            VENUE_KEYWORDS["Architecture / Built-environment / Design"],
        ),
        (
            "Nature / Environment / Landscape / Health",
            VENUE_KEYWORDS["Nature / Environment / Landscape / Health"],
        ),
        (
            "Engineering / Acoustics / Technology",
            VENUE_KEYWORDS["Engineering / Acoustics / Technology"],
        ),
    ]:
        if any(kw in j for kw in kws):
            return label
    return "Other / Unclassified"


def classify_company(company: str) -> str:
    c = str(company).lower().strip()
    if any(k in c for k in CONSUMER_COMPANIES):
        return "consumer"
    if any(k in c for k in RESEARCH_COMPANIES):
        return "research"
    return "other"


def parse_multicoded(val: object) -> list[str]:
    """Split '1, 2' or '1,2' style cells into a list of stripped tokens."""
    if pd.isna(val):
        return []
    return [t.strip() for t in re.split(r"[,;/]", str(val)) if t.strip()]


# %%
# =============================================================================
# ANALYSIS SECTIONS
# =============================================================================


def section_corpus_overview(df: pd.DataFrame) -> None:
    total = len(df)
    sep("1. CORPUS OVERVIEW")
    print(f"  Total papers (non-blank rows): {total}")
    print(f"  Year range: {int(df['Year'].min())} – {int(df['Year'].max())}")
    n_2020 = (df["Year"] >= 2020).sum()
    print(f"  Published 2020 onwards: {pct(n_2020, total)}")

    n_part = pd.to_numeric(df["num_participants"], errors="coerce")
    total_part = int(n_part.sum())
    print(f"\n  Total participants (sum): {total_part:,}")
    print(f"  Participant N reporting:  {n_part.notna().sum()} studies")
    print(f"  Median N per study:       {n_part.median():.0f}")
    print(
        f"  IQR:                      {n_part.quantile(0.25):.0f} – {n_part.quantile(0.75):.0f}"
    )
    print(f"  Range:                    {int(n_part.min())} – {int(n_part.max())}")


def section_study_design(df: pd.DataFrame) -> None:
    total = len(df)
    sep("2. STUDY DESIGN  (lab / real-world / combined)")
    lab = df["lab_realworld_binary"].eq(1).sum()
    realworld = df["lab_realworld_binary"].eq(2).sum()
    combined = df["lab_realworld_binary"].eq(3).sum()
    hmd = (
        df["EEG_system_mobile_stationary"]
        .str.lower()
        .str.strip()
        .eq("stat - hmd")
        .sum()
    )
    lab_incl_hmd = lab + hmd  # VR/HMD counted as lab
    print(f"  Lab (incl. HMD/VR): {pct(lab_incl_hmd, total)}")
    print(f"    of which HMD/VR:  {pct(hmd, total)}")
    print(f"  Real-world (mobile): {pct(realworld, total)}")
    print(f"  Combined lab+field:  {pct(combined, total)}")

    sep("  Mobility breakdown (EEG_system_mobile_stationary)")
    mob = (
        df["EEG_system_mobile_stationary"]
        .str.lower()
        .str.strip()
        .value_counts(dropna=False)
    )
    for val, cnt in mob.items():
        print(f"    {str(val):<30} {pct(cnt, total)}")


def section_demographics(df: pd.DataFrame) -> None:
    total = len(df)
    sep("3. PARTICIPANT DEMOGRAPHICS")

    # Age
    age = pd.to_numeric(df["mean_age_participants"], errors="coerce")
    age_n = age.notna().sum()
    print(f"  Mean age reported: {age_n} of {total} studies")
    print(
        f"  Median study mean age: {age.median():.1f} y  (range {age.min():.2f} – {age.max():.2f})"
    )
    age_valid = age.dropna()
    minors = (age_valid < 18).sum()
    ya = ((age_valid >= 18) & (age_valid < 30)).sum()
    adults = ((age_valid >= 30) & (age_valid < 50)).sum()
    older = (age_valid >= 50).sum()
    print(f"  Age groups (of {age_n} reporting):")
    print(f"    < 18:    {pct(minors, age_n)}")
    print(f"    18–29:   {pct(ya, age_n)}")
    print(f"    30–49:   {pct(adults, age_n)}")
    print(f"    50+:     {pct(older, age_n)}")

    # Sex
    sex_raw = df["sex_perc_male"].apply(parse_pct).dropna()
    sex_n = len(sex_raw)
    print(f"\n  Sex composition reported: {sex_n} of {total} studies")
    print(f"  Median % male: {sex_raw.median():.1f}%")
    balanced = ((sex_raw >= 40) & (sex_raw <= 60)).sum()
    maj_female = (sex_raw < 40).sum()
    maj_male = (sex_raw > 60).sum()
    print(f"  Balanced (40–60% male): {pct(balanced, sex_n)}")
    print(f"  Majority female (<40%): {pct(maj_female, sex_n)}")
    print(f"  Majority male   (>60%): {pct(maj_male, sex_n)}")


def section_replicability(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    sep("4. REPLICABILITY")

    scored = df.apply(score_row, axis=1, result_type="expand")
    df = pd.concat([df, scored], axis=1)

    replicable = df["replicable"].sum()
    non_replicable = total - replicable

    print(f"  Replicable (all {N_MAX} criteria): {pct(replicable, total)}")
    print(f"  Non-replicable:                   {pct(non_replicable, total)}")
    print(f"  Median criteria met: {df['n_necessary'].median():.1f} / {N_MAX}")
    print(f"  Mean criteria met:   {df['n_necessary'].mean():.2f} / {N_MAX}")

    sep("  Per-criterion reporting rates (sorted low → high)")
    rates: list[tuple[str, float]] = []
    for col, label in NECESSARY_COLS.items():
        rates.append((label, df[f"rep_{col}"].mean()))
    rates.append(("Offline filter (either/or)", df["rep_offline_filter"].mean()))
    rates.sort(key=lambda x: x[1])
    for label, rate in rates:
        bar = "#" * round(rate * 30)
        print(f"  {label:<35} {100 * rate:5.1f}%  {bar}")

    sep("  Good-to-have reporting rates")
    for col, label in GOOD_COLS.items():
        rate = df[f"good_{col}"].mean()
        print(f"  {label:<35} {100 * rate:5.1f}%")

    sep("  Distribution of criteria met")
    dist = df["n_necessary"].value_counts().sort_index()
    for n, count in dist.items():
        bar = "#" * round(count / total * 50)
        print(f"  {int(n)}/{N_MAX}  {count:>4} papers  {bar}")

    sep("  Replicable papers")
    rep = df[df["replicable"]][["Authors", "Year", "Title"]]
    for _, row in rep.iterrows():
        print(
            f"  [{int(row['Year'])}] {str(row['Authors'])[:35]:<35} {str(row['Title'])[:55]}"
        )

    return df


def section_domain(df: pd.DataFrame) -> None:
    total = len(df)
    sep("5. ENVIRONMENTAL DOMAIN")

    dom_col = "architecture = 1 urbanism = 2 \nnature = 3"
    df = df.copy()
    df["_dom_raw"] = df[dom_col].astype(str).str.strip()
    df["_dom_primary"] = df["_dom_raw"].apply(
        lambda v: parse_multicoded(v)[0] if parse_multicoded(v) else ""
    )
    df["_dom_multi"] = df["_dom_raw"].apply(lambda v: len(parse_multicoded(v)) > 1)

    multi = df["_dom_multi"].sum()
    undef = (df["_dom_primary"] == "").sum() + (df["_dom_primary"] == "nan").sum()
    arch = (df["_dom_primary"] == "1").sum()
    urban = (df["_dom_primary"] == "2").sum()
    nature = (df["_dom_primary"] == "3").sum()

    print(f"  Multi-domain papers:   {pct(multi, total)}")
    print(f"  Unassignable:          {pct(undef, total)}")
    print(f"  Urbanism (primary):    {pct(urban, total)}")
    print(f"  Architecture (primary):{pct(arch, total)}")
    print(f"  Nature (primary):      {pct(nature, total)}")

    # Mobility within domain
    mob_col = df["EEG_system_mobile_stationary"].str.lower().str.strip()
    for dom_code, dom_name in [
        ("1", "Architecture"),
        ("2", "Urbanism"),
        ("3", "Nature"),
    ]:
        sub = df[df["_dom_primary"] == dom_code]
        n_sub = len(sub)
        n_mobile = sub[
            mob_col.reindex(sub.index).fillna("").str.contains("mobile")
        ].shape[0]
        n_hmd = sub[mob_col.reindex(sub.index).fillna("") == "stat - hmd"].shape[0]
        n_stat = sub[mob_col.reindex(sub.index).fillna("") == "stat"].shape[0]
        print(f"\n  {dom_name} (n={n_sub}):")
        print(f"    Stationary lab: {pct(n_stat, n_sub)}")
        print(f"    HMD/VR:         {pct(n_hmd, n_sub)}")
        print(f"    Mobile:         {pct(n_mobile, n_sub)}")

    # Non-replicability by domain
    if "replicable" in df.columns:
        sep("  Non-replicability by domain")
        for dom_code, dom_name in [
            ("1", "Architecture"),
            ("2", "Urbanism"),
            ("3", "Nature"),
        ]:
            sub = df[df["_dom_primary"] == dom_code]
            nr = (~sub["replicable"]).sum()
            print(f"  {dom_name:<15} non-replicable: {pct(nr, len(sub))}")


def section_research_focus(df: pd.DataFrame) -> None:
    total = len(df)
    sep("6. RESEARCH FOCUS & MOTIVATION")

    print("  Research Topic:")
    for topic, cnt in df["Research Topic"].value_counts(dropna=False).head(8).items():
        print(f"    {str(topic):<55} {pct(cnt, total)}")

    print("\n  Motivation:")
    mot = df["Motivation"].value_counts(dropna=False)
    for val, cnt in mot.items():
        print(f"    {str(val):<45} {pct(cnt, total)}")

    # Grouped motivation
    mot_lower = df["Motivation"].str.lower().str.strip().fillna("")
    design_policy = mot_lower.isin(
        ["design optimisation", "planning & policy evidence"]
    ).sum()
    fundamental = mot_lower.eq("fundamental understanding").sum()
    theory_testing = mot_lower.eq("theory testing").sum()
    methdev = mot_lower.eq("methodological development").sum()
    health = mot_lower.eq("health & therapeutic applications").sum()
    print("\n  Grouped:")
    print(f"    Design optimisation + planning/policy: {pct(design_policy, total)}")
    print(f"    Fundamental understanding:             {pct(fundamental, total)}")
    print(f"    Methodological development:            {pct(methdev, total)}")
    print(f"    Health & therapeutic:                  {pct(health, total)}")
    print(f"    Theory testing:                        {pct(theory_testing, total)}")


def section_eeg_features(df: pd.DataFrame) -> None:
    total = len(df)
    sep("7. EEG FEATURES & ANALYTIC DOMAIN")

    # Parse EEG_features_cat (may be multi-coded: "1, 2")
    feat_col = "EEG_features_cat"
    has_erp = (
        df[feat_col].astype(str).str.contains(r"\b1\b", regex=True, na=False).sum()
    )
    has_freq = (
        df[feat_col].astype(str).str.contains(r"\b2\b", regex=True, na=False).sum()
    )
    has_conn = (
        df[feat_col].astype(str).str.contains(r"\b3\b", regex=True, na=False).sum()
    )
    has_src = (
        df[feat_col].astype(str).str.contains(r"\b4\b", regex=True, na=False).sum()
    )
    has_prop = (
        df[feat_col]
        .astype(str)
        .str.contains(r"(?:9|propriat)", regex=True, na=False)
        .sum()
    )
    both_12 = df[feat_col].astype(str).str.contains(r"\b1\b", na=False) & df[
        feat_col
    ].astype(str).str.contains(r"\b2\b", na=False)
    n_both_12 = both_12.sum()

    print(f"  Frequency domain:           {pct(has_freq, total)}")
    print(f"  Time domain (ERP):          {pct(has_erp, total)}")
    print(f"  Functional connectivity:    {pct(has_conn, total)}")
    print(f"  Source localisation:        {pct(has_src, total)}")
    print(f"  Proprietary output:         {pct(has_prop, total)}")
    print(f"  Both time + freq domain:    {pct(n_both_12, total)}")

    # Frequency bands from EEG_parameter_space
    sep("  Frequency band prevalence (EEG_parameter_space)")
    ps = df["EEG_parameter_space"].astype(str)
    # Unicode characters used in the CSV
    alpha_pat = r"[⍺α]|alpha"
    beta_pat = r"[𝛽β]|beta"
    theta_pat = r"[𝜃θ]|theta"
    gamma_pat = r"[λγ]|gamma"  # λ is used as gamma in this CSV
    delta_pat = r"[δ]|delta"

    freq_papers = df[
        df[feat_col].astype(str).str.contains(r"\b2\b", regex=True, na=False)
    ]
    n_freq = len(freq_papers)
    ps_freq = freq_papers["EEG_parameter_space"].astype(str)

    for band, pat in [
        ("Alpha", alpha_pat),
        ("Beta", beta_pat),
        ("Theta", theta_pat),
        ("Gamma (λ)", gamma_pat),
        ("Delta", delta_pat),
    ]:
        n_band = ps_freq.str.contains(pat, case=False, regex=True, na=False).sum()
        n_all = ps.str.contains(pat, case=False, regex=True, na=False).sum()
        print(
            f"  {band:<12} in freq sub-corpus: {pct(n_band, n_freq)}  |  full corpus: {pct(n_all, total)}"
        )

    # Alpha separately from alpha_para
    alpha_any = df["alpha_para"].isin([1.0, 2.0]).sum()
    print(f"\n  Alpha (alpha_para col, any):  {pct(alpha_any, total)}")

    # ICA usage
    ica_yes = df["ica_used"].eq(1.0).sum()
    ica_no = df["ica_used"].eq(0.0).sum()
    ica_n = ica_yes + ica_no
    print(f"\n  ICA used: {pct(ica_yes, ica_n)} (of {ica_n} reporting studies)")


def section_multimodal(df: pd.DataFrame) -> None:
    total = len(df)
    sep("8. MULTIMODAL ACQUISITION & INTEGRATION")

    eeg_only = df["other_measures"].isna().sum()
    multimodal = total - eeg_only
    print(f"  EEG only (no other_measures):  {pct(eeg_only, total)}")
    print(f"  Multimodal acquisition:        {pct(multimodal, total)}")

    # Parse modalities from free-text other_measures
    om = df["other_measures"].dropna().astype(str).str.lower()
    modalities = {
        "ECG / HRV": om.str.contains(r"ecg|hrv|heart rate", na=False),
        "EDA": om.str.contains(r"\beda\b|galvanic|gsr|skin conduct", na=False),
        "Eye-tracking": om.str.contains(r"eye.?track|eyetrack", na=False),
        "Blood pressure": om.str.contains(r"blood.?press", na=False),
        "Skin temperature": om.str.contains(r"skin.?temp|temperature", na=False),
        "PPG": om.str.contains(r"\bppg\b|photopleth", na=False),
        "Respiration": om.str.contains(r"resp|breath", na=False),
        "EMG": om.str.contains(r"\bemg\b|electromyo", na=False),
        "Motion / GPS": om.str.contains(r"\bgps\b|motion|accel|inertial", na=False),
        "EOG": om.str.contains(r"\beog\b|electrooculo", na=False),
        "Cortisol": om.str.contains(r"cortisol", na=False),
    }
    print(f"\n  Modality prevalence (of {multimodal} multimodal studies):")
    for mod, mask in modalities.items():
        n = mask.sum()
        print(f"    {mod:<22} {pct(n, multimodal)}")

    # Integration
    fusion = df["Fusion EEG-Other Modalities"].eq(1.0).sum()
    subj = df["Fusion EEG-Subjective"].eq(1.0).sum()
    print(
        f"\n  Cross-modal analytical integration (Fusion EEG-Other): {pct(fusion, total)}"
    )
    print(
        f"  EEG + subjective fusion:                                {pct(subj, total)}"
    )
    if multimodal > 0:
        print(
            f"  Integration rate within multimodal studies: {pct(fusion, multimodal)}"
        )


def section_hardware(df: pd.DataFrame) -> None:
    total = len(df)
    sep("9. EEG HARDWARE")

    # Channel counts
    ch = pd.to_numeric(df["num_channels"], errors="coerce")
    ch_n = ch.notna().sum()
    print(
        f"  Channel count reported: {ch_n} of {total} studies ({100 * ch_n / total:.1f}%)"
    )
    print(
        f"  Median channels: {ch.median():.0f}  IQR: {ch.quantile(0.25):.0f}–{ch.quantile(0.75):.0f}  Mean: {ch.mean():.2f}  Range: {int(ch.min())}–{int(ch.max())}"
    )
    ch_valid = ch.dropna()
    lt20 = (ch_valid < 20).sum()
    r2131 = ((ch_valid >= 21) & (ch_valid <= 31)).sum()
    r3263 = ((ch_valid >= 32) & (ch_valid <= 63)).sum()
    ge64 = (ch_valid >= 64).sum()
    print(f"  < 20 channels:  {pct(lt20, ch_n)}")
    print(f"  21–31 channels: {pct(r2131, ch_n)}")
    print(f"  32–63 channels: {pct(r3263, ch_n)}")
    print(f"  64+ channels:   {pct(ge64, ch_n)}")

    # EEG company / device
    sep("  EEG company (top 12)")
    comp = df["EEG_company"].dropna().astype(str).str.strip()
    comp_n = len(comp)
    for company, cnt in comp.value_counts().head(12).items():
        grade = classify_company(company)
        print(f"  {company:<35} {pct(cnt, total)}  [{grade}]")

    # Consumer vs research grade
    grades = comp.apply(classify_company).value_counts()
    print(f"\n  Consumer-grade:  {pct(grades.get('consumer', 0), total)}")
    print(f"  Research-grade:  {pct(grades.get('research', 0), total)}")
    print(f"  Other/unknown:   {pct(grades.get('other', 0), total)}")
    print(f"  Not reported:    {pct(total - comp_n, total)}")

    # Top EEG systems
    sep("  EEG system (top 12)")
    sys_col = df["EEG_system"].dropna().astype(str).str.strip()
    for sys, cnt in sys_col.value_counts().head(12).items():
        print(f"  {sys:<35} {pct(cnt, total)}")

    # Emotiv family specifically
    emotiv = comp.str.lower().str.contains("emotiv").sum()
    print(f"\n  Emotiv family total: {pct(emotiv, total)}")


def section_geography(df: pd.DataFrame) -> None:
    total = len(df)
    sep("10. GEOGRAPHY")

    country = df["Country first Author Affiliation"].str.lower().str.strip()
    print("  Top 15 countries:")
    for c, cnt in country.value_counts().head(15).items():
        print(f"    {str(c):<25} {pct(cnt, total)}")

    # Western vs non-Western
    western_n = country.isin(WESTERN).sum()
    non_west = total - western_n
    print(f"\n  Western (N.Am, W.Eur, Aus): {pct(western_n, total)}")
    print(f"  Non-Western:                {pct(non_west, total)}")

    # East Asian
    east_asian = country.isin({"china", "south korea", "japan", "taiwan"}).sum()
    print(f"  East Asian:                 {pct(east_asian, total)}")

    # Non-replicability by country (if replicable column present)
    if "replicable" in df.columns:
        sep("  Non-replicability by top countries")
        top_countries = country.value_counts().head(8).index
        for c in top_countries:
            sub = df[country == c]
            nr = (~sub["replicable"]).sum()
            print(f"  {str(c).title():<20} non-replicable: {pct(nr, len(sub))}")


def section_open_science(df: pd.DataFrame) -> None:
    total = len(df)
    sep("11. OPEN SCIENCE (data availability & pre-registration)")

    da = df["Data Availability"]
    open_repo = da.eq(2.0).sum()
    on_request = da.eq(1.0).sum()
    no_stmt = da.eq(0.0).sum()
    not_coded = da.isna().sum()

    print(f"  Open repository (code 2): {pct(open_repo, total)}")
    print(f"  Available on request (1): {pct(on_request, total)}")
    print(f"  No statement (code 0):    {pct(no_stmt, total)}")
    print(f"  Not coded / NaN:          {pct(not_coded, total)}")
    print("\n  Note: pre-registration is not a separate column in the current CSV.")
    print("        The 6% / 28 studies figure requires a dedicated pre-reg field.")


def section_publication_venue(df: pd.DataFrame) -> None:
    total = len(df)
    sep("12. PUBLICATION VENUE")

    df = df.copy()
    df["_venue"] = df["Journal"].apply(classify_venue)

    print("  Venue group counts:")
    venue_counts = df["_venue"].value_counts()
    for v, cnt in venue_counts.items():
        print(f"    {v:<50} {pct(cnt, total)}")

    if "replicable" in df.columns:
        sep("  Replicability by venue group")
        rows = []
        for v in venue_counts.index:
            sub = df[df["_venue"] == v]
            rep = sub["replicable"].sum()
            nr = len(sub) - rep
            mean_score = (
                sub["n_necessary"].mean()
                if "n_necessary" in sub.columns
                else float("nan")
            )
            print(
                f"  {v:<50} n={len(sub):>3}  replicable: {pct(rep, len(sub))}  mean score: {mean_score:.2f}"
            )
            rows.append([rep, nr])

        # Chi-square test
        contingency = np.array(rows)
        # Drop rows with zero total to avoid degenerate cells
        contingency = contingency[contingency.sum(axis=1) > 0]
        if contingency.shape[0] >= 2:
            chi2, p, dof, _ = chi2_contingency(contingency)
            print(
                f"\n  Chi-square test (replicable vs not × venue): χ²({dof}) = {chi2:.2f}, p = {p:.3f}"
            )

    # Top journals overall
    sep("  Top journals (all)")
    for j, cnt in df["Journal"].value_counts().head(15).items():
        v = classify_venue(str(j))
        print(f"  {str(j):<55} {cnt:>3}  [{v[:25]}]")

    if "replicable" in df.columns:
        sep("  Journals with replicable papers")
        rep_journals = df[df["replicable"]]["Journal"].value_counts()
        for j, cnt in rep_journals.items():
            print(f"  {str(j):<55} {cnt}")


# %%
# =============================================================================
# MAIN
# =============================================================================


def main(csv_path: Path) -> None:
    df_raw = pd.read_csv(csv_path)
    df = df_raw.dropna(subset=["Title"]).copy()
    # Drop rows where Title is whitespace only
    df = df[df["Title"].str.strip().ne("")]

    print("=" * 70)
    print("  NEURO-URBANISM CORPUS ANALYSIS")
    print("  Gramann, Wieske, Estudillo & Sander (2026)")
    print("=" * 70)

    section_corpus_overview(df)
    section_study_design(df)
    section_demographics(df)
    df = section_replicability(df)  # adds replicable / n_necessary columns
    section_domain(df)
    section_research_focus(df)
    section_eeg_features(df)
    section_multimodal(df)
    section_hardware(df)
    section_geography(df)
    section_open_science(df)
    section_publication_venue(df)

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


# %% Main
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neuro-Urbanism corpus analysis")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).parent.parent
        / "NeuroUrbanism-DB"
        / "data"
        / "papers.csv",
        help="Path to papers.csv  (default: ../NeuroUrbanism-DB/data/papers.csv)",
    )
    args = parser.parse_args()
    if not args.csv.exists():
        raise FileNotFoundError(f"CSV not found: {args.csv}")
    main(args.csv)
