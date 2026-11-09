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
    repo  = "BeMoBIL/EnvironBrainBase"
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

DATA_PATH = Path(__file__).parent.parent / "data" / "papers.csv"


st.title("✉️ Submit a paper")
st.caption(
    "Submissions are added by opening a Pull Request against the public repo. "
    "A maintainer reviews and merges; on merge, the live database updates within ~1 minute."
)

# ---------- Secrets / config ----------
gh_cfg = st.secrets.get("github", {}) if hasattr(st, "secrets") else {}
TOKEN = gh_cfg.get("token", "")
REPO = gh_cfg.get("repo", "BeMoBIL/EnvironBrainBase")
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


COLUMNS = load_columns()

EEG_SYSTEM_TO_BRAND = {
    "ANT eegoSport": "ANT Neuro",
    "ANT mylab": "ANT Neuro",
    "B-Alert X10": "Advanced Brain Monitoring",
    "B-Alert X24": "Advanced Brain Monitoring",
    "BEmicro": "EB Neuro",
    "BIO-ST": "BioBrain Inc.",
    "BIOPAC Bionomadix": "BIOPAC",
    "BIOPAC EEG100C": "BIOPAC",
    "BIOPAC MP150": "BIOPAC",
    "BIOPAC MP160": "BIOPAC",
    "Biopac Smart Center": "Biopac",
    "Biosemi ActiveTwo": "Biosemi",
    "BitBrain": "Bitbrain",
    "BitBrain Versatile 32": "Bitbrain",
    "BrainLink Pro": "Macrotellect",
    "BrainProducts Actichamp": "Brain Products",
    "BrainProducts BrainAmp": "Brain Products",
    "BrainProducts LiveAmp": "Brain Products",
    "BrainProducts MOVE": "Brain Products",
    "BrainProducts QuickAmp": "Brain Products",
    "BrainProducts V-Amp": "Brain Products",
    "Cognionics Quick-20": "Cognionics",
    "Cognionics Quick-8": "Cognionics",
    "EEG-1100": "Nihon Kohden",
    "Embla N7000": "Natus",
    "Emotiv EPOC": "Emotiv",
    "Emotiv Epoc Flex": "Emotiv",
    "Emotiv EPOC X": "Emotiv",
    "Emotiv EPOC+": "Emotiv",
    "Emotiv Insight": "Emotiv",
    "Encephalan-EEGR-19": "Medicom MTD",
    "Enobio": "Neuroelectrics",
    "eWave+24": "Science Beam",
    "Flowtime headband": "Enter Technology",
    "G-tec g.HIAMP": "g.tec",
    "G-tec g.Nautilus": "g.tec",
    "G-tec g.USBamp": "g.tec",
    "Ganglion Board": "Open BCI",
    "Geodesic 400": "Electrical Geodesic Inc.",
    "Geodesic Netamp": "Electrical Geodesic Inc./Philips",
    "Kingfar Ergolab": "Kingfar",
    "KT88": "Contec Medical Systems",
    "Looxid Link (HTC Vive AddOn)": "Looxid",
    "MB8600 BoYing BI": "BoYing BI",
    "MBrainTrain Smarting": "MBrainTrain",
    "Micromed EEGraph": "Micromed",
    "MindBand": "",
    "MindCare": "Omnifit",
    "Mindrider": "NeuroSky",
    "Mindset": "NeuroSky",
    "Mindwave": "NeuroSky",
    "Muse": "InteraXon",
    "Muse 2": "InteraXon",
    "Muse S": "InteraXon",
    "Nervus Digital": "Cephalon",
    "Neuro Harmony": "BrainTech",
    "NeuroHub": "Neuracle",
    "neuroNicle FX2": "Laxtha Inc.",
    "Neuroscan": "Neuroscan",
    "Neuroscan NuAmp": "Compumedics Neuroscan",
    "Neuroscan Synamps": "Compumedics Neuroscan",
    "Neurosky Mindwave": "NeuroSky",
    "Neurosky Mindwave 2": "NeuroSky",
    "Nexus-32": "mindmedia",
    "Nexus-4": "mindmedia",
    "Nova ND-97": "Nova Medical Equipment Co., Ltd.",
    "NuoWan ND-97": "Nova Medical Equipment Co., Ltd.",
    "Okti": "Compumedics",
    "OpenBCI": "OpenBCI",
    "PLUX Biosignals": "Plux Biosignals",
    "Polimate AP1000": "TEAC Co. Ltd.",
    "Powerlab": "ADInstruments",
    "ProComp Infinity": "Thought Technology",
    "ProComp+": "Thought Technology",
    "ProComp5": "Thought Technology",
    "Q5000": "Negar Andishgan Company",
    "SAGA": "TMSi",
    "Sichiray Mindband": "Sichiray",
    "Sichiray Taurus": "Sichiray",
    "Sichiray TGAM": "Sichiray",
    "SmartBCI": "Everloyal",
    "SP-Mars II": "Siga Medical",
    "StarStim8": "Neuroelectrics",
    "Synamps2": "Compumedics Neuroscan",
    "Tesla MRI": "Bittium",
    "TGAM": "NeuroSky",
    "Unicorn Hybrid Black": "g.tec",
    "Visheew Infinity 3000": "Nanjing Visheew Medical Technology",
    "Wearable Sensing DSI-24": "Wearable Sensing",
    "Wearable Sensing DSI-7": "Wearable Sensing",
    "Other": "",
}

