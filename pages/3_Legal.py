"""
EnviroBrainBase: Legal / licensing / privacy page.
"""

from __future__ import annotations

import streamlit as st


st.title("⚖️ Legal")

st.markdown("## Licensing")
st.markdown(
    "EnviroBrainBase has a split licence so that the *code* is freely reusable "
    "while the curated *data* is reusable with attribution:"
)
st.markdown(
    "- **Code**: every Python file in the repository, the configuration files, "
    "and the documentation are released under the **MIT Licence**. You can fork, "
    "modify, and redeploy without restriction; please retain the copyright notice.\n"
    "- **Data**: everything in `data/` (the `papers.csv` catalogue and ancillary "
    "files) is released under **Creative Commons Attribution 4.0 International "
    "(CC-BY-4.0)**. You may copy, redistribute, transform, and build upon the "
    "material for any purpose, including commercially, provided that you give "
    "appropriate credit. Recommended attribution: cite the Zenodo DOI of the "
    "specific release you used (see the **Welcome** page)."
)
st.markdown(
    "Individual study-level facts (a paper's title, year, EEG channel count, etc.) "
    "are not themselves copyrightable, but the curation (column scheme, scoring "
    "rubrics, harmonization, and the act of selecting what belongs) represents "
    "creative editorial work. The CC-BY-4.0 licence makes the boundary clear."
)

st.divider()

st.markdown("## Disclaimer")
st.markdown(
    "EnviroBrainBase is a research aid, not an authoritative source. The "
    "categorical codings, scoring rubrics, and replicability assessments "
    "reflect the editors' interpretations of each paper and may contain errors "
    "or judgement calls you would make differently. Always go back to the "
    "primary source before drawing conclusions, and feel free to open a GitHub "
    "Issue if you spot something that should be corrected."
)
st.markdown(
    "Inclusion of a study in this database does not constitute endorsement of "
    "its methodology, claims, or conclusions. The database deliberately "
    "includes papers that the editors have flagged as methodologically weak "
    "(see the `replicability_score` and `analysis_approach_binary` columns) "
    "so that secondary analyses can quantify the state of the field rather "
    "than launder it."
)

st.divider()

st.markdown("## Privacy")
st.markdown(
    "This site does not set tracking cookies and does not embed third-party "
    "analytics. Streamlit Community Cloud, which hosts the app, may keep "
    "operational request logs (timestamps, IP, basic browser metadata) for "
    "infrastructure-level abuse prevention; these are governed by "
    "[Streamlit's privacy policy](https://streamlit.io/privacy-policy)."
)
st.markdown(
    "When you submit a paper through the form, the fields you fill in are "
    "committed to the public GitHub repository as part of a Pull Request "
    "(authored as the project's deploy account). The submitter name and email "
    "you provide appear in the PR description and will be visible to anyone "
    "who can read the repository. If you need to retract a submission before "
    "it is merged, contact a maintainer via the "
    "[GitHub issue tracker](https://github.com/Randomidous/EnviroBrainBase/issues)."
)

st.divider()

st.markdown("## Contact & corrections")
st.markdown(
    "- **Bug or correction:** open an Issue at "
    "[github.com/Randomidous/EnviroBrainBase/issues](https://github.com/Randomidous/EnviroBrainBase/issues).\n"
    "- **Submit a paper:** use the **Submit a paper** page in the sidebar.\n"
    "- **Maintainer contact:** see the GitHub repository description.\n"
)

st.caption(
    "This page is informational. It is not legal advice. If your jurisdiction "
    "or institution imposes additional requirements on data reuse, those take "
    "precedence over the licences above."
)
