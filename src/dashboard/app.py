"""
Main Entry Point for Nifty 100 Analytics Dashboard.
Redirects to the Home screen (01_home.py) in the pages directory.
"""

import streamlit as st

# Set page config
st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Redirect to home page
st.switch_page("pages/01_home.py")
