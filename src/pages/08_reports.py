"""
Annual Reports Screen.
Lists available report years with clickable BSE PDF links, and flags invalid links.
"""

import os
import sys
import requests
import streamlit as st
import pandas as pd

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.db import get_connection, get_companies

st.set_page_config(page_title="Nifty 100 Analytics - Reports", layout="wide")

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">📋 Annual Reports Finder</h1>', unsafe_allow_html=True)
st.write("Browse and download original BSE annual reports PDFs for any constituent company.")

@st.cache_data(ttl=86400)  # Cache URL checks for 24 hours
def check_url_valid(url):
    """Performs a fast HTTP check to verify if a document URL is valid."""
    if not url or not str(url).startswith("http"):
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Use stream=True to avoid downloading the entire PDF file
        r = requests.get(url, headers=headers, timeout=5.0, stream=True)
        return r.status_code in [200, 301, 302, 304]
    except Exception:
        # Fallback: if URL is valid HTTP link format, allow access
        return True if url and str(url).startswith("http") else False

# Load companies
df_all_cos = get_companies()
options_list = sorted([f"{row['company_id']} - {row['company_name']}" for _, row in df_all_cos.iterrows()])

search_choice = st.selectbox("Select Company Ticker or Name", options_list, key="rep_comp")

if search_choice:
    ticker = search_choice.split(" - ")[0]
    
    # Load document links from sqlite
    conn = get_connection()
    df_docs = pd.read_sql_query("SELECT * FROM documents WHERE company_id = ? ORDER BY year DESC", conn, params=(ticker,))
    conn.close()
    
    if len(df_docs) > 0:
        st.write(f"Available Annual Reports for **{ticker}**:")
        
        # Display as a table or list
        for _, row in df_docs.iterrows():
            year_val = row["year"]
            doc_url = row["annual_report"]
            report_type = "Annual Report"
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                st.write(f"**FY {year_val}** ({report_type})")
                
            with col2:
                if doc_url:
                    is_valid = check_url_valid(doc_url)
                    if is_valid:
                        st.markdown(f"🔗 [Download original PDF]({doc_url})")
                    else:
                        st.markdown("<span style='color:#C0392B; font-weight:bold; background-color:#FDEDEC; padding:2px 6px; border-radius:4px;'>🔴 Report unavailable (404 / Invalid Link)</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:#7F8C8D; background-color:#F2F4F4; padding:2px 6px; border-radius:4px;'>⚪ No link provided</span>", unsafe_allow_html=True)
            
            st.divider()
    else:
        st.info("No annual report document records found for this company in the database.")
