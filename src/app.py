import streamlit as st

# Page Config
st.set_page_config(
    page_title="Nifty 100 Financial Intelligence Portal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Explicitly define page routing using paths relative to the repository root
pg = st.navigation([
    st.Page("src/pages/01_home.py", title="🏛️ Executive Overview", default=True),
    st.Page("src/pages/02_profile.py", title="📊 Company Explorer"),
    st.Page("src/pages/03_screener.py", title="🔍 Financial Screener"),
    st.Page("src/pages/04_peers.py", title="👥 Peer Comparison"),
    st.Page("src/pages/05_trends.py", title="📉 Trend Analysis"),
    st.Page("src/pages/06_sectors.py", title="🏢 Sector Analysis"),
    st.Page("src/pages/07_capital.py", title="🌳 Capital Allocation"),
    st.Page("src/pages/08_reports.py", title="📋 Annual Reports")
])

pg.run()
