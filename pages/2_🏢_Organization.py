"""
Organization Page - Aegis Transcript Intelligence
=================================================

Provides deep-dive analysis for specific customer organizations:
- Overall sentiment metrics and trends
- Meeting history and timeline
- Product mentions and usage
- Churn risk assessment
- Renewal status tracking

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.organization_analyzer import OrganizationAnalyzer
from utils.css_loader import load_css, apply_custom_styles


def create_sentiment_donut_chart(sentiment_metrics):
    """
    Create a donut chart for sentiment distribution.
    
    Args:
        sentiment_metrics (dict): Dictionary with positive_pct, neutral_pct, negative_pct
        
    Returns:
        plotly.graph_objects.Figure: Donut chart
    """
    labels = ['Positive', 'Neutral', 'Negative']
    values = [
        sentiment_metrics['positive_pct'],
        sentiment_metrics['neutral_pct'],
        sentiment_metrics['negative_pct']
    ]
    colors = ['#10B981', '#6B7280', '#EF4444']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textposition='outside'
    )])
    
    fig.update_layout(
        showlegend=False,
        height=300,
        margin=dict(t=0, b=0, l=0, r=0)
    )
    
    return fig


def create_sentiment_timeline(org_df):
    """
    Create a line chart showing sentiment over time.
    
    Args:
        org_df (pd.DataFrame): Organization's meetings
        
    Returns:
        plotly.graph_objects.Figure: Line chart
    """
    # Sort by date ascending for timeline
    timeline_df = org_df.sort_values('date')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timeline_df['date'],
        y=timeline_df['sentiment_score'],
        mode='lines+markers',
        name='Sentiment Score',
        line=dict(color='#3B82F6', width=2),
        marker=dict(size=8),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Sentiment: %{y:.2f}/5.0<extra></extra>'
    ))
    
    # Add reference lines
    fig.add_hline(y=3.0, line_dash="dash", line_color="gray", opacity=0.5, annotation_text="Neutral (3.0)")
    fig.add_hline(y=2.5, line_dash="dash", line_color="red", opacity=0.3, annotation_text="Risk Threshold (2.5)")
    
    fig.update_layout(
        title="Sentiment Trend Over Time",
        xaxis_title="Date",
        yaxis_title="Sentiment Score (1-5)",
        yaxis=dict(range=[1, 5]),
        height=350,
        hovermode='x unified'
    )
    
    return fig


def create_product_bar_chart(product_counts):
    """
    Create a bar chart for product mentions.
    
    Args:
        product_counts (dict): Dictionary mapping product names to mention counts
        
    Returns:
        plotly.graph_objects.Figure: Bar chart
    """
    products = list(product_counts.keys())
    counts = list(product_counts.values())
    colors = ['#3B82F6', '#10B981', '#F59E0B']
    
    fig = go.Figure(data=[
        go.Bar(
            x=products,
            y=counts,
            marker_color=colors,
            text=counts,
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Product Mentions Across Meetings",
        xaxis_title="Product",
        yaxis_title="Number of Mentions",
        height=300,
        showlegend=False
    )
    
    return fig


def format_risk_badge(risk_level):
    """
    Format risk level as a colored badge.
    
    Args:
        risk_level (str): 'High', 'Medium', or 'Low'
        
    Returns:
        str: HTML for colored badge
    """
    color_map = {
        'High': '#EF4444',
        'Medium': '#F59E0B',
        'Low': '#10B981'
    }
    
    color = color_map.get(risk_level, '#6B7280')
    icon_map = {
        'High': '🚨',
        'Medium': '⚠️',
        'Low': '✅'
    }
    icon = icon_map.get(risk_level, '•')
    
    return f'<div style="background-color: {color}; color: white; padding: 1rem; border-radius: 0.5rem; text-align: center; font-size: 1.5rem; font-weight: bold;">{icon} {risk_level} Risk</div>'


def format_renewal_status(status):
    """
    Format renewal status with appropriate styling.
    
    Args:
        status (str): Renewal status
        
    Returns:
        str: HTML for formatted status
    """
    color_map = {
        'Active Discussions': '#10B981',
        'Recent Activity': '#3B82F6',
        'Due Soon': '#F59E0B',
        'No Recent Activity': '#6B7280'
    }
    
    color = color_map.get(status, '#6B7280')
    
    return f'<div style="background-color: {color}; color: white; padding: 0.75rem; border-radius: 0.5rem; text-align: center; font-weight: bold;">{status}</div>'


def show_overview_summary(df, analyzer):
    """
    Display aggregate summary across all organizations.
    
    Shows high-level metrics, top organizations by meeting count,
    sentiment distribution, and at-risk organizations.
    
    Args:
        df (pd.DataFrame): Full meetings dataframe
        analyzer (OrganizationAnalyzer): Analyzer instance
    """
    st.markdown("## 📊 Organizations Overview")
    st.markdown("Aggregate insights across all customer organizations")
    st.markdown("---")
    
    # Filter out internal meetings
    external_df = df[df['organization'] != 'Internal'].copy()
    
    if len(external_df) == 0:
        st.warning("⚠️ No external organizations found in the dataset.")
        return
    
    # Calculate aggregate metrics
    total_orgs = external_df['organization'].nunique()
    total_meetings = len(external_df)
    avg_sentiment = external_df['sentiment_score'].mean()
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Organizations", total_orgs)
    
    with col2:
        st.metric("Total Meetings", total_meetings)
    
    with col3:
        st.metric("Avg Sentiment", f"{avg_sentiment:.2f}/5.0")
    
    with col4:
        avg_meetings_per_org = total_meetings / total_orgs if total_orgs > 0 else 0
        st.metric("Avg Meetings/Org", f"{avg_meetings_per_org:.1f}")
    
    st.markdown("---")
    
    # Organizations by meeting count
    st.subheader("📈 Most Active Organizations")
    org_counts = external_df['organization'].value_counts().head(10)
    
    fig_top_orgs = go.Figure(data=[
        go.Bar(
            x=org_counts.values,
            y=org_counts.index,
            orientation='h',
            marker=dict(color='#3B82F6')
        )
    ])
    
    fig_top_orgs.update_layout(
        xaxis_title="Number of Meetings",
        yaxis_title="Organization",
        height=400,
        margin=dict(l=0, r=0, t=20, b=0)
    )
    
    st.plotly_chart(fig_top_orgs, use_container_width=True)
    
    st.markdown("---")
    
    # Sentiment distribution across all orgs
    st.subheader("💭 Overall Sentiment Distribution")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        sentiment_counts = external_df['overall_sentiment'].value_counts()
        
        fig_sentiment = go.Figure(data=[go.Pie(
            labels=sentiment_counts.index,
            values=sentiment_counts.values,
            hole=0.4,
            marker=dict(colors=['#10B981', '#6B7280', '#F59E0B', '#EF4444']),
            textinfo='label+percent'
        )])
        
        fig_sentiment.update_layout(
            height=300,
            margin=dict(t=0, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig_sentiment, use_container_width=True)
    
    with col2:
        st.markdown("**Sentiment Breakdown:**")
        for sentiment, count in sentiment_counts.items():
            pct = (count / len(external_df)) * 100
            st.write(f"• {sentiment}: {count} meetings ({pct:.1f}%)")
        
        st.markdown("---")
        st.markdown("**Average Sentiment by Score:**")
        st.write(f"• Mean: {external_df['sentiment_score'].mean():.2f}")
        st.write(f"• Median: {external_df['sentiment_score'].median():.2f}")
        st.write(f"• Std Dev: {external_df['sentiment_score'].std():.2f}")
    
    st.markdown("---")
    
    # At-risk organizations (low sentiment)
    st.subheader("⚠️ Organizations Requiring Attention")
    
    # Calculate average sentiment per organization
    org_sentiment = external_df.groupby('organization').agg({
        'sentiment_score': 'mean',
        'meetingId': 'count'
    }).rename(columns={'meetingId': 'meeting_count'})
    
    # Find organizations with low average sentiment (< 2.5) or negative overall sentiments
    negative_sentiments = external_df[external_df['overall_sentiment'].str.contains('negative', case=False, na=False)]
    at_risk_orgs = negative_sentiments['organization'].value_counts().head(10)
    
    if len(at_risk_orgs) > 0:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Organizations with Negative Sentiments:**")
            for org, count in at_risk_orgs.items():
                avg_sent = org_sentiment.loc[org, 'sentiment_score']
                st.write(f"• **{org}**: {count} negative meetings (avg: {avg_sent:.2f})")
        
        with col2:
            # Bar chart of at-risk organizations
            fig_risk = go.Figure(data=[
                go.Bar(
                    x=at_risk_orgs.values,
                    y=at_risk_orgs.index,
                    orientation='h',
                    marker=dict(color='#EF4444')
                )
            ])
            
            fig_risk.update_layout(
                xaxis_title="Negative Meetings Count",
                yaxis_title="Organization",
                height=300,
                margin=dict(l=0, r=0, t=20, b=0)
            )
            
            st.plotly_chart(fig_risk, use_container_width=True)
    else:
        st.success("✅ No organizations with significant negative sentiment patterns detected")
    
    st.markdown("---")
    
    # Category distribution
    st.subheader("📂 Meeting Categories Distribution")
    
    category_counts = external_df['category'].value_counts().head(8)
    
    fig_categories = go.Figure(data=[
        go.Bar(
            x=category_counts.index,
            y=category_counts.values,
            marker=dict(color='#8B5CF6')
        )
    ])
    
    fig_categories.update_layout(
        xaxis_title="Category",
        yaxis_title="Number of Meetings",
        height=350,
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis={'tickangle': -45}
    )
    
    st.plotly_chart(fig_categories, use_container_width=True)
    
    st.markdown("---")
    
    # Instructions
    st.info("💡 **Tip:** Select a specific organization from the sidebar to view detailed analysis including churn risk, renewal status, and meeting history.")


def main():
    """
    Main function for Organization page.
    
    Displays:
    - Organization selector
    - Summary metrics header
    - Sentiment analysis and trends
    - Product mentions
    - Churn risk assessment
    - Renewal status
    - Meeting history table
    """
    
    # Load CSS styles
    load_css()
    apply_custom_styles()
    
    st.title("🏢 Organization Analysis")
    st.markdown("Deep-dive into customer account health, sentiment, and engagement")
    st.markdown("---")
    
    # Get data from session state
    if 'meetings_df' not in st.session_state:
        st.error("❌ No data loaded. Please return to the home page.")
        return
    
    df = st.session_state['meetings_df'].copy()
    analyzer = OrganizationAnalyzer()
    
    # Get list of organizations (exclude Internal)
    organizations = sorted(df[df['organization'] != 'Internal']['organization'].unique().tolist())
    
    if not organizations:
        st.warning("⚠️ No external organizations found in the dataset.")
        return
    
    # Sidebar - Organization selector with Overview option
    st.sidebar.header("🏢 Select Organization")
    
    # Add "Overview" as default option
    org_options = ["-- Overview (All Organizations) --"] + organizations
    
    selected_org = st.sidebar.selectbox(
        "Choose an organization:",
        options=org_options,
        index=0,
        help="Select 'Overview' for aggregate insights, or choose a specific organization for detailed analysis"
    )
    
    st.sidebar.markdown("---")
    
    # Check if overview is selected
    if selected_org == "-- Overview (All Organizations) --":
        # Show aggregate summary
        show_overview_summary(df, analyzer)
        return
    
    # Otherwise, show detailed organization analysis
    # Date range filter for organization meetings
    st.sidebar.subheader("📅 Date Filter")
    org_df = analyzer.get_organization_meetings(df, selected_org)
    
    if len(org_df) == 0:
        st.warning(f"⚠️ No meetings found for {selected_org}")
        return
    
    min_date = org_df['date'].min().date()
    max_date = org_df['date'].max().date()
    
    # Display formatted date range
    st.sidebar.caption(f"Available: {min_date.strftime('%m/%d/%Y')} - {max_date.strftime('%m/%d/%Y')}")
    
    date_range = st.sidebar.date_input(
        "Date range:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="MM/DD/YYYY"
    )
    
    # Apply date filter
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        org_df = org_df[
            (org_df['date'].dt.date >= start_date) &
            (org_df['date'].dt.date <= end_date)
        ]
    
    # Calculate metrics
    sentiment_metrics = analyzer.calculate_sentiment_metrics(org_df)
    product_data = analyzer.extract_product_mentions(org_df)
    churn_risk = analyzer.calculate_churn_risk(org_df)
    renewal_status = analyzer.check_renewal_status(org_df)
    
    # Header with organization name
    st.markdown(f"## {selected_org}")
    st.markdown("---")
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Meetings", len(org_df))
    
    with col2:
        avg_sentiment = sentiment_metrics['avg_sentiment']
        trend_icon = {
            'improving': '📈',
            'declining': '📉',
            'stable': '➡️'
        }
        icon = trend_icon.get(sentiment_metrics['sentiment_trend'], '➡️')
        st.metric(
            "Avg Sentiment",
            f"{avg_sentiment:.2f}/5.0",
            delta=f"{icon} {sentiment_metrics['sentiment_trend']}"
        )
    
    with col3:
        first_meeting = org_df['date'].max().strftime('%m/%d/%Y')
        last_meeting = org_df['date'].min().strftime('%m/%d/%Y')
        st.metric("Latest Meeting", first_meeting)
        st.caption(f"First: {last_meeting}")
    
    with col4:
        # Primary product (most mentioned)
        product_counts = product_data['counts']
        primary_product = max(product_counts, key=product_counts.get) if any(product_counts.values()) else "None"
        st.metric("Primary Product", primary_product)
    
    st.markdown("---")
    
    # Sentiment Analysis Section
    st.subheader("💭 Sentiment Analysis")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Sentiment distribution donut chart
        fig_donut = create_sentiment_donut_chart(sentiment_metrics)
        st.plotly_chart(fig_donut, use_container_width=True)
        
        # Sentiment breakdown
        st.markdown("**Sentiment Breakdown:**")
        st.write(f"• Positive: {sentiment_metrics['positive_pct']:.1f}%")
        st.write(f"• Neutral: {sentiment_metrics['neutral_pct']:.1f}%")
        st.write(f"• Negative: {sentiment_metrics['negative_pct']:.1f}%")
    
    with col2:
        # Sentiment timeline
        if len(org_df) > 1:
            fig_timeline = create_sentiment_timeline(org_df)
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("📊 Timeline requires multiple meetings")
    
    st.markdown("---")
    
    # Product Mentions Section
    st.subheader("📦 Product Mentions")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        fig_products = create_product_bar_chart(product_data['counts'])
        st.plotly_chart(fig_products, use_container_width=True)
    
    with col2:
        st.markdown("**Product Context Examples:**")
        for product, contexts in product_data['contexts'].items():
            if contexts:
                with st.expander(f"📦 {product} ({product_data['counts'][product]} mentions)"):
                    for ctx in contexts:
                        st.write(f"**{ctx['title']}**")
                        st.write(f"_{ctx['context']}_")
                        st.write(f"Date: {ctx['date'].strftime('%m/%d/%Y')}")
                        st.markdown("---")
    
    st.markdown("---")
    
    # Churn Risk Assessment Section
    st.subheader("⚠️ Churn Risk Assessment")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Risk level badge
        st.markdown(format_risk_badge(churn_risk['risk_level']), unsafe_allow_html=True)
        st.markdown(f"**Risk Score:** {churn_risk['risk_score']}/10+")
    
    with col2:
        # Risk factors
        st.markdown("**Risk Factors Identified:**")
        if churn_risk['risk_factors']:
            for factor in churn_risk['risk_factors']:
                st.write(factor)
        else:
            st.success("✅ No significant risk factors detected")
        
        st.markdown("**Recommended Actions:**")
        if churn_risk['recommendations']:
            for rec in churn_risk['recommendations']:
                st.write(f"• {rec}")
    
    st.markdown("---")
    
    # Renewal Status Section
    st.subheader("🔄 Renewal Status")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(format_renewal_status(renewal_status['status']), unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Details:**")
        st.write(renewal_status['details'])
        
        if renewal_status['last_discussion']:
            st.write(f"**Last Renewal Discussion:** {renewal_status['last_discussion'].strftime('%m/%d/%Y')}")
            st.write(f"**Days Since Discussion:** {renewal_status.get('days_since_discussion', 'N/A')}")
    
    st.markdown("---")
    
    # Meeting History Table
    st.subheader("📋 Meeting History")
    
    # Prepare display DataFrame
    display_df = org_df[[
        'date', 'title', 'category', 'call_type', 
        'overall_sentiment', 'sentiment_score', 'duration'
    ]].copy()
    
    # Format columns
    display_df['date'] = display_df['date'].dt.strftime('%m/%d/%Y %H:%M')
    display_df['sentiment_score'] = display_df['sentiment_score'].apply(lambda x: f"{x:.2f}")
    display_df['duration'] = display_df['duration'].apply(lambda x: f"{x:.1f} min")
    
    # Rename for display
    display_df.columns = [
        'Date', 'Title', 'Category', 'Call Type',
        'Sentiment', 'Score', 'Duration'
    ]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Export organization report
    st.markdown("---")
    
    if st.button("📥 Export Organization Report"):
        # Create comprehensive report
        report_data = {
            'Organization': [selected_org],
            'Total Meetings': [len(org_df)],
            'Avg Sentiment': [sentiment_metrics['avg_sentiment']],
            'Sentiment Trend': [sentiment_metrics['sentiment_trend']],
            'Positive %': [sentiment_metrics['positive_pct']],
            'Neutral %': [sentiment_metrics['neutral_pct']],
            'Negative %': [sentiment_metrics['negative_pct']],
            'Churn Risk Level': [churn_risk['risk_level']],
            'Churn Risk Score': [churn_risk['risk_score']],
            'Renewal Status': [renewal_status['status']],
            'Detect Mentions': [product_data['counts']['Detect']],
            'Comply Mentions': [product_data['counts']['Comply']],
            'Protect Mentions': [product_data['counts']['Protect']],
        }
        
        report_df = pd.DataFrame(report_data)
        csv = report_df.to_csv(index=False)
        
        st.download_button(
            label="Download Report",
            data=csv,
            file_name=f"aegis_org_report_{selected_org.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
