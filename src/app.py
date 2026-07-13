"""
Nifty 100 Financial Intelligence Portal Entry Point.
Redirects to the Home screen (01_home.py) in the pages directory.
"""

import streamlit as st

# Page Config
st.set_page_config(
    page_title="Nifty 100 Financial Intelligence Portal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Redirect to home page
st.switch_page("pages/01_home.py")
