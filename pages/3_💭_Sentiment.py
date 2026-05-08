"""
Sentiment Analysis Page - Aegis Transcript Intelligence
=======================================================

Interactive sentiment analysis across call types:
- Multi-line chart showing sentiment trends over time
- Sentiment comparison across Customer Support, External, and Internal calls
- Rule-based insights identifying patterns, trends, and anomalies
- Outage detection and impact analysis
- LLM-powered deep insights for individual meetings

This page provides UI orchestration, delegating business logic to 
utils.sentiment_analyzer.SentimentAnalyzer class.

Author: Aegis Transcript Intelligence Team
Date: 2026-05-07
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.css_loader import load_css, apply_custom_styles
from utils.sentiment_analyzer import SentimentAnalyzer
from services.llm_insights_service import LLMInsightsService


def main():
    """
    Main function for Sentiment Analysis page.
    
    Orchestrates UI components and delegates business logic to SentimentAnalyzer:
    - Interactive multi-line chart: sentiment over time by call type
    - Summary metrics and trend indicators
    - Rule-based insights with actionable recommendations
    """
    
    # Load CSS styles
    load_css()
    apply_custom_styles()
    
    st.title("💭 Sentiment Analysis Across Call Types")
    st.markdown("Track sentiment trends and identify patterns across different meeting types")
    
    # Display 5-Tier Sentiment Scale
    st.info("""
    **📊 5-Tier Sentiment Scale:**  
    🔴 **0.0 – 2.4 Critical** → Severe issues, immediate escalation required  
    🟠 **2.5 – 3.4 Needs Attention** → Below acceptable, requires investigation  
    🟡 **3.5 – 3.9 Acceptable** → Meeting baseline expectations  
    🟢 **4.0 – 4.4 Strong** → Good customer experience  
    ⭐ **4.5 – 5.0 Exceptional** → Outstanding service
    """)
    
    st.markdown("---")
    
    # Get data from session state
    if 'meetings_df' not in st.session_state:
        st.error("❌ No data loaded. Please return to the home page.")
        return
    
    df = st.session_state['meetings_df'].copy()
    
    # Load configuration
    config = SentimentAnalyzer.get_config()
    trend_window_days = config['trend_analysis']['window_days']
    
    # Sidebar Filters
    st.sidebar.header("🔍 Filters")
    st.sidebar.markdown("---")
    
    # Date Range Filter
    st.sidebar.subheader("📅 Date Range")
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    
    st.sidebar.caption(f"Available: {min_date.strftime('%m/%d/%Y')} - {max_date.strftime('%m/%d/%Y')}")
    
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="MM/DD/YYYY"
    )
    
    # Handle date range selection
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = min_date
    
    # Call Type Multi-Select Filter
    st.sidebar.subheader("📞 Call Types")
    all_call_types = sorted(df['call_type'].unique().tolist())
    
    selected_call_types = st.sidebar.multiselect(
        "Select call types to analyze",
        options=all_call_types,
        default=all_call_types,
        help="Select one or more call types to display on the chart"
    )
    
    # Apply filters
    filtered_df = df[
        (df['date'].dt.date >= start_date) &
        (df['date'].dt.date <= end_date) &
        (df['call_type'].isin(selected_call_types))
    ].copy()
    
    # Check if we have data after filtering
    if len(filtered_df) == 0:
        st.warning("⚠️ No meetings found for the selected filters. Please adjust your date range or call type selection.")
        return
    
    # Summary Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Meetings", f"{len(filtered_df):,}")
    
    with col2:
        overall_avg = filtered_df['sentiment_score'].mean()
        st.metric("Overall Avg Sentiment", f"{overall_avg:.2f}/5.0")
    
    with col3:
        date_range_display = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
        st.metric("Date Range", "Custom" if start_date != min_date or end_date != max_date else "All Time")
        st.caption(date_range_display)
    
    with col4:
        st.metric("Call Types", len(selected_call_types))
        st.caption(", ".join(selected_call_types[:2]) + ("..." if len(selected_call_types) > 2 else ""))
    
    st.markdown("---")
    
    # Main Chart Section
    st.subheader("📈 Sentiment Over Time by Call Type")
    
    # Use SentimentAnalyzer to create the timeline chart
    fig = SentimentAnalyzer.create_sentiment_timeline(filtered_df)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Trend Metrics Section
    st.subheader(f"📊 Trend Analysis (Last {trend_window_days} Days)")
    
    # Calculate trend metrics for each call type using SentimentAnalyzer
    trend_metrics_list = []
    for call_type in selected_call_types:
        metrics = SentimentAnalyzer.calculate_trend_metrics(filtered_df, call_type)
        if metrics:
            trend_metrics_list.append(metrics)
    
    if trend_metrics_list:
        # Display trend metrics in columns
        cols = st.columns(len(trend_metrics_list))
        
        for idx, metrics in enumerate(trend_metrics_list):
            with cols[idx]:
                if metrics['recent_avg'] is not None:
                    delta_text = f"{metrics['icon']} {metrics['change']:.1f}" if metrics['change'] is not None else None
                    st.metric(
                        metrics['call_type'],
                        f"{metrics['recent_avg']:.2f}/5.0",
                        delta=delta_text
                    )
                    st.caption(f"{metrics['recent_count']} meetings")
                else:
                    st.metric(metrics['call_type'], "N/A")
                    st.caption("No recent data")
    
    st.markdown("---")
    
    # Insights Section
    st.subheader("💡 Key Insights & Recommendations")
    
    # Generate insights using SentimentAnalyzer
    insights = SentimentAnalyzer.generate_insights(filtered_df, trend_metrics_list)
    
    if len(insights) > 0:
        for insight in insights:
            with st.expander(f"{insight['icon']} {insight['headline']}", expanded=False):
                st.markdown(f"**Metrics:** {insight['metrics']}")
                st.markdown(f"**What's happening:** {insight['explanation']}")
                st.markdown(f"**Why it matters:** {insight['why_matters']}")
                st.markdown(f"**Recommended action:** {insight['action']}")
    else:
        # Calculate average sentiment for the period
        avg_sentiment = filtered_df['sentiment_score'].mean() if len(filtered_df) > 0 else 0
        neutral_threshold = config['thresholds']['neutral_threshold']
        
        # Get sentiment category using 5-tier system
        category = SentimentAnalyzer.get_sentiment_category(avg_sentiment)
        
        if avg_sentiment < neutral_threshold:
            st.warning(f"{category['emoji']} Period average sentiment: **{avg_sentiment:.2f}/5.0** ({category['name']}: {category['description']}). No specific call type trends detected by rule-based analysis. Check AI-Powered High-Risk Analysis below for detailed insights on individual meetings.")
        else:
            st.success(f"{category['emoji']} Period average sentiment: **{avg_sentiment:.2f}/5.0** ({category['name']}: {category['description']}). No critical trends detected. Call types show stable sentiment patterns.")
    
    st.markdown("---")
    
    # Export Section
    if st.button("📥 Export Sentiment Analysis Report"):
        # Get export configuration
        export_config = config['export']
        filename_pattern = export_config['filename_pattern']
        
        # Create export data
        export_data = []
        
        for call_type in selected_call_types:
            call_type_df = filtered_df[filtered_df['call_type'] == call_type]
            if len(call_type_df) > 0:
                export_data.append({
                    'Call Type': call_type,
                    'Meeting Count': len(call_type_df),
                    'Avg Sentiment': call_type_df['sentiment_score'].mean(),
                    'Min Sentiment': call_type_df['sentiment_score'].min(),
                    'Max Sentiment': call_type_df['sentiment_score'].max(),
                    'Positive Meetings': len(call_type_df[call_type_df['overall_sentiment'].str.contains('positive', case=False, na=False)]),
                    'Negative Meetings': len(call_type_df[call_type_df['overall_sentiment'].str.contains('negative', case=False, na=False)])
                })
        
        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False)
        
        st.download_button(
            label="Download CSV Report",
            data=csv,
            file_name=datetime.now().strftime(filename_pattern),
            mime="text/csv"
        )
    
    st.markdown("---")
    
    # LLM Deep Insights Section
    st.subheader("🤖 AI-Powered High-Risk Analysis")
    st.markdown("**Critical insights for high-risk meetings** with low sentiment (<2.5 out of 5.0) requiring immediate attention.")    
    
    # Get low sentiment meetings (high-risk threshold)
    low_sentiment_meetings = filtered_df[filtered_df['sentiment_score'] < 2.5].sort_values('sentiment_score')
    
    if len(low_sentiment_meetings) > 0:
        st.markdown(f"**🚨 Found {len(low_sentiment_meetings)} HIGH-RISK meeting(s) with low sentiment in the selected period.**")
        
        # Initialize LLM service (provider from config)
        try:
            llm_service = LLMInsightsService()
            
            # Limit to top 10 meetings to stay within token limits
            meetings_to_analyze = low_sentiment_meetings.head(10)
            
            st.markdown(f"**Analyzing {len(meetings_to_analyze)} meetings in batch...**")
            
            with st.spinner(f"Generating batch insights using LLM... This may take 20-40 seconds."):
                try:
                    # Get date range from filtered data
                    period_start = meetings_to_analyze['date'].min().strftime('%Y-%m-%d')
                    period_end = meetings_to_analyze['date'].max().strftime('%Y-%m-%d')
                    
                    # Get batch insights (single LLM call for all meetings)
                    insights = llm_service.get_batch_insights(
                        meetings_to_analyze,
                        period_start=period_start,
                        period_end=period_end,
                        force_refresh=False
                    )
                    
                    st.success("✅ Batch analysis complete!")
                    st.markdown("---")
                    
                    # Executive Summary (most important - show first)
                    with st.expander("📊 Executive Summary", expanded=True):
                        executive_summary = insights.get('executive_summary', 'N/A')
                        if isinstance(executive_summary, list):
                            for item in executive_summary:
                                st.markdown(f"• {item}")
                        elif isinstance(executive_summary, dict):
                            # Handle nested dict format (flatten it)
                            st.warning("⚠️ LLM returned nested format. Displaying all insights:")
                            for category, items in executive_summary.items():
                                st.markdown(f"**{category.replace('_', ' ').title()}:**")
                                if isinstance(items, list):
                                    for item in items:
                                        st.markdown(f"• {item}")
                                else:
                                    st.markdown(f"• {items}")
                        else:
                            st.markdown(str(executive_summary))
                    
                    # Period Overview
                    with st.expander("📅 Period Overview", expanded=True):
                        period_overview = insights.get('period_overview', 'N/A')
                        if isinstance(period_overview, str):
                            st.markdown(period_overview)
                        elif isinstance(period_overview, dict):
                            # Handle nested dict format (flatten it)
                            st.warning("⚠️ LLM returned nested format. Displaying all sections:")
                            for key, value in period_overview.items():
                                st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                        elif isinstance(period_overview, list):
                            for item in period_overview:
                                st.markdown(f"• {item}")
                        else:
                            st.markdown(str(period_overview))
                    
                    # Actionable Recommendations (high priority)
                    with st.expander("💡 Actionable Recommendations", expanded=True):
                        recommendations = insights.get('actionable_recommendations', {})
                        if isinstance(recommendations, dict):
                            for category, items in recommendations.items():
                                st.markdown(f"**{category.replace('_', ' ').title()}:**")
                                if isinstance(items, list):
                                    for item in items:
                                        st.markdown(f"• {item}")
                                else:
                                    st.markdown(f"• {items}")
                        elif isinstance(recommendations, list):
                            for item in recommendations:
                                st.markdown(f"• {item}")
                        else:
                            st.markdown(str(recommendations))
                    
                    # Common Themes and Issues
                    with st.expander("🎯 Common Themes & Issues"):
                        themes = insights.get('common_themes', {})
                        if isinstance(themes, dict):
                            for category, items in themes.items():
                                st.markdown(f"**{category.replace('_', ' ').title()}:**")
                                if isinstance(items, list):
                                    for item in items:
                                        st.markdown(f"• {item}")
                                else:
                                    st.markdown(f"• {items}")
                        elif isinstance(themes, list):
                            for item in themes:
                                st.markdown(f"• {item}")
                        else:
                            st.markdown(str(themes))
                    
                    # Product Issues
                    with st.expander("🐛 Product Issues"):
                        product_issues = insights.get('product_issues', {})
                        if isinstance(product_issues, dict):
                            for category, items in product_issues.items():
                                st.markdown(f"**{category.replace('_', ' ').title()}:**")
                                if isinstance(items, list):
                                    for item in items:
                                        st.markdown(f"• {item}")
                                else:
                                    st.markdown(f"• {items}")
                        elif isinstance(product_issues, list):
                            for item in product_issues:
                                st.markdown(f"• {item}")
                        else:
                            st.markdown(str(product_issues))
                
                except Exception as e:
                    st.error(f"❌ Failed to generate batch insights: {str(e)}")
                    st.info("Check the console for detailed prompt logs.")
        
        except Exception as e:
            st.error(f"❌ Failed to initialize LLM service: {str(e)}")
            st.info("Make sure you have set the appropriate API key environment variable (OPENAI_API_KEY or GEMINI_API_KEY) and configured `config/llm.yaml`.")
    
    else:
        st.info("✅ No meetings with low sentiment (<2.5) found in the selected date range and call types.")


if __name__ == "__main__":
    main()