VENUE_TO_PUBLISHER = {
    "Acta Horticulturae": "ISHS",
    "Acta Medica Int": "Parsvnath Publishing House",
    "Advanced Engineering Informatics": "Elsevier",
    "Advances in Electrical and Electronic Engineering": "VSB–Technical University of Ostrava, Czech Republic",
    "Ain Shams Engineering Journal": "Elsevier",
    "Indoor and Built Environ": "Sage Publishing",
    "Annals of Neurosciences": "Sage Publishing",
    "Ann NY Acad Sci": "Wiley",
    "Annual International Conference of the IEEE Engineering in Medicine and Biology Society": "IEEE",
    "Applied Acoustics": "Elsevier",
    "Applied Ecology Environ Research": "ALÖKI Kft.",
    "Applied Ergonomics": "Elsevier",
    "Applied Mathematics and Nonlinear Sciences": "De Gruyter",
    "Applied Psychophysiology Biofeedback": "Springer Nature",
    "Applied Sciences": "MDPI",
    "Applied Spatial Analysis and Policy": "Springer Nature",
    "Architectural Intelligence": "Springer Nature",
    "Architectural Science Review": "Taylor & Francis",
    "architecture": "MDPI",
    "Architecture and Engineering": "St. Petersburg State University of Architecture and Civil Engineering",
    "Biomedical Signal Processing and Control": "Elsevier",
    "biology": "MDPI",
    "Biomimetics": "MDPI",
    "BMC Research Notes": "Springer Nature",
    "Br J Sports Med": "BMJ Group",
    "Brain and Behavior": "Wiley",
    "Brain and Environment": "Elsevier",
    "Brain Sciences": "MDPI",
    "Build Simul": "Springer Nature",
    "Building and Environment": "Elsevier",
    "Building Research & Information": "Taylor & Francis",
    "Buildings": "MDPI",
    "Cities": "Elsevier",
    "Cities & Health": "Taylor & Francis",
    "Cogn Process": "Springer Nature",
    "Cogn Systems Res": "Elsevier",
    "Cognition and Behavior": "eNeuro",
    "Cogn Res Princ Implic": "Springer Nature",
    "Cognitive Neuroscience": "Taylor & Francis",
    "Color Research & Application": "Wiley",
    "Complementary Therapies in Medicine": "Elsevier",
    "Computer animation & virtual worlds": "Wiley",
    "Computers in Biology and Medicine": "Elsevier",
    "Current issues in tourism": "Taylor & Francis",
    "Current Psychol": "Springer Nature",
    "Dev Built Environ": "Elsevier",
    "Dev Psychol": "APA",
    "DYNA": "Universidad Nacional de Colombia",
    "Ecological Frontiers": "Elsevier",
    "Ecological Indicators": "Elsevier",
    "Energy and Buildings": "Elsevier",
    "Educat Sci": "MDPI",
    "eNeuro": "Society for Neuroscience",
    "Environ Health Insights": "Sage Publishing",
    "Environ Monit Assess": "Springer Nature",
    "Environ Pollution": "Elsevier",
    "Information Technology & Tourism": "Springer Nature",
    "Environ Research": "Elsevier",
    "Environ Research and Public Health": "MDPI",
    "Environment and Behavior": "Sage Publishing",
    "Environment, Development and Sustainability": "Springer Nature",
    "Environ Science": "Hikari Ltd",
    "Environ Impact Ass Rev": "Elsevier",
    "Euro J Forest Res": "Springer Nature",
    "Euro J Hort Sci": "CABI",
    "Euro J Neurosci": "Wiley",
    "Evidence-Based Complement Alternat Medicine": "Wiley",
    "Exp Brain Res": "Springer Nature",
    "Exp Geront": "Elsevier",
    "Infrastructures": "MDPI",
    "EXPLORE": "Elsevier",
    "Forests": "MDPI",
    "Front Architectural Research": "KeAi",
    "Front Behav Neurosci": "Frontiers",
    "Front Built Environ": "Frontiers",
    "Front Forest Global Change": "Frontiers",
    "Int J Built Environ Sustain": "Universiti Teknologi Malaysia / Faculty of Built Environment (UTM / Penerbit UTM)",
    "Front Human Neuroscience": "Frontiers",
    "Front Psychiatry": "Frontiers",
    "Front Psychol": "Frontiers",
    "Front Public Health": "Frontiers",
    "Front Virtual Reality": "Frontiers",
    "Health Environ Res Design J": "Sage Publishing",
    "Int J Architectural Research": "Emerald Publishing Ltd",
    "Healthcare": "MDPI",
    "Heliyon": "Elsevier",
    "HERD: Health Environments Research & Design Journal": "Sage Publishing",
    "Horticulturae": "MDPI",
    "Horticultural Science": "American Society for Horticultural Science",
    "Hortscience": "American Society for Horticultural Science",
    "Human Brain Mapping": "Wiley",
    "Human Soc Sci Comm": "Springer Nature",
    "IEEE Access": "IEEE",
    "Cognitive Neurodynamics": "Springer Nature",
    "Int J Architectural Engineering & Urban Planning": "Iran University of Science & Technology",
    "Int J Com WB": "Springer Nature",
    "Int J Eng Trends and Technologies": "Seventh Sense Research Group",
    "Int J Environ Res Pub Health": "MDPI",
    "Int J Geo-Inf": "MDPI",
    "Int J Geoheritage Parks": "Elsevier",
    "Int J Health Well Soc": "Common Ground Research Networks",
    "Int J Ind Ergon": "Elsevier",
    "Int J Low-Carbon Technologies": "Oxford University Press",
    "Int J Parallel, Emergent and Distributed Systems": "Taylor & Francis",
    "Int J Preventive Medicine": "Lippincott",
    "Int J Psychophysiol": "Elsevier",
    "Int J Technol Design Education": "Springer Nature",
    "Int J Urban Sciences": "Taylor & Francis",
    "Integrated Computer-Aided Engineering": "IOS Press",
    "Intelligent Buildings International": "Taylor & Francis",
    "Iran J Public Health": "School of Public Health Iran",
    "J Architectural and Planning Research": "Locke Science",
    "J Asian Architecture and Building Engineering": "Taylor & Francis",
    "J Audio Eng Soc": "AES",
    "J Building Engineering": "Elsevier",
    "J Cleaner Production": "Elsevier",
    "J Cog Neurosci": "MIT Press",
    "J Cog Psychol": "Taylor & Francis",
    "J Comput Civ Eng": "American Society of Civil Engineers",
    "J Comput Des Eng": "Oxford University Press",
    "J Constr Eng Manag": "ASCE",
    "J Daylighting": "SolarLits",
    "J Dig Landsc Arch": "VDE",
    "J East Asia Society for Transportation Studies": "J-STAGE",
    "J Eng Sci": "Assiut University",
    "J Environ Manage": "Elsevier",
    "J Environ Psychol": "Elsevier",
    "J Environ Sci Int": "Korean Environmental Science Technology",
    "J Forest Res": "Springer Nature",
    "J Korean Institute of Landscape Architecture": "Korean Institute of Landscape Architecture",
    "J Medical Internet Research": "JMIR Publications",
    "J People Plants Environ": "The Society of People, Plants, and Environment",
    "J Physiol Anthropology": "Springer Nature",
    "J Research in Psychopathology": "University of Mohaghegh Ardabili",
    "J Spirituality in Mental Health": "Taylor & Francis",
    "J Urban Design": "Taylor & Francis",
    "J Urban Environ Eng": "University of Paraiba , Brazil",
    "J Urban Health": "Springer Nature",
    "J Urban Technol": "Taylor & Francis",
    "Journal of urban health : bulletin of the New York Academy of Medicine": "New York Academy of Medicine",
    "Land": "MDPI",
    "Land Degradation & Development": "Wiley",
    "Landscape Archit Front": "Higher Education Press",
    "Landscape Research": "Taylor & Francis",
    "Landscape Urban Planning": "Elsevier",
    "Leisure Sciences": "Taylor & Francis",
    "Leukos": "Taylor & Francis",
    "Light & Engineering": "Znack Publishing House",
    "Machine Learning and Knowledge Extraction": "MDPI",
    "Materials Today Advances": "Elsevier",
    "Medical Eng Physics": "IOP",
    "NeuroImage": "Elsevier",
    "Neuroscience": "Elsevier",
    "Noise and Health": "Wolters Kluwer Medknow",
    "Nonlinear Dynamics Psychol Life Sci": "Society for Chaos Theory in Psychology & Life Sciences",
    "npj Heritage Science": "Springer Nature",
    "Open House International": "Emerald Publishing Ltd",
    "PeerJ": "PeerJ",
    "Planning Malaysia": "Malaysian Institute of Planners",
    "PLOS One": "PLOS",
    "Proc International Conference of Contemporary Affairs in Architecture and Urbanism-ICCAUA": "Alanya Üniversitesi",
    "Proc Natl Acad Sci USA": "National Academy of Science USA",
    "Procedia": "Elsevier",
    "PsyCH Journal": "Wiley",
    "Psychology of Aesthetics Creativity and the Arts": "APA",
    "Psychophysiology": "Wiley",
    "Psychosomatic Medicine": "Springer Nature",
    "Scandinavian J Psychol": "Wiley",
    "Science and Technology for the Built Environment": "Taylor & Francis",
    "Scientific Reports": "Springer Nature",
    "Sensors": "MDPI",
    "Service Industries Journal": "Taylor & Francis",
    "She Ji - The Journal of Design Economics and Innovation": "Elsevier",
    "Smart Health": "Elsevier",
    "Social Science Journal": "Taylor & Francis",
    "Space Ontology International Journal": "Qazvin Islamic Azad University",
    "Stress and Health": "Wiley",
    "Sustainability": "MDPI",
    "Sustainable Cities and Society": "Elsevier",
    "The International Archives of the Photogrammetry, Remote Sensing and Spatial Information Sciences": "The International Society of the Photogrammetry, Remote Sensing and Spatial Information Sciences",
    "The Journal of Academic Librarianship": "Elsevier",
    "The Journal of Neuroscience": "SfN",
    "Transactions in GIS": "Wiley",
    "Transp. Res. F: Traffic Psychol. Behav.": "Elsevier",
    "Trees Forests People": "Elsevier",
    "Tunneling and Underground Space Technology": "Elsevier",
    "Urban Climate": "Elsevier",
    "Urban Forestry Urban Green": "Elsevier",
    "Urban Science": "MDPI",
    "Virtual Creativity": "intellect books",
    "Virtual Reality": "Springer Nature",
    "Vision": "MDPI",
    "Visions for Sustainability": "University of Turin",
    "Vitruvio": "Universitat Politècnica de València (UPV)",
    "World Leisure Journal": "Taylor & Francis",
    "Ying yong sheng tai xue bao = The journal of applied ecology publisher": "Science Press",
}
VENUE_OPTIONS = [""] + sorted(VENUE_TO_PUBLISHER, key=str.lower) + ["Other"]


