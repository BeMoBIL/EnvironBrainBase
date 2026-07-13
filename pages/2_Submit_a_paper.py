"""
Submit a paper: opens a Pull Request against the canonical CSV.

Behaviour:
  1. User fills the form (only the high-value fields are required; long-form
     EEG-pipeline metadata is optional and can be added later via PR review).
  2. We validate the inputs.
  3. We fetch the current data/papers.csv from GitHub via the contents API.
  4. We append the new row, push it to a fresh branch, and open a PR titled
     'Submit: <Authors> (<Year>) <Title>'.
  5. The submitter sees the PR URL.

Secrets required (in Streamlit Cloud → Settings → Secrets, or
.streamlit/secrets.toml locally):

    [github]
    token = "ghp_xxx"          # fine-grained PAT with Contents:RW + Pull-Requests:RW
    repo  = "Randomidous/EnviroBrainBase"
    base_branch = "main"

If 'token' is missing the page still renders so reviewers can see the form,
but the submit button is disabled and a banner explains why.
"""

from __future__ import annotations

import base64
import csv
import io
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import yaml

DATA_PATH = Path(__file__).parent.parent / "data" / "papers.csv"
EEG_YAML_PATH = Path(__file__).parent.parent / "data" / "eeg_systems.yaml"

st.title("✉️ Submit a paper")
st.caption(
    "Submissions are added by opening a Pull Request against the public repo. "
    "A maintainer reviews and merges; on merge, the live database updates within ~1 minute."
)

# ---------- Secrets / config ----------
gh_cfg = st.secrets.get("github", {}) if hasattr(st, "secrets") else {}
TOKEN = gh_cfg.get("token", "")
REPO = gh_cfg.get("repo", "Randomidous/EnviroBrainBase")
BASE_BRANCH = gh_cfg.get("base_branch", "main")
DATA_FILE_IN_REPO = "data/papers.csv"

if not TOKEN:
    st.warning(
        "Submission is **disabled** in this deployment because no GitHub token is configured. "
        'Maintainers: add `[github] token = "..."` to Streamlit secrets. '
        "In the meantime you can submit by opening a GitHub Issue using the *Submit a paper* template."
    )


# ---------- Load schema (column list + filled examples) ----------
@st.cache_data(show_spinner=False)
def load_columns() -> list[str]:
    return list(pd.read_csv(DATA_PATH, dtype=str, nrows=1).columns)


