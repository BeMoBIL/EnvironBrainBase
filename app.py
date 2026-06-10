"""
NeuroUrbanism-DB: navigation router.

Streamlit Community Cloud entrypoint. All page content lives in ./pages/.
Using st.navigation() (Streamlit >= 1.36) for full control over labels and grouping.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="NeuroUrbanism-DB",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation(
    {
        "About": [
            st.Page("pages/0_About.py", title="About", icon="🧠", default=True),
            st.Page("pages/contributors.py", title="Contributors", icon="👥"),
        ],
        "Data": [
            st.Page("pages/1_Database.py", title="Database", icon="📚"),
            st.Page("pages/4_EEG_Systems.py", title="EEG Systems", icon="🔬"),
        ],
        "Contribute": [
            st.Page("pages/2_Submit_a_paper.py", title="Submit a paper", icon="📝"),
        ],
        "Info": [
            st.Page("pages/3_Legal.py", title="Legal", icon="⚖️"),
        ],
    }
)

pg.run()