VENUE_TO_DOMAIN = {
    "Acta Horticulturae": "Nature / Landscape / Environment / Ecology",
    "Acta Medica Int": "Neuroscience / Psychology / Medicine",
    "Advanced Engineering Informatics": "Engineering / Technology / Acoustics / Thermal",
    "Advances in Electrical and Electronic Engineering": "Engineering / Technology / Acoustics / Thermal",
    "Ain Shams Engineering Journal": "Engineering / Technology / Acoustics / Thermal",
    "Indoor and Built Environ": "Architecture / Design / Built Environment",
    "Annals of Neurosciences": "Neuroscience / Psychology / Medicine",
    "Ann NY Acad Sci": "Multidisciplinary",
    "Annual International Conference of the IEEE Engineering in Medicine and Biology Society": "Engineering / Technology / Acoustics / Thermal",
    "Applied Acoustics": "Engineering / Technology / Acoustics / Thermal",
    "Applied Ecology Environ Research": "Nature / Landscape / Environment / Ecology",
    "Applied Ergonomics": "Engineering / Technology / Acoustics / Thermal",
    "Applied Mathematics and Nonlinear Sciences": "Engineering / Technology / Acoustics / Thermal",
    "Applied Psychophysiology Biofeedback": "Neuroscience / Psychology / Medicine",
    "Applied Sciences": "Multidisciplinary",
    "Applied Spatial Analysis and Policy": "Engineering / Technology / Acoustics / Thermal",
    "Architectural Intelligence": "Architecture / Design / Built Environment",
    "Architectural Science Review": "Architecture / Design / Built Environment",
    "architecture": "Architecture / Design / Built Environment",
    "Architecture and Engineering": "Architecture / Design / Built Environment",
    "Biomedical Signal Processing and Control": "Neuroscience / Psychology / Medicine",
    "biology": "Neuroscience / Psychology / Medicine",
    "Biomimetics": "Engineering / Technology / Acoustics / Thermal",
    "BMC Research Notes": "Multidisciplinary",
    "Br J Sports Med": "Neuroscience / Psychology / Medicine",
    "Brain and Behavior": "Neuroscience / Psychology / Medicine",
    "Brain and Environment": "Neuroscience / Psychology / Medicine",
    "Brain Sciences": "Neuroscience / Psychology / Medicine",
    "Build Simul": "Engineering / Technology / Acoustics / Thermal",
    "Building and Environment": "Architecture / Design / Built Environment",
    "Building Research & Information": "Architecture / Design / Built Environment",
    "Buildings": "Architecture / Design / Built Environment",
    "Cities": "Architecture / Design / Built Environment",
    "Cities & Health": "Multidisciplinary",
    "Cogn Process": "Neuroscience / Psychology / Medicine",
    "Cogn Systems Res": "Neuroscience / Psychology / Medicine",
    "Cognition and Behavior": "Neuroscience / Psychology / Medicine",
    "Cogn Res Princ Implic": "Neuroscience / Psychology / Medicine",
    "Cognitive Neuroscience": "Neuroscience / Psychology / Medicine",
    "Color Research & Application": "Multidisciplinary",
    "Complementary Therapies in Medicine": "Neuroscience / Psychology / Medicine",
    "Computer animation & virtual worlds": "Engineering / Technology / Acoustics / Thermal",
    "Computers in Biology and Medicine": "Engineering / Technology / Acoustics / Thermal",
    "Current issues in tourism": "Other",
    "Current Psychol": "Neuroscience / Psychology / Medicine",
    "Dev Built Environ": "Architecture / Design / Built Environment",
    "Dev Psychol": "Neuroscience / Psychology / Medicine",
    "DYNA": "Engineering / Technology / Acoustics / Thermal",
    "Ecological Frontiers": "Nature / Landscape / Environment / Ecology",
    "Ecological Indicators": "Nature / Landscape / Environment / Ecology",
    "Energy and Buildings": "Engineering / Technology / Acoustics / Thermal",
    "Educat Sci": "Other",
    "eNeuro": "Neuroscience / Psychology / Medicine",
    "Environ Health Insights": "Neuroscience / Psychology / Medicine",
    "Environ Monit Assess": "Nature / Landscape / Environment / Ecology",
    "Environ Pollution": "Nature / Landscape / Environment / Ecology",
    "Information Technology & Tourism": "Engineering / Technology / Acoustics / Thermal",
    "Environ Research": "Nature / Landscape / Environment / Ecology",
    "Environ Research and Public Health": "Nature / Landscape / Environment / Ecology",
    "Environment and Behavior": "Neuroscience / Psychology / Medicine",
    "Environment, Development and Sustainability": "Nature / Landscape / Environment / Ecology",
    "Environ Science": "Nature / Landscape / Environment / Ecology",
    "Environ Impact Ass Rev": "Nature / Landscape / Environment / Ecology",
    "Euro J Forest Res": "Nature / Landscape / Environment / Ecology",
    "Euro J Hort Sci": "Nature / Landscape / Environment / Ecology",
    "Euro J Neurosci": "Neuroscience / Psychology / Medicine",
    "Evidence-Based Complement Alternat Medicine": "Neuroscience / Psychology / Medicine",
    "Exp Brain Res": "Neuroscience / Psychology / Medicine",
    "Exp Geront": "Neuroscience / Psychology / Medicine",
    "Infrastructures": "Engineering / Technology / Acoustics / Thermal",
    "EXPLORE": "Multidisciplinary",
    "Forests": "Nature / Landscape / Environment / Ecology",
    "Front Architectural Research": "Architecture / Design / Built Environment",
    "Front Behav Neurosci": "Neuroscience / Psychology / Medicine",
    "Front Built Environ": "Architecture / Design / Built Environment",
    "Front Forest Global Change": "Nature / Landscape / Environment / Ecology",
    "Int J Built Environ Sustain": "Architecture / Design / Built Environment",
    "Front Human Neuroscience": "Neuroscience / Psychology / Medicine",
    "Front Psychiatry": "Neuroscience / Psychology / Medicine",
    "Front Psychol": "Neuroscience / Psychology / Medicine",
    "Front Public Health": "Neuroscience / Psychology / Medicine",
    "Front Virtual Reality": "Engineering / Technology / Acoustics / Thermal",
    "Health Environ Res Design J": "Architecture / Design / Built Environment",
    "Int J Architectural Research": "Architecture / Design / Built Environment",
    "Healthcare": "Neuroscience / Psychology / Medicine",
    "Heliyon": "Multidisciplinary",
    "HERD: Health Environments Research & Design Journal": "Architecture / Design / Built Environment",
    "Horticulturae": "Nature / Landscape / Environment / Ecology",
    "Horticultural Science": "Nature / Landscape / Environment / Ecology",
    "Hortscience": "Nature / Landscape / Environment / Ecology",
    "Human Brain Mapping": "Neuroscience / Psychology / Medicine",
    "Human Soc Sci Comm": "Multidisciplinary",
    "IEEE Access": "Engineering / Technology / Acoustics / Thermal",
    "Cognitive Neurodynamics": "Neuroscience / Psychology / Medicine",
    "Int J Architectural Engineering & Urban Planning": "Architecture / Design / Built Environment",
    "Int J Com WB": "Multidisciplinary",
    "Int J Eng Trends and Technologies": "Engineering / Technology / Acoustics / Thermal",
    "Int J Environ Res Pub Health": "Neuroscience / Psychology / Medicine",
    "Int J Geo-Inf": "Engineering / Technology / Acoustics / Thermal",
    "Int J Geoheritage Parks": "Nature / Landscape / Environment / Ecology",
    "Int J Health Well Soc": "Neuroscience / Psychology / Medicine",
    "Int J Ind Ergon": "Engineering / Technology / Acoustics / Thermal",
    "Int J Low-Carbon Technologies": "Engineering / Technology / Acoustics / Thermal",
    "Int J Parallel, Emergent and Distributed Systems": "Engineering / Technology / Acoustics / Thermal",
    "Int J Preventive Medicine": "Neuroscience / Psychology / Medicine",
    "Int J Psychophysiol": "Neuroscience / Psychology / Medicine",
    "Int J Technol Design Education": "Architecture / Design / Built Environment",
    "Int J Urban Sciences": "Architecture / Design / Built Environment",
    "Integrated Computer-Aided Engineering": "Engineering / Technology / Acoustics / Thermal",
    "Intelligent Buildings International": "Architecture / Design / Built Environment",
    "Iran J Public Health": "Neuroscience / Psychology / Medicine",
    "J Architectural and Planning Research": "Architecture / Design / Built Environment",
    "J Asian Architecture and Building Engineering": "Architecture / Design / Built Environment",
    "J Audio Eng Soc": "Engineering / Technology / Acoustics / Thermal",
    "J Building Engineering": "Engineering / Technology / Acoustics / Thermal",
    "J Cleaner Production": "Engineering / Technology / Acoustics / Thermal",
    "J Cog Neurosci": "Neuroscience / Psychology / Medicine",
    "J Cog Psychol": "Neuroscience / Psychology / Medicine",
    "J Comput Civ Eng": "Engineering / Technology / Acoustics / Thermal",
    "J Comput Des Eng": "Engineering / Technology / Acoustics / Thermal",
    "J Constr Eng Manag": "Engineering / Technology / Acoustics / Thermal",
    "J Daylighting": "Engineering / Technology / Acoustics / Thermal",
    "J Dig Landsc Arch": "Engineering / Technology / Acoustics / Thermal",
    "J East Asia Society for Transportation Studies": "Engineering / Technology / Acoustics / Thermal",
    "J Eng Sci": "Engineering / Technology / Acoustics / Thermal",
    "J Environ Manage": "Nature / Landscape / Environment / Ecology",
    "J Environ Psychol": "Neuroscience / Psychology / Medicine",
    "J Environ Sci Int": "Nature / Landscape / Environment / Ecology",
    "J Forest Res": "Nature / Landscape / Environment / Ecology",
    "J Korean Institute of Landscape Architecture": "Architecture / Design / Built Environment",
    "J Medical Internet Research": "Neuroscience / Psychology / Medicine",
    "J People Plants Environ": "Nature / Landscape / Environment / Ecology",
    "J Physiol Anthropology": "Neuroscience / Psychology / Medicine",
    "J Research in Psychopathology": "Neuroscience / Psychology / Medicine",
    "J Spirituality in Mental Health": "Other",
    "J Urban Design": "Architecture / Design / Built Environment",
    "J Urban Environ Eng": "Engineering / Technology / Acoustics / Thermal",
    "J Urban Health": "Neuroscience / Psychology / Medicine",
    "J Urban Technol": "Engineering / Technology / Acoustics / Thermal",
    "Journal of urban health : bulletin of the New York Academy of Medicine": "Neuroscience / Psychology / Medicine",
    "Land": "Nature / Landscape / Environment / Ecology",
    "Land Degradation & Development": "Nature / Landscape / Environment / Ecology",
    "Landscape Archit Front": "Architecture / Design / Built Environment",
    "Landscape Research": "Nature / Landscape / Environment / Ecology",
    "Landscape Urban Planning": "Architecture / Design / Built Environment",
    "Leisure Sciences": "Multidisciplinary",
    "Leukos": "Engineering / Technology / Acoustics / Thermal",
    "Light & Engineering": "Engineering / Technology / Acoustics / Thermal",
    "Machine Learning and Knowledge Extraction": "Engineering / Technology / Acoustics / Thermal",
    "Materials Today Advances": "Engineering / Technology / Acoustics / Thermal",
    "Medical Eng Physics": "Engineering / Technology / Acoustics / Thermal",
    "NeuroImage": "Neuroscience / Psychology / Medicine",
    "Neuroscience": "Neuroscience / Psychology / Medicine",
    "Noise and Health": "Neuroscience / Psychology / Medicine",
    "Nonlinear Dynamics Psychol Life Sci": "Neuroscience / Psychology / Medicine",
    "npj Heritage Science": "Other",
    "Open House International": "Architecture / Design / Built Environment",
    "PeerJ": "Multidisciplinary",
    "Planning Malaysia": "Architecture / Design / Built Environment",
    "PLOS One": "Multidisciplinary",
    "Proc International Conference of Contemporary Affairs in Architecture and Urbanism-ICCAUA": "Architecture / Design / Built Environment",
    "Proc Natl Acad Sci USA": "Multidisciplinary",
    "Procedia": "Multidisciplinary",
    "PsyCH Journal": "Neuroscience / Psychology / Medicine",
    "Psychology of Aesthetics Creativity and the Arts": "Neuroscience / Psychology / Medicine",
    "Psychophysiology": "Neuroscience / Psychology / Medicine",
    "Psychosomatic Medicine": "Neuroscience / Psychology / Medicine",
    "Scandinavian J Psychol": "Neuroscience / Psychology / Medicine",
    "Science and Technology for the Built Environment": "Engineering / Technology / Acoustics / Thermal",
    "Scientific Reports": "Multidisciplinary",
    "Sensors": "Engineering / Technology / Acoustics / Thermal",
    "Service Industries Journal": "Other",
    "She Ji - The Journal of Design Economics and Innovation": "Architecture / Design / Built Environment",
    "Smart Health": "Engineering / Technology / Acoustics / Thermal",
    "Social Science Journal": "Multidisciplinary",
    "Space Ontology International Journal": "Architecture / Design / Built Environment",
    "Stress and Health": "Neuroscience / Psychology / Medicine",
    "Sustainability": "Multidisciplinary",
    "Sustainable Cities and Society": "Architecture / Design / Built Environment",
    "The International Archives of the Photogrammetry, Remote Sensing and Spatial Information Sciences": "Engineering / Technology / Acoustics / Thermal",
    "The Journal of Academic Librarianship": "Other",
    "The Journal of Neuroscience": "Neuroscience / Psychology / Medicine",
    "Transactions in GIS": "Engineering / Technology / Acoustics / Thermal",
    "Transp. Res. F: Traffic Psychol. Behav.": "Neuroscience / Psychology / Medicine",
    "Trees Forests People": "Nature / Landscape / Environment / Ecology",
    "Tunneling and Underground Space Technology": "Engineering / Technology / Acoustics / Thermal",
    "Urban Climate": "Nature / Landscape / Environment / Ecology",
    "Urban Forestry Urban Green": "Nature / Landscape / Environment / Ecology",
    "Urban Science": "Architecture / Design / Built Environment",
    "Virtual Creativity": "Architecture / Design / Built Environment",
    "Virtual Reality": "Architecture / Design / Built Environment",
    "Vision": "Neuroscience / Psychology / Medicine",
    "Visions for Sustainability": "Engineering / Technology / Acoustics / Thermal",
    "Vitruvio": "Architecture / Design / Built Environment",
    "World Leisure Journal": "Multidisciplinary",
    "Ying yong sheng tai xue bao = The journal of applied ecology publisher": "Nature / Landscape / Environment / Ecology",
}


