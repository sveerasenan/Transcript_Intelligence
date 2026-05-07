"""
Home Page - Aegis Transcript Intelligence
=========================================

Welcome page with dataset overview and navigation instructions.

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.css_loader import load_css, apply_custom_styles


def main():
    """
    Main function for Home page.
    
    Displays:
    - Application header
    - Welcome message
    - Quick statistics
    - Navigation guidance
    """
    
    # Load CSS styles
    load_css()
    apply_custom_styles()
    
    # Application header
    st.markdown('<div class="main-header">🎯 Aegis Transcript Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Meeting Analysis & Business Intelligence</div>', unsafe_allow_html=True)
    
    # Get data from session state
    if 'meetings_df' not in st.session_state:
        st.warning("⚠️ Data not loaded. Redirecting to initialize...")
        st.switch_page("app.py")
        st.stop()
    
    df = st.session_state['meetings_df']
    
    st.markdown("---")
    
    # Welcome message with navigation
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 👋 Welcome to Aegis Transcript Intelligence
        
        This application provides comprehensive analysis of meeting transcripts to help you:
        
        ✅ **Categorize** meetings automatically using intelligent keyword matching  
        ✅ **Monitor** sentiment trends across customers and call types  
        ✅ **Identify** churn risks and at-risk accounts  
        ✅ **Track** renewal status and product adoption  
        ✅ **Analyze** organizational health and engagement patterns
        
        ---
        
        ### 🚀 Get Started
        
        Navigate using the **sidebar menu** to explore different views:
        
        **📊 Category** - View all meetings in a searchable table with advanced filters  
        **🏢 Organization** - Deep-dive into specific customer accounts  
        **💭 Sentiment** - Analyze sentiment patterns (Coming in Phase 2)  
        **🚧 Recurring Blockers** - Identify common issues (Coming in Phase 2)  
        **⚠️ Churn Risks** - Early warning system for at-risk accounts (Coming in Phase 2)
        """)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h4>📈 Quick Stats</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Category distribution
        st.markdown("**Top Categories:**")
        top_categories = df['category'].value_counts().head(5)
        for cat, count in top_categories.items():
            st.write(f"• {cat}: {count}")
        
        st.markdown("---")
        
        # Sentiment distribution
        st.markdown("**Sentiment Distribution:**")
        sentiment_counts = df['overall_sentiment'].value_counts()
        for sentiment, count in sentiment_counts.items():
            st.write(f"• {sentiment}: {count}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #64748B; padding: 1rem;">
            Built with ❤️ using Streamlit | Aegis Transcript Intelligence v1.0
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
