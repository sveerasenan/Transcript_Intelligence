"""
Aegis Transcript Intelligence - Main Application
================================================

A Streamlit application for analyzing meeting transcripts, providing insights on:
- Meeting categorization and filtering
- Organization-level sentiment analysis
- Churn risk assessment
- Renewal tracking

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add utils to path for imports
sys.path.append(str(Path(__file__).parent))

from utils.data_loader import load_all_meetings
from utils.rule_based_categorizer import RuleBasedCategorizer
from utils.organization_analyzer import OrganizationAnalyzer
from utils.css_loader import load_css, apply_custom_styles


# Page configuration
st.set_page_config(
    page_title="Aegis Transcript Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(show_spinner=False)
def load_and_process_data():
    """
    Load and process all meeting data. Results are cached for performance.
    
    This function:
    1. Loads all meetings from the dataset directory
    2. Applies rule-based categorization
    3. Caches results to avoid reprocessing
    
    Returns:
        pd.DataFrame: Processed meetings with categories assigned
    """
    # Load raw meeting data
    dataset_path = "dataset"
    df = load_all_meetings(dataset_path)
    
    # Apply categorization
    categorizer = RuleBasedCategorizer()
    df = categorizer.categorize_dataframe(df)
    
    return df


# Main application
def main():
    """
    Main application entry point.
    
    Loads data and initializes the application, then redirects to Home page.
    """
    
    # Load data with spinner (only if not already loaded)
    if 'meetings_df' not in st.session_state:
        with st.spinner('🔄 Loading and processing meeting data...'):
            try:
                df = load_and_process_data()
                
                # Store in session state for access by pages
                st.session_state['meetings_df'] = df
                
            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")
                st.info("💡 Please ensure the 'dataset' folder exists and contains meeting data.")
                st.stop()
    
    df = st.session_state['meetings_df']
    
    # Sidebar - Summary Statistics
    st.sidebar.markdown("## 📊 Dataset Summary")
    st.sidebar.markdown("---")
    
    # Total meetings
    total_meetings = len(df)
    st.sidebar.metric("Total Meetings", f"{total_meetings:,}")
    
    # Date range
    date_range = f"{df['date'].min().strftime('%m/%d/%Y')} to {df['date'].max().strftime('%m/%d/%Y')}"
    st.sidebar.markdown(f"**📅 Date Range:**  \n{date_range}")
    
    # Organizations
    orgs = df[df['organization'] != 'Internal']['organization'].nunique()
    st.sidebar.metric("Organizations", f"{orgs:,}")
    
    # Average sentiment
    avg_sentiment = df['sentiment_score'].mean()
    st.sidebar.metric("Avg Sentiment", f"{avg_sentiment:.2f}/5.0")
    
    st.sidebar.markdown("---")
    
    # Call type distribution
    st.sidebar.markdown("**📞 Call Types:**")
    call_type_counts = df['call_type'].value_counts()
    for call_type, count in call_type_counts.items():
        pct = count / total_meetings * 100
        st.sidebar.write(f"• {call_type}: {count} ({pct:.1f}%)")
    
    # Automatically redirect to Home page
    st.switch_page("pages/0_🏠_Home.py")


# Entry point
if __name__ == "__main__":
    main()