# ---------- Form ----------
st.markdown(
    "Required fields are marked. Anything you don't know, leave blank: a "
    "maintainer can fill it during review."
)

with st.form("submit_form", clear_on_submit=False):
    st.subheader("Citation")
    c1, c2, c3 = st.columns(3)
    authors_short = c1.text_input(
        "Authors (short, e.g. *Smith et al.*)", help="Required"
    )
    year = c2.text_input("Year", help="Required")
    country = c3.selectbox(
        "First author's country of primary affiliation",
        options=[
            "",
            "Afghanistan",
            "Albania",
            "Algeria",
            "Andorra",
            "Angola",
            "Antigua and Barbuda",
            "Argentina",
            "Armenia",
            "Australia",
            "Austria",
            "Azerbaijan",
            "Bahamas",
            "Bahrain",
            "Bangladesh",
            "Barbados",
            "Belarus",
            "Belgium",
            "Belize",
            "Benin",
            "Bhutan",
            "Bolivia",
            "Bosnia and Herzegovina",
            "Botswana",
            "Brazil",
            "Brunei",
            "Bulgaria",
            "Burkina Faso",
            "Burundi",
            "Cambodia",
            "Cameroon",
            "Canada",
            "Cape Verde",
            "Central African Republic",
            "Chad",
            "Chile",
            "China",
            "Colombia",
            "Comoros",
            "Congo (Brazzaville)",
            "Congo (Kinshasa)",
            "Costa Rica",
            "Croatia",
            "Cuba",
            "Cyprus",
            "Czech Republic",
            "Denmark",
            "Djibouti",
            "Dominica",
            "Dominican Republic",
            "Ecuador",
            "Egypt",
            "El Salvador",
            "Equatorial Guinea",
            "Eritrea",
            "Estonia",
            "Eswatini",
            "Ethiopia",
            "Fiji",
            "Finland",
            "France",
            "Gabon",
            "Gambia",
            "Georgia",
            "Germany",
            "Ghana",
            "Greece",
            "Grenada",
            "Guatemala",
            "Guinea",
            "Guinea-Bissau",
            "Guyana",
            "Haiti",
            "Honduras",
            "Hong Kong",
            "Hungary",
            "Iceland",
            "India",
            "Indonesia",
            "Iran",
            "Iraq",
            "Ireland",
            "Israel",
            "Italy",
            "Ivory Coast",
            "Jamaica",
            "Japan",
            "Jordan",
            "Kazakhstan",
            "Kenya",
            "Kiribati",
            "Kosovo",
            "Kuwait",
            "Kyrgyzstan",
            "Laos",
            "Latvia",
            "Lebanon",
            "Lesotho",
            "Liberia",
            "Libya",
            "Liechtenstein",
            "Lithuania",
            "Luxembourg",
            "Macau",
            "Madagascar",
            "Malawi",
            "Malaysia",
            "Maldives",
            "Mali",
            "Malta",
            "Marshall Islands",
            "Mauritania",
            "Mauritius",
            "Mexico",
            "Micronesia",
            "Moldova",
            "Monaco",
            "Mongolia",
            "Montenegro",
            "Morocco",
            "Mozambique",
            "Myanmar",
            "Namibia",
            "Nauru",
            "Nepal",
            "Netherlands",
            "New Zealand",
            "Nicaragua",
            "Niger",
            "Nigeria",
            "North Korea",
            "North Macedonia",
            "Norway",
            "Oman",
            "Pakistan",
            "Palau",
            "Palestine",
            "Panama",
            "Papua New Guinea",
            "Paraguay",
            "Peru",
            "Philippines",
            "Poland",
            "Portugal",
            "Puerto Rico",
            "Qatar",
            "Romania",
            "Russia",
            "Rwanda",
            "Saint Kitts and Nevis",
            "Saint Lucia",
            "Saint Vincent and the Grenadines",
            "Samoa",
            "San Marino",
            "Sao Tome and Principe",
            "Saudi Arabia",
            "Senegal",
            "Serbia",
            "Seychelles",
            "Sierra Leone",
            "Singapore",
            "Slovakia",
            "Slovenia",
            "Solomon Islands",
            "Somalia",
            "South Africa",
            "South Korea",
            "South Sudan",
            "Spain",
            "Sri Lanka",
            "Sudan",
            "Suriname",
            "Sweden",
            "Switzerland",
            "Syria",
            "Taiwan",
            "Tajikistan",
            "Tanzania",
            "Thailand",
            "Timor-Leste",
            "Togo",
            "Tonga",
            "Trinidad and Tobago",
            "Tunisia",
            "Turkey",
            "Turkmenistan",
            "Tuvalu",
            "UK",
            "USA",
            "Uganda",
            "Ukraine",
            "United Arab Emirates",
            "Uruguay",
            "Uzbekistan",
            "Vanuatu",
            "Vatican City",
            "Venezuela",
            "Vietnam",
            "Yemen",
            "Zambia",
            "Zimbabwe",
            "Other",
        ],
        format_func=lambda v: {"": "—"}.get(v, v),
    )
    c1, c2 = st.columns(2)
    title = c1.text_input("Title", help="Required")
    venue = c2.selectbox("Journal / venue (Abbreviation; e.g. *J Env Psychol*)", options=VENUE_OPTIONS, help="Required")
    authors_full = st.text_area(
        "Full author list (with first names; e.g., *John Doe, Jane Smith*)", height=80
    )
    doi_link = st.text_input("DOI or link", help="Required if available")
    c1, c2 = st.columns(2)
    data_availability = c1.selectbox(
        "Data availability",
        options=["","NA", "2", "1", "0"],
        format_func=lambda v: {
            "": "—",
            "NA": "No statement",
            "2": "Openly available in repositories",
            "1": "Available upon request",
            "0": "Data not made available",
        }.get(v, v),
    )
    preregistration = c2.selectbox(
        "Was the study preregistered?",
        options=["", "Yes", "No"],
        format_func=lambda v: {"": "—"}.get(v, v),
    )

    st.subheader("Sample & setting")
    c1, c2, c3 = st.columns(3)
    sample_category = c1.selectbox(
        "Study Topic",
        options=["", "1", "2", "3", "1, 2", "2, 3", "1, 3", "1, 2, 3"],
        format_func=lambda v: {
            "": "—",
            "1": "Architecture",
            "2": "Urbanism",
            "3": "Nature",
            "1, 2": "Architecture+Urbanism",
            "2, 3": "Urbanism+Nature",
            "1, 3": "Architecture+Nature",
            "1, 2, 3": "All three",
        }.get(v, v),
    )
    lab_realworld_binary = c2.selectbox(
        "Lab / real-world",
        options=["", "1", "2", "3"],
        format_func=lambda v: {
            "": "—",
            "1": "Lab",
            "2": "Real-world",
            "3": "Mixed",
        }.get(v, v),
    )
    eeg_system_mobile_stationary = c3.selectbox(
        "How is the EEG system used?",
        options=["", "stat", "mob", "mix"],
        format_func=lambda v: {
            "": "—",
            "stat": "Stationary",
            "mob": "Mobile",
            "mix": "Mix (both stationary and mobile use)",
        }.get(v, v),
    )

    c1, c2, c3, c4 = st.columns(4)
    num_participants = c1.text_input("N participants")
    age_range = c2.text_input("Age range (e.g. 18–35)")
    mean_age_participants = c3.text_input("Mean age (e.g. 24.5)")
    sex_perc_male = c4.text_input("% male (e.g. 27%)")

    st.subheader("EEG setup")
    eeg_system = st.selectbox(
        "EEG system / model",
        options=[
            "",
            "ANT eegoSport",
            "ANT mylab",
            "B-Alert X10",
            "B-Alert X24",
            "BEmicro",
            "BIO-ST",
            "BIOPAC Bionomadix",
            "BIOPAC EEG100C",
            "BIOPAC MP150",
            "BIOPAC MP160",
            "Biopac Smart Center",
            "Biosemi ActiveTwo",
            "BitBrain",
            "BitBrain Versatile 32",
            "BrainLink Pro",
            "BrainProducts Actichamp",
            "BrainProducts BrainAmp",
            "BrainProducts LiveAmp",
            "BrainProducts MOVE",
            "BrainProducts QuickAmp",
            "BrainProducts V-Amp",
            "Cognionics Quick-20",
            "Cognionics Quick-8",
            "EEG-1100",
            "Embla N7000",
            "Emotiv EPOC",
            "Emotiv Epoc Flex",
            "Emotiv EPOC X",
            "Emotiv EPOC+",
            "Emotiv Insight",
            "Encephalan-EEGR-19",
            "Enobio",
            "eWave+24",
            "Flowtime headband",
            "G-tec g.HIAMP",
            "G-tec g.Nautilus",
            "G-tec g.USBamp",
            "Ganglion Board",
            "Geodesic 400",
            "Geodesic Netamp",
            "Kingfar Ergolab",
            "KT88",
            "Looxid Link (HTC Vive AddOn)",
            "MB8600 BoYing BI",
            "MBrainTrain Smarting",
            "Micromed EEGraph",
            "MindBand",
            "MindCare",
            "Mindrider",
            "Mindset",
            "Mindwave",
            "Muse",
            "Muse 2",
            "Muse S",
            "Nervus Digital",
            "Neuro Harmony",
            "NeuroHub",
            "neuroNicle FX2",
            "Neuroscan",
            "Neuroscan NuAmp",
            "Neuroscan Synamps",
            "Neurosky Mindwave",
            "Neurosky Mindwave 2",
            "Nexus-32",
            "Nexus-4",
            "Nova ND-97",
            "NuoWan ND-97",
            "Okti",
            "OpenBCI",
            "PLUX Biosignals",
            "Polimate AP1000",
            "Powerlab",
            "ProComp Infinity",
            "ProComp+",
            "ProComp5",
            "Q5000",
            "SAGA",
            "Sichiray Mindband",
            "Sichiray Taurus",
            "Sichiray TGAM",
            "SmartBCI",
            "SP-Mars II",
            "StarStim8",
            "Synamps2",
            "Tesla MRI",
            "TGAM",
            "Unicorn Hybrid Black",
            "Visheew Infinity 3000",
            "Wearable Sensing DSI-24",
            "Wearable Sensing DSI-7",
            "Other",
        ],
    )

    c1, c2, c3, c4 = st.columns(4)
    num_channels = c1.text_input("Channels")
    sampling_rate_hz = c2.text_input("Sampling rate (Hz)")
    reference_electrode = c3.text_input("Reference")
    electrode_type = c4.selectbox(
        "Kind of electrodes",
        options=["", "wet electrodes", "dry electrodes", "semi-dry"],
        format_func=lambda v: {"": "—"}.get(v, v),
    )
    c1, c2 = st.columns(2)
    electrode_locations = c1.selectbox(
        "Electrode locations reported? (y/n)",
        options=["", "yes", "no"],
        format_func=lambda v: {"": "—"}.get(v, v),
    )
    online_filters = c2.selectbox(
        "Amplifier filter settings reported? (y/n)",
        options=["", "yes", "no"],
        format_func=lambda v: {"": "—"}.get(v, v),
    )

    st.subheader("Stimulus / paradigm")
    input_modality_cat = st.selectbox(
        "Stimilus Input modality",
        options=[
            "",
            "visual",
            "auditory",
            "olfactory",
            "real world all modalities",
            "tactile",
            "air quality",
            "visual + auditory",
            "visual + olfactory",
            "auditory + olfactory",
            "visual + auditory + olfactory",
            "other",
        ],
        format_func=lambda v: {"": "—"}.get(v, v),
    )
    stimulus_material_visual = st.selectbox(
        "Stimulus material",
        options=[
            "",
            "still images",
            "still images (HMD)",
            "video (monitor)",
            "virtual reality (monitor)",
            "virtual reality (cave)",
            "virtual reality (HMD)",
            "video immersive (HMD)",
            "audio recordings",
            "smells",
            "real world",
            "temperature",
            "lighting",
        ],
        format_func=lambda v: {"": "—", "still images": "Still images (desktop)"}.get(
            v, v
        ),
    )
    independent_variable = st.text_area("Independent variable(s)", height=70)
    dependent_variable = st.text_area("Dependent variable(s)", height=70)
    c1, c2 = st.columns(2)
    eeg_parameters = c1.selectbox(
        "Analyzed EEG parameters",
        options=["", "frequency domain", "time domain", "proprietary outputs"],
        format_func=lambda v: {"": "—"}.get(v, v),
    )
    other_measures = c2.selectbox(
        "Other collected physiological modalities",
        options=[
            "",
            "Bioimpedance",
            "Blood Glucose",
            "Blood Oxygenation",
            "Blood Pressure",
            "breathing",
            "BVP",
            "Cortisol",
            "Cytokenes",
            "ECG",
            "EDA",
            "EMG",
            "EOG",
            "eye tracking",
            "Eyetracking",
            "fNIRS",
            "Gait",
            "Genetics",
            "GPS",
            "mocap",
            "Performance",
            "PPG",
            "Posture",
            "Pupillometry",
            "resp",
            "Skin Temperature",
            "Wet markers",
            "Other",
        ],
        format_func=lambda v: {"": "—", "resp": "Respiration"}.get(v, v),
    )

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
        "country": form["country"],
        "journal": form["venue"],
        "publisher": form["publisher"],
        "authors_full": form["authors_full"],
        "title": form["title"],
        "data_availability": form["data_availability"],
        "preregistration": form["preregistration"],
        "sample_category": form["sample_category"],
        "num_participants": form["num_participants"],
        "electrode_locations": form["electrode_locations"],
        "online_filters": form["online_filters"],
        "age_range": form["age_range"],
        "mean_age_participants": form["mean_age_participants"],
        "sex_perc_male": form["sex_perc_male"],
        "input_modality_cat": form["input_modality_cat"],
        "stimulus_material_visual": form["stimulus_material_visual"],
        "eeg_parameters": form["eeg_parameters"],
        "other_measures": form["other_measures"],
        "eeg_system_mobile_stationary": form["eeg_system_mobile_stationary"],
        "lab_realworld_binary": form["lab_realworld_binary"],
        "eeg_system": form["eeg_system"],
        "eeg_company": form["eeg_company"],
        "sampling_rate_hz": form["sampling_rate_hz"],
        "num_channels": form["num_channels"],
        "reference_electrode": form["reference_electrode"],
        "electrode_type": form["electrode_type"],
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
    if eeg_system in EEG_SYSTEM_TO_BRAND:
        eeg_company = EEG_SYSTEM_TO_BRAND[eeg_system]
    if venue in VENUE_TO_PUBLISHER:
        publisher = VENUE_TO_PUBLISHER[venue]
        venue_domain = VENUE_TO_DOMAIN[venue]
    form = {
        "authors_short": authors_short,
        "year": year,
        "title": title,
        "country": country,
        "journal": venue,
        "data_availability": data_availability,
        "preregistration": preregistration,
        "publisher": publisher,
        "venue_domain": venue_domain,
        "authors_full": authors_full,
        "doi_link": doi_link,
        "sample_category": sample_category,
        "lab_realworld_binary": lab_realworld_binary,
        "eeg_system_mobile_stationary": eeg_system_mobile_stationary,
        "num_participants": num_participants,
        "age_range": age_range,
        "mean_age_participants": mean_age_participants,
        "sex_perc_male": sex_perc_male,
        "eeg_system": eeg_system,
        "eeg_company": eeg_company,
        "num_channels": num_channels,
        "sampling_rate_hz": sampling_rate_hz,
        "reference_electrode": reference_electrode,
        "electrode_type": electrode_type,
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
