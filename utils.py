"""
Shared utilities for EnvironBrainBase Streamlit pages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

_REPO_ROOT = Path(__file__).parent
_RENAME_MAP_PATH = _REPO_ROOT / "data" / "schema_rename_map.json"
_DATA_PATH = _REPO_ROOT / "data" / "papers.csv"
_EEG_SYSTEMS_PATH = _REPO_ROOT / "data" / "eeg_systems.yaml"


def _load_rename_map() -> dict[str, str]:
    with open(_RENAME_MAP_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalize_header(s: str) -> str:
    """Collapse CRLF/CR/LF differences."""
    return s.replace("\r\n", "\n").replace("\r", "\n")


_DROP_COLS: list[str] = ["comments_Analysis"]


def load_csv(path: Path | None = None) -> pd.DataFrame:
    """Read papers.csv and apply the canonical column rename map."""
    p = path or _DATA_PATH
    df = pd.read_csv(p, dtype=str).fillna("")
    rename_map = _load_rename_map()
    normalized_map = {_normalize_header(k): v for k, v in rename_map.items()}
    actual_rename = {}
    for col in df.columns:
        target = normalized_map.get(_normalize_header(col))
        if target is not None:
            actual_rename[col] = target
    df = df.rename(columns=actual_rename)
    df = df.dropna(how="all")
    return df.drop(columns=[c for c in _DROP_COLS if c in df.columns])


def load_eeg_systems() -> "dict[str, dict[str, Any]]":
    """Load the canonical EEG system lookup from data/eeg_systems.yaml.

    Returns a dict keyed by normalised system name (lowercase, stripped).
    """
    with open(_EEG_SYSTEMS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {entry["name"].strip().lower(): entry for entry in data.get("systems", [])}


def lookup_eeg_system(system_name: str, systems=None) -> "dict[str, Any]":
    """Return canonical info for system_name, or an empty dict if not found."""
    if systems is None:
        systems = load_eeg_systems()
    return systems.get(system_name.strip().lower(), {})