@st.cache_data(show_spinner=False)
def load_eeg_lookup() -> dict[str, dict]:
    """Return a dict keyed by system name (case-preserved) with all YAML fields."""
    with open(EEG_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {s["name"]: s for s in data.get("systems", [])}


COLUMNS = load_columns()
EEG_LOOKUP = load_eeg_lookup()
EEG_NAMES_SORTED = [""] + sorted(EEG_LOOKUP.keys(), key=str.lower)

MOB_OPTIONS = ["", "stat", "mob"]


# ---------- Session-state initialisation ----------
# Keys shared between the EEG picker (sidebar) and the bound form widgets.
_SS_DEFAULTS: dict[str, str] = {
    "_eeg_picker": "",
    "f_eeg_system": "",
    "f_eeg_company": "",
    "f_num_channels": "",
    "f_eeg_mob": "",
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ---------- Autofill callback ----------
def _on_eeg_pick() -> None:
    """Called when the EEG picker changes. Writes into the form-field keys."""
    chosen = st.session_state.get("_eeg_picker", "")
    if chosen and chosen in EEG_LOOKUP:
        info = EEG_LOOKUP[chosen]
        st.session_state["f_eeg_system"] = chosen
        st.session_state["f_eeg_company"] = info.get("manufacturer", "")
        channels = info.get("channels")
        st.session_state["f_num_channels"] = str(channels) if channels else ""
        mob_score = info.get("mobility_score", 0)
        st.session_state["f_eeg_mob"] = "stat" if mob_score == 0 else "mob"
    else:
        # Picker cleared: reset so user can enter values manually
        st.session_state["f_eeg_system"] = ""
        st.session_state["f_eeg_company"] = ""
        st.session_state["f_num_channels"] = ""
        st.session_state["f_eeg_mob"] = ""


# ---------- Sidebar EEG picker ----------
# Must be declared OUTSIDE st.form so on_change fires immediately (not on submit).
with st.sidebar:
    st.markdown("### 🔍 EEG system picker")
    st.caption(
        "Select a known EEG system to auto-fill manufacturer, channel count, "
        "and mobility in the form."
    )
    st.selectbox(
        "Choose EEG system",
        options=EEG_NAMES_SORTED,
        key="_eeg_picker",
        on_change=_on_eeg_pick,
        format_func=lambda v: v if v else "— type to search —",
    )
    picked = st.session_state.get("_eeg_picker", "")
    if picked and picked in EEG_LOOKUP:
        info = EEG_LOOKUP[picked]
        mob_score = info.get("mobility_score", 0)
        st.markdown(
            f"**Manufacturer:** {info.get('manufacturer', '—')}  \n"
            f"**Channels:** {info.get('channels', '—')}  \n"
            f"**Mobility:** {'Stationary' if mob_score == 0 else 'Mobile'} "
            f"(score {mob_score}/4)"
        )
        if info.get("notes"):
            st.caption(info["notes"])
        if info.get("link"):
            st.markdown(f"[Product page]({info['link']})")


# ---------- Form ----------
st.markdown(
    "Required fields are marked. Anything you don't know, leave blank: a "
    "maintainer can fill it during review."
)

with st.form("submit_form", clear_on_submit=False):
    st.subheader("Citation")
    c1, c2 = st.columns([3, 1])
    authors_short = c1.text_input(
        "Authors (short, e.g. *Smith et al.*)", help="Required"
    )
    year = c2.text_input("Year", help="Required")
    title = st.text_input("Title", help="Required")
    c1, c2 = st.columns(2)
    journal = c1.text_input("Journal / venue")
    publisher = c2.text_input("Publisher")
    authors_full = st.text_area("Full author list (with first names)", height=80)
    doi_link = st.text_input("DOI or link", help="Required if available")

    st.subheader("Sample & setting")
    c1, c2 = st.columns(2)
    sample_category = c1.selectbox(
        "Sample category",
        options=["", "1", "2", "3", "1, 2", "2, 3", "1, 3", "1, 2, 3"],
        format_func=lambda v: {
            "": ":",
            "1": "1 · Architecture",
            "2": "2 · Urbanism",
            "3": "3 · Nature",
            "1, 2": "1+2 · Architecture+Urbanism",
            "2, 3": "2+3 · Urbanism+Nature",
            "1, 3": "1+3 · Architecture+Nature",
            "1, 2, 3": "All three",
        }.get(v, v),
    )
    lab_realworld_binary = c2.selectbox(
        "Lab / real-world",
        options=["", "1", "2", "3"],
        format_func=lambda v: {
            "": "—",
            "1": "1 · Lab",
            "2": "2 · Real-world",
            "3": "3 · Mixed",
        }.get(v, v),
    )

    c1, c2, c3 = st.columns(3)
    num_participants = c1.text_input("N participants")
    age_range = c2.text_input("Age range (e.g. 18–35)")
    sex_perc_male = c3.text_input("% male (e.g. 27%)")

    # EEG setup — fields bound to session_state keys so sidebar picker can fill them.
    st.subheader("EEG setup")
    st.caption("Use the **EEG system picker** in the sidebar to auto-fill the fields below.")

    c1, c2, c3 = st.columns(3)
    eeg_system_mobile_stationary = c1.selectbox(
        "EEG system mobility",
        options=MOB_OPTIONS,
        format_func=lambda v: {"": "—", "stat": "Stationary", "mob": "Mobile"}.get(v, v),
        key="f_eeg_mob",
    )

    c1, c2 = st.columns(2)
    eeg_system = c1.text_input("EEG system / model", key="f_eeg_system")
    eeg_company = c2.text_input("Manufacturer", key="f_eeg_company")

    c1, c2, c3 = st.columns(3)
    num_channels = c1.text_input("Channels", key="f_num_channels")
    sampling_rate_hz = c2.text_input("Sampling rate (Hz)")
    reference_electrode = c3.text_input("Reference")

    st.subheader("Stimulus / paradigm")
    input_modality_cat = st.text_input(
        "Input modality (e.g. visual, auditory, multimodal)",
    )
    stimulus_material_visual = st.text_area("Stimulus material", height=70)
    independent_variable = st.text_area("Independent variable(s)", height=70)
    dependent_variable = st.text_area("Dependent variable(s)", height=70)

    st.subheader("Your details")
    c1, c2 = st.columns(2)
    contributor = c1.text_input("Your name (will appear in `contributor` column)")
    contact_email = c2.text_input("Your email (kept on the PR; not added to the CSV)")

    submit = st.form_submit_button(
        "Submit (open PR)", type="primary", disabled=not TOKEN
    )


# ---------- Helpers ----------
def _gh_headers() -> dict:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _slug(s: str, n: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:n] or "submission"


def _build_row(form: dict) -> dict:
    """Map form fields into the canonical CSV schema. Empty for everything else."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    row = {c: "" for c in COLUMNS}
    direct = {
        "authors_short": form["authors_short"],
        "year": form["year"],
        "journal": form["journal"],
        "publisher": form["publisher"],
        "authors_full": form["authors_full"],
        "title": form["title"],
        "sample_category": form["sample_category"],
        "num_participants": form["num_participants"],
        "age_range": form["age_range"],
        "sex_perc_male": form["sex_perc_male"],
        "input_modality_cat": form["input_modality_cat"],
        "stimulus_material_visual": form["stimulus_material_visual"],
        "eeg_system_mobile_stationary": form["eeg_system_mobile_stationary"],
        "lab_realworld_binary": form["lab_realworld_binary"],
        "eeg_system": form["eeg_system"],
        "eeg_company": form["eeg_company"],
        "sampling_rate_hz": form["sampling_rate_hz"],
        "num_channels": form["num_channels"],
        "reference_electrode": form["reference_electrode"],
        "independent_variable": form["independent_variable"],
        "dependent_variable": form["dependent_variable"],
        "doi_link": form["doi_link"],
        "added_date": today,
        "contributor": form["contributor"],
    }
    for k, v in direct.items():
        if k in row:
            row[k] = (v or "").strip()
    return row


def _validate(form: dict) -> list[str]:
    errors = []
    if not form["authors_short"].strip():
        errors.append("Authors (short) is required.")
    if not form["title"].strip():
        errors.append("Title is required.")
    if not form["year"].strip():
        errors.append("Year is required.")
    elif not re.fullmatch(r"(19|20)\d{2}", form["year"].strip()):
        errors.append("Year must be a four-digit year between 1900 and 2099.")
    if form["doi_link"] and not (
        form["doi_link"].startswith("http") or form["doi_link"].startswith("10.")
    ):
        errors.append("DOI / link should start with `http`, `https`, or `10.` (a DOI).")
    return errors


def _fetch_csv() -> tuple[str, str]:
    """Returns (csv_text, blob_sha)."""
    url = f"https://api.github.com/repos/{REPO}/contents/{DATA_FILE_IN_REPO}?ref={BASE_BRANCH}"
    r = requests.get(url, headers=_gh_headers(), timeout=20)
    r.raise_for_status()
    j = r.json()
    content = base64.b64decode(j["content"]).decode("utf-8")
    return content, j["sha"]


def _append_row_to_csv(csv_text: str, row: dict) -> str:
    """Read with csv.reader, append, re-emit with consistent quoting."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    fieldnames = reader.fieldnames or list(row.keys())
    rows.append({k: row.get(k, "") for k in fieldnames})
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return out.getvalue()


def _open_pr(form: dict, row: dict) -> dict:
    """Returns the PR JSON or raises."""
    csv_text, base_sha = _fetch_csv()
    new_csv = _append_row_to_csv(csv_text, row)

    # Get base ref SHA (commit) so we can branch from it.
    ref_url = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BASE_BRANCH}"
    r = requests.get(ref_url, headers=_gh_headers(), timeout=20)
    r.raise_for_status()
    base_commit_sha = r.json()["object"]["sha"]

    branch = f"submit/{_slug(form['authors_short'])}-{form['year']}-{int(time.time())}"
    create_ref = f"https://api.github.com/repos/{REPO}/git/refs"
    r = requests.post(
        create_ref,
        headers=_gh_headers(),
        json={"ref": f"refs/heads/{branch}", "sha": base_commit_sha},
        timeout=20,
    )
    r.raise_for_status()

    # Update file on the new branch.
    put_url = f"https://api.github.com/repos/{REPO}/contents/{DATA_FILE_IN_REPO}"
    commit_msg = f"Add: {form['authors_short']} ({form['year']}) {form['title'][:60]}"
    r = requests.put(
        put_url,
        headers=_gh_headers(),
        json={
            "message": commit_msg,
            "content": base64.b64encode(new_csv.encode("utf-8")).decode("ascii"),
            "sha": base_sha,
            "branch": branch,
        },
        timeout=30,
    )
    r.raise_for_status()

    # Open PR.
    body = (
        f"Automated submission via the website form.\n\n"
        f"**Title:** {form['title']}\n"
        f"**Authors:** {form['authors_short']}\n"
        f"**Year:** {form['year']}\n"
        f"**DOI / link:** {form.get('doi_link') or '_not provided_'}\n"
        f"**Submitter:** {form.get('contributor') or '_anonymous_'}"
        f" (contact: {form.get('contact_email') or '_not provided_'})\n\n"
        f"_Reviewer: please verify the row is correct, fill any gaps in the "
        f"long-form EEG/analysis fields, then merge._"
    )
    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    r = requests.post(
        pr_url,
        headers=_gh_headers(),
        json={
            "title": commit_msg,
            "head": branch,
            "base": BASE_BRANCH,
            "body": body,
            "maintainer_can_modify": True,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


# ---------- Submission handler ----------
if submit:
    form = {
        "authors_short": authors_short,
        "year": year,
        "title": title,
        "journal": journal,
        "publisher": publisher,
        "authors_full": authors_full,
        "doi_link": doi_link,
        "sample_category": sample_category,
        "lab_realworld_binary": lab_realworld_binary,
        "eeg_system_mobile_stationary": eeg_system_mobile_stationary,
        "num_participants": num_participants,
        "age_range": age_range,
        "sex_perc_male": sex_perc_male,
        "eeg_system": eeg_system,
        "eeg_company": eeg_company,
        "num_channels": num_channels,
        "sampling_rate_hz": sampling_rate_hz,
        "reference_electrode": reference_electrode,
        "input_modality_cat": input_modality_cat,
        "stimulus_material_visual": stimulus_material_visual,
        "independent_variable": independent_variable,
        "dependent_variable": dependent_variable,
        "contributor": contributor,
        "contact_email": contact_email,
    }
    errors = _validate(form)
    if errors:
        for e in errors:
            st.error(e)
    else:
        try:
            with st.spinner("Opening pull request…"):
                pr = _open_pr(form, _build_row(form))
        except requests.HTTPError as e:
            st.error(
                f"GitHub API error: {e.response.status_code} — {e.response.text[:300]}"
            )
        except Exception as e:  # pragma: no cover
            st.error(f"Unexpected error: {e}")
        else:
            st.success("Submitted! Your paper is now an open Pull Request.")
            st.markdown(f"**PR #{pr['number']}**: [{pr['title']}]({pr['html_url']})")
            st.caption(
                "A maintainer will review and merge. Once merged, the live "
                "database refreshes automatically."
            )
