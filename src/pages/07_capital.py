"""
Capital Allocation Map Screen.
Implements a Plotly treemap to visualize Nifty 100 constituents grouped by their 8 capital allocation patterns.
"""

import os
import sys
import streamlit as st
import plotly.express as px
import pandas as pd

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

st.set_page_config(page_title="Nifty 100 Analytics - Capital Map", layout="wide")

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">🌳 Capital Allocation Treemap</h1>', unsafe_allow_html=True)
st.write("Visualizing Nifty 100 companies grouped by their core capital allocation profiles (FY 2024).")

# Connect to database and load latest allocation labels
conn = get_connection()
query = (
    "SELECT ca.company_id, c.company_name, s.broad_sector as sector, ca.pattern_label "
    "FROM capital_allocation ca "
    "JOIN companies c ON ca.company_id = c.id "
    "LEFT JOIN sectors s ON ca.company_id = s.company_id "
    "WHERE ca.year = '2024-03'"
)
df_ca = pd.read_sql_query(query, conn)
conn.close()

if len(df_ca) > 0:
    # Add a constant value for sizing cells equally
    df_ca["value"] = 1
    
    # Render Treemap
    fig = px.treemap(
        df_ca,
        path=["pattern_label", "company_id"],
        values="value",
        color="pattern_label",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hover_name="company_name"
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=450)
    st.plotly_chart(fig, use_container_width=True)
    
    # Interactive filtering below treemap
    st.write("")
    st.subheader("Filter Constituents by Pattern")
    selected_pattern = st.selectbox("Choose Capital Allocation Pattern", sorted(df_ca["pattern_label"].unique()))
    
    df_filtered = df_ca[df_ca["pattern_label"] == selected_pattern][["company_id", "company_name", "sector"]].rename(columns={
        "company_id": "Ticker",
        "company_name": "Company Name",
        "sector": "Sector"
    })
    
    st.write(f"📁 Showing **{len(df_filtered)}** companies classified under **{selected_pattern}**:")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
else:
    st.warning("No capital allocation records found in the database.")
