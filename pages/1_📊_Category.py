"""
Category Page - Aegis Transcript Intelligence
=============================================

Displays all meetings in a searchable, filterable table with:
- Multi-criteria filtering (date, organization, category, call type, sentiment)
- Search functionality
- Export to CSV capability
- Expandable comments/details

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.css_loader import load_css, apply_custom_styles


def format_sentiment_badge(sentiment):
    """
    Format sentiment as a colored badge for display.
    
    Args:
        sentiment (str): Sentiment label (e.g., 'positive', 'negative', 'mixed-positive')
        
    Returns:
        str: HTML for colored badge
    """
    color_map = {
        'positive': '#10B981',
        'mixed-positive': '#3B82F6',
        'neutral': '#6B7280',
        'mixed-negative': '#F59E0B',
        'negative': '#EF4444'
    }
    
    sentiment_lower = sentiment.lower()
    color = color_map.get(sentiment_lower, '#6B7280')
    
    return f'<span style="background-color: {color}; color: white; padding: 0.25rem 0.75rem; border-radius: 0.25rem; font-size: 0.875rem;">{sentiment}</span>'


def format_confidence_badge(confidence):
    """
    Format confidence level as a colored badge.
    
    Args:
        confidence (str): 'High', 'Medium', or 'Low'
        
    Returns:
        str: HTML for colored badge
    """
    color_map = {
        'High': '#10B981',
        'Medium': '#F59E0B',
        'Low': '#EF4444'
    }
    
    color = color_map.get(confidence, '#6B7280')
    return f'<span style="background-color: {color}; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">{confidence}</span>'


def main():
    """
    Main function for Category page.
    
    Features:
    - Comprehensive filtering sidebar
    - Searchable data table
    - Export functionality
    - Summary metrics
    """
    
    # Load CSS styles
    load_css()
    apply_custom_styles()
    
    st.title("📊 Meeting Categories")
    st.markdown("View and filter all meetings with detailed categorization")
    st.markdown("---")
    
    # Get data from session state
    if 'meetings_df' not in st.session_state:
        st.error("❌ No data loaded. Please return to the home page.")
        return
    
    df = st.session_state['meetings_df'].copy()
    
    # Sidebar - Filters
    st.sidebar.header("🔍 Filters")
    st.sidebar.markdown("---")
    
    # Date range filter
    st.sidebar.subheader("📅 Date Range")
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    
    # Display formatted date range
    st.sidebar.caption(f"Available: {min_date.strftime('%m/%d/%Y')} - {max_date.strftime('%m/%d/%Y')}")
    
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="MM/DD/YYYY"
    )
    
    # Handle single date selection
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range if not isinstance(date_range, tuple) else date_range[0]
    
    # Organization filter
    st.sidebar.subheader("🏢 Organization")
    all_orgs = sorted(df['organization'].unique().tolist())
    selected_orgs = st.sidebar.multiselect(
        "Select organizations",
        options=all_orgs,
        default=None,
        help="Leave empty to show all organizations"
    )
    
    # Category filter
    st.sidebar.subheader("📑 Category")
    all_categories = sorted(df['category'].unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Select categories",
        options=all_categories,
        default=None,
        help="Leave empty to show all categories"
    )
    
    # Call Type filter
    st.sidebar.subheader("📞 Call Type")
    all_call_types = sorted(df['call_type'].unique().tolist())
    selected_call_types = st.sidebar.multiselect(
        "Select call types",
        options=all_call_types,
        default=None,
        help="Leave empty to show all call types"
    )
    
    # Sentiment filter
    st.sidebar.subheader("💭 Sentiment")
    sentiment_options = sorted(df['overall_sentiment'].unique().tolist())
    selected_sentiments = st.sidebar.multiselect(
        "Select sentiment",
        options=sentiment_options,
        default=None,
        help="Leave empty to show all sentiments"
    )
    
    # Confidence filter
    st.sidebar.subheader("🎯 Confidence")
    confidence_options = ['High', 'Medium', 'Low']
    selected_confidence = st.sidebar.multiselect(
        "Select confidence level",
        options=confidence_options,
        default=None,
        help="Categorization confidence level"
    )
    
    # Duration filter
    st.sidebar.subheader("⏱️ Duration (minutes)")
    min_duration = float(df['duration'].min())
    max_duration = float(df['duration'].max())
    duration_range = st.sidebar.slider(
        "Select duration range",
        min_value=min_duration,
        max_value=max_duration,
        value=(min_duration, max_duration),
        step=1.0
    )
    
    # Search box
    st.sidebar.subheader("🔎 Search")
    search_term = st.sidebar.text_input(
        "Search in title or organization",
        value="",
        help="Search by keywords in meeting title or organization name"
    )
    
    # Clear filters button
    if st.sidebar.button("🔄 Clear All Filters"):
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Apply filters to DataFrame
    filtered_df = df.copy()
    
    # Date filter
    filtered_df = filtered_df[
        (filtered_df['date'].dt.date >= start_date) &
        (filtered_df['date'].dt.date <= end_date)
    ]
    
    # Organization filter
    if selected_orgs:
        filtered_df = filtered_df[filtered_df['organization'].isin(selected_orgs)]
    
    # Category filter
    if selected_categories:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
    
    # Call Type filter
    if selected_call_types:
        filtered_df = filtered_df[filtered_df['call_type'].isin(selected_call_types)]
    
    # Sentiment filter
    if selected_sentiments:
        filtered_df = filtered_df[filtered_df['overall_sentiment'].isin(selected_sentiments)]
    
    # Confidence filter
    if selected_confidence:
        filtered_df = filtered_df[filtered_df['confidence'].isin(selected_confidence)]
    
    # Duration filter
    filtered_df = filtered_df[
        (filtered_df['duration'] >= duration_range[0]) &
        (filtered_df['duration'] <= duration_range[1])
    ]
    
    # Search filter
    if search_term:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_term, case=False, na=False) |
            filtered_df['organization'].str.contains(search_term, case=False, na=False)
        ]
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Filtered Meetings", f"{len(filtered_df):,} of {len(df):,}")
    
    with col2:
        avg_sentiment = filtered_df['sentiment_score'].mean() if len(filtered_df) > 0 else 0
        st.metric("Avg Sentiment", f"{avg_sentiment:.2f}/5.0")
    
    with col3:
        avg_duration = filtered_df['duration'].mean() if len(filtered_df) > 0 else 0
        st.metric("Avg Duration", f"{avg_duration:.1f} min")
    
    with col4:
        unique_orgs = filtered_df[filtered_df['organization'] != 'Internal']['organization'].nunique()
        st.metric("Organizations", f"{unique_orgs:,}")
    
    st.markdown("---")
    
    # Export button
    if len(filtered_df) > 0:
        # Prepare export data
        export_df = filtered_df[[
            'meetingId', 'date', 'title', 'organization', 'category', 
            'confidence', 'duration', 'call_type', 
            'overall_sentiment', 'sentiment_score', 'comments'
        ]].copy()
        
        # Format date for export
        export_df['date'] = export_df['date'].dt.strftime('%m/%d/%Y %H:%M:%S')
        
        csv = export_df.to_csv(index=False)
        
        st.download_button(
            label="📥 Export to CSV",
            data=csv,
            file_name=f"aegis_meetings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download filtered data as CSV file"
        )
    
    # Display data table
    if len(filtered_df) == 0:
        st.warning("⚠️ No meetings match the selected filters. Try adjusting your filter criteria.")
    else:
        st.subheader(f"📋 Meetings ({len(filtered_df)} results)")
        
        # Prepare display DataFrame
        display_df = filtered_df[[
            'meetingId', 'date', 'title', 'organization', 'category', 
            'confidence', 'duration', 'call_type', 
            'overall_sentiment', 'sentiment_score'
        ]].copy()
        
        # Format columns for display
        display_df['date'] = display_df['date'].dt.strftime('%m/%d/%Y %H:%M')
        display_df['duration'] = display_df['duration'].apply(lambda x: f"{x:.1f} min")
        display_df['sentiment_score'] = display_df['sentiment_score'].apply(lambda x: f"{x:.2f}")
        
        # Rename columns for better display
        display_df.columns = [
            'Meeting ID', 'Date', 'Title', 'Organization', 'Category',
            'Confidence', 'Duration', 'Call Type', 'Sentiment', 'Score (1-5)'
        ]
        
        # Display table with configuration
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500,
            hide_index=True,
            column_config={
                "Meeting ID": st.column_config.TextColumn("Meeting ID", width="small"),
                "Date": st.column_config.TextColumn("Date", width="medium"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Organization": st.column_config.TextColumn("Organization", width="medium"),
                "Category": st.column_config.TextColumn("Category", width="medium"),
                "Confidence": st.column_config.TextColumn("Confidence", width="small"),
                "Duration": st.column_config.TextColumn("Duration", width="small"),
                "Call Type": st.column_config.TextColumn("Call Type", width="medium"),
                "Sentiment": st.column_config.TextColumn("Sentiment", width="medium"),
                "Score (1-5)": st.column_config.TextColumn("Score", width="small"),
            }
        )
        
        # Expandable details section
        st.markdown("---")
        st.subheader("🔍 Meeting Details")
        st.markdown("Select a meeting to view detailed categorization comments")
        
        # Meeting selector
        meeting_titles = filtered_df['title'].tolist()
        selected_meeting_title = st.selectbox(
            "Choose a meeting:",
            options=["-- Select a meeting --"] + meeting_titles,
            index=0
        )
        
        if selected_meeting_title != "-- Select a meeting --":
            # Find the selected meeting
            selected_meeting = filtered_df[filtered_df['title'] == selected_meeting_title].iloc[0]
            
            # Display details in columns
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("**Meeting Information:**")
                st.write(f"**ID:** {selected_meeting['meetingId']}")
                st.write(f"**Date:** {selected_meeting['date'].strftime('%m/%d/%Y %H:%M')}")
                st.write(f"**Duration:** {selected_meeting['duration']:.1f} minutes")
                st.write(f"**Organization:** {selected_meeting['organization']}")
                st.write(f"**Call Type:** {selected_meeting['call_type']}")
                st.markdown(f"**Sentiment:** {format_sentiment_badge(selected_meeting['overall_sentiment'])}", unsafe_allow_html=True)
                st.write(f"**Sentiment Score:** {selected_meeting['sentiment_score']:.2f}/5.0")
                
                # Display invitees
                st.markdown("**Invitees:**")
                participants = selected_meeting['participants']
                if participants and participants.strip():  # Check if string is not empty
                    # Split comma-separated string
                    participants_list = [p.strip() for p in participants.split(',') if p.strip()]
                    for participant in participants_list:
                        st.write(f"• {participant}")
                else:
                    st.write("_No invitees recorded_")
            
            with col2:
                st.markdown("**Categorization Details:**")
                st.write(f"**Category:** {selected_meeting['category']}")
                st.write(f"**Score:** {selected_meeting['category_score']}")
                st.markdown(f"**Confidence:** {format_confidence_badge(selected_meeting['confidence'])}", unsafe_allow_html=True)
                st.markdown("**Comments:**")
                st.info(selected_meeting['comments'])
            
            # Topics and action items
            st.markdown("**Topics Discussed:**")
            topics = selected_meeting['topics']
            if topics and topics.strip():  # Check if string is not empty
                # Split comma-separated string
                topics_list = [t.strip() for t in topics.split(',') if t.strip()]
                for topic in topics_list:
                    st.write(f"• {topic}")
            else:
                st.write("_No topics recorded_")
            
            st.markdown("**Action Items:**")
            action_items = selected_meeting['action_items']
            if action_items and action_items.strip():  # Check if string is not empty
                # Split comma-separated string
                items_list = [item.strip() for item in action_items.split(',') if item.strip()]
                for item in items_list:
                    st.write(f"• {item}")
            else:
                st.write("_No action items recorded_")
            
            # Key moments
            import json
            key_moments_str = selected_meeting['key_moments']
            if key_moments_str and key_moments_str.strip() and key_moments_str != '[]':
                st.markdown("**Key Moments:**")
                try:
                    key_moments_list = json.loads(key_moments_str)
                    for moment in key_moments_list:
                        moment_type = moment.get('type', 'unknown')
                        moment_text = moment.get('text', '')
                        moment_time = moment.get('time', 0)
                        
                        # Format time as MM:SS
                        minutes = int(moment_time // 60)
                        seconds = int(moment_time % 60)
                        time_str = f"{minutes:02d}:{seconds:02d}"
                        
                        st.write(f"⏱️ **{time_str}** [{moment_type}]: {moment_text}")
                except json.JSONDecodeError:
                    st.write("_Error parsing key moments_")


if __name__ == "__main__":
    main()
