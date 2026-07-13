import streamlit as st

# Page Config
st.set_page_config(
    page_title="Nifty 100 Financial Intelligence Portal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Explicitly define page routing using paths relative to the entrypoint directory (src/)
pg = st.navigation([
    st.Page("pages/01_home.py", title="🏛️ Executive Overview", default=True),
    st.Page("pages/02_profile.py", title="📊 Company Explorer"),
    st.Page("pages/03_screener.py", title="🔍 Financial Screener"),
    st.Page("pages/04_peers.py", title="👥 Peer Comparison"),
    st.Page("pages/05_trends.py", title="📉 Trend Analysis"),
    st.Page("pages/06_sectors.py", title="🏢 Sector Analysis"),
    st.Page("pages/07_capital.py", title="🌳 Capital Allocation"),
    st.Page("pages/08_reports.py", title="📋 Annual Reports")
])

pg.run()
