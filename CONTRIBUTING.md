# Contributing to EnviroBrainBase

Thanks for helping grow the database. There are three ways to contribute, in
order of how much friction they cost you:

1. **Submit a paper via the website form**: fill in [the *Submit a paper*
   page](https://YOUR-APP-URL.streamlit.app/Submit_a_paper) and click submit. A
   pull request is opened automatically; a maintainer reviews and merges. This
   is the right path for most contributors.
2. **Open a GitHub Issue** using the *Submit a paper* template. Use this if
   the website form is down, or if you want to flag a paper without filling
   in metadata yourself.
3. **Open a Pull Request directly** against `data/papers.csv`. Use this if
   you're comfortable editing CSVs, or if you're submitting many papers at
   once.

All three paths converge on the same place: a PR that edits
`data/papers.csv`, which a maintainer reviews and merges.

---

## What goes in the database

Empirical studies that record EEG (or related neurophysiology) from human
participants in response to stimuli or environments related to **architecture,
urbanism, or nature**. Lab studies, real-world studies, and VR studies are
all in scope. Reviews and theoretical papers are out of scope (they belong in
a separate reading list: feel free to suggest one).

If you're unsure, open an Issue: better to ask than to spend an hour
extracting a paper that gets rejected.

---

## Schema

`data/papers.csv` has 63 columns. They are intentionally fine-grained because
the database is a research instrument: it has to support secondary analyses
of EEG methodology, not just paper lookup. You're not expected to fill all 63
when submitting: the **bold** fields below are required, the rest are
optional and a maintainer can fill them during review.

### Citation

| Column | Description |
| --- | --- |
| **`authors_short`** | First author family name + *et al.* (e.g. *Smith et al.*) |
| **`year`** | Four-digit year of publication |
| **`title`** | Full paper title |
| `journal` | Journal or conference venue |
| `publisher` | Publisher (e.g. Elsevier, Frontiers, MDPI) |
| `authors_full` | Comma-separated full author names with first names |
| **`doi_link`** | DOI (`10.xxxx/...`) or stable URL |

### Sample

| Column | Type | Description |
| --- | --- | --- |
| `sample_category` | enum | `1` = Architecture, `2` = Urbanism, `3` = Nature. Multi-coded papers may use `1, 2`, `2, 3`, etc. |
| `special_sample` | string | Special population notes (e.g. clinical, age group). |
| `num_participants` | int | Total N |
| `age_range` | string | e.g. `18–35` |
| `mean_age_participants` | number | |
| `sex_perc_male` | string | e.g. `27%` |

### Stimulus / paradigm

| Column | Description |
| --- | --- |
| `input_modality_cat` | `visual`, `auditory`, `multimodal`, etc. |
| `input_modality` | numeric code (legacy from upstream) |
| `stimulus_material_visual` | What was shown / heard (e.g. *still images*, *VR walkthrough*) |
| `protocol_lab_realworld` | `Lab`, `Real-world`, `Mixed` (free-text label) |
| `lab_realworld_binary` | `1` = Lab, `2` = Real-world, `3` = Mixed |

### EEG hardware

| Column | Description |
| --- | --- |
| `eeg_system_mobile_stationary` | `stat` or `mob` |
| `eeg_system` | Model name |
| `eeg_company` | Manufacturer |
| `sampling_rate_hz` | Hz |
| `filters_amp` | Amplifier filter spec |
| `online_filters` | `0`/`1` |
| `num_channels` | Integer count |
| `electrode_type` | wet/dry/saline |
| `electrode_locations` | 10–20 labels or summary |
| `reference_electrode` | Reference setup |
| `offline_filters` | Description of offline filtering |
| `offline_highpass_hz` | |
| `offline_lowpass_hz` | |
| `channel_interpolation` | `0`/`1` |
| `artifact_rejection` | description |

### Mobility scoring

| Column | Description |
| --- | --- |
| `participant_mobility_label` | full label, e.g. `0 - Lying, sitting, or standing still` |
| `participant_mobility_score` | numeric `0`–`4` |
| `system_mobility_label` | full label |
| `system_mobility_score` | numeric `0`–`4` |

#### Participant mobility rubric

- `0`: Lying, sitting, or standing still
- `1`: Constrained head/torso movement (e.g. seated VR with head turn)
- `2`: Standing with limb movement
- `3`: Walking on a fixed path
- `4`: Free locomotion in real-world environment

#### System mobility rubric

- `0`: Wired desktop amplifier in shielded room
- `1`: Wired amplifier, ambulatory but tethered
- `2`: Wireless amplifier, requires line-of-sight to receiver
- `3`: Fully wireless, recorded to body-worn device
- `4`: Head-mounted and requires smartphone/tablet

### Variables & analysis

| Column | Description |
| --- | --- |
| `eeg_parameter_space` | Frequency bands / ERP components extracted |
| `subj_behave_parameter_space` | Behavioral / questionnaire measures |
| `eeg_features_cat` | numeric category |
| `alpha_para` | `0`/`1`: was alpha analyzed |
| `independent_variable` | What was manipulated |
| `dependent_variable` | What was measured |
| `analyzed_rois_electrodes` | Channels / ROIs |
| `parameter_interpretation` | What the EEG measure was claimed to index |
| `theories_interpretation` | Theoretical framework cited |
| `other_measures` | Non-EEG measures (HRV, GSR, eye-tracking, etc.) |
| `analysis_approach` | Free text |
| `analysis_approach_binary` | `0` = Black box, `1` = transparent |
| `ica_used` | `0`/`1` |

### Replicability & data

| Column | Description |
| --- | --- |
| `replicability_label` | full label, e.g. `3 - not replicable` |
| `replicability_score` | numeric `0`–`3` (lower = more replicable) |
| `data_availability` | `0`/`1`/`2` (none / on request / public) |

#### Replicability rubric

- `0`: Fully replicable: code, data, and detailed methods all available
- `1`: Methods are detailed enough to reproduce, no data/code
- `2`: Some methodological gaps, would require contacting authors
- `3`: Not replicable from the paper alone

### Quotes / record-keeping

| Column | Description |
| --- | --- |
| `added_date` | `YYYY-MM-DD` of original entry |
| `contributor` | Who added it |
| `edited_date` / `edited_by` | Last edit |
| `full_text_status` | Notes about full-text availability |

---

## Manual PR workflow

If you'd rather edit the CSV directly:

```bash
git clone https://github.com/BeMoBIL/EnviroBrainBase.git
cd EnviroBrainBase
git checkout -b add/firstauthor-year
# edit data/papers.csv: append a row, keep column order
git add data/papers.csv
git commit -m "Add: Smith et al. (2024) Title here"
git push origin add/firstauthor-year
# open PR on GitHub
```

CSV editing tips:

- **Encoding:** UTF-8.
- **Quoting:** quote any cell that contains a comma, newline, or double-quote.
  Most editors do this automatically; don't fight them.
- **List-valued cells:** separate items with `;` (semicolon-space). Example:
  `frontal; central; parietal`.
- **Don't add a column.** If you think a column is missing, open an Issue
  first: schema changes need migration of all existing rows.
- **Don't reorder columns.** Keep the column order identical to `papers.csv`'s
  header.

---

## Review checklist (for maintainers)

Before merging a submission PR:

- [ ] DOI resolves and matches the paper.
- [ ] No duplicate (search by DOI and by title in `papers.csv`).
- [ ] Required fields (`authors_short`, `year`, `title`) are present.
- [ ] Numeric fields parse as numbers; categorical fields use the documented codes.
- [ ] Long-form EEG/analysis fields are filled to a reasonable level: if the
  submitter left them blank, fill what you can or label with `NA`.
- [ ] CI green (CSV parses, app loads).
