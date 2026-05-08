"""
Sentiment Analyzer Module for Aegis Transcript Intelligence
============================================================

This module provides sentiment analysis capabilities including:
- Interactive timeline visualization by call type
- Trend analysis and change detection
- Rule-based insight generation
- Outage detection and impact assessment

Author: Aegis Transcript Intelligence Team
Date: 2026-05-07
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import yaml


class SentimentAnalyzer:
    """
    Analyzes sentiment patterns across call types and generates actionable insights.
    
    This class provides static methods for:
    - Creating interactive sentiment timeline visualizations
    - Calculating trend metrics over configurable time windows
    - Generating rule-based insights (at-risk, trending, outages)
    - Detecting anomalies and inconsistent experiences
    
    All methods are static as they operate on DataFrames and don't require state.
    Configuration is loaded from config/sentiment_analysis.yaml.
    """
    
    # Load configuration on class initialization
    _config = None
    
    @classmethod
    def _load_config(cls):
        """Load sentiment analysis configuration from YAML file."""
        if cls._config is None:
            config_path = Path(__file__).parent.parent / 'config' / 'sentiment_analysis.yaml'
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)
        return cls._config
    
    @classmethod
    def get_config(cls):
        """
        Get sentiment analysis configuration.
        
        Returns:
            dict: Configuration dictionary with thresholds, visualization settings, etc.
        """
        return cls._load_config()
    
    @staticmethod
    def get_sentiment_category(score):
        """
        Categorize a sentiment score using the 5-tier system.
        
        5-Tier Classification:
        🔴 0.0-2.4: Critical - Severe issues, immediate escalation required
        🟠 2.5-3.4: Needs Attention - Below acceptable, requires investigation
        🟡 3.5-3.9: Acceptable - Meeting baseline expectations
        🟢 4.0-4.4: Strong - Good customer experience
        ⭐ 4.5-5.0: Exceptional - Outstanding service
        
        Args:
            score (float): Sentiment score between 0.0 and 5.0
            
        Returns:
            dict: Category information with keys:
                - name: str (Critical, Needs Attention, Acceptable, Strong, Exceptional)
                - emoji: str (🔴, 🟠, 🟡, 🟢, ⭐)
                - color: str (hex color code)
                - description: str (brief description)
        """
        config = SentimentAnalyzer.get_config()
        thresholds = config['thresholds']
        
        if score <= thresholds['critical_threshold']:
            return {
                'name': 'Critical',
                'emoji': '🔴',
                'color': '#DC2626',
                'description': 'Severe issues, immediate escalation required'
            }
        elif score <= thresholds['needs_attention_threshold']:
            return {
                'name': 'Needs Attention',
                'emoji': '🟠',
                'color': '#F59E0B',
                'description': 'Below acceptable, requires investigation'
            }
        elif score <= thresholds['acceptable_threshold']:
            return {
                'name': 'Acceptable',
                'emoji': '🟡',
                'color': '#FBBF24',
                'description': 'Meeting baseline expectations'
            }
        elif score <= thresholds['strong_threshold']:
            return {
                'name': 'Strong',
                'emoji': '🟢',
                'color': '#10B981',
                'description': 'Good customer experience'
            }
        else:
            return {
                'name': 'Exceptional',
                'emoji': '⭐',
                'color': '#8B5CF6',
                'description': 'Outstanding service'
            }
    
    @staticmethod
    def create_sentiment_timeline(df):
        """
        Create interactive multi-line chart showing sentiment trends by call type.
        
        Features:
        - One line per call type with distinct colors
        - Lines + markers showing actual meeting points
        - Reference lines at risk, neutral, and target thresholds
        - Interactive tooltips with date, call type, sentiment score
        - Zoom, pan, and toggle lines via legend
        
        Args:
            df (pd.DataFrame): Filtered dataframe with meetings containing:
                - date: datetime
                - call_type: str
                - sentiment_score: float
                
        Returns:
            plotly.graph_objects.Figure: Interactive line chart with one line per call type
        """
        config = SentimentAnalyzer.get_config()
        viz_config = config['visualization']
        ref_lines = viz_config['reference_lines']
        color_map = viz_config['call_type_colors']
        default_color = viz_config['default_color']
        
        if len(df) == 0:
            # Return empty figure with message
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray")
            )
            return fig
        
        # Sort by date for proper line rendering
        df_sorted = df.sort_values('date')
        
        # Create figure
        fig = go.Figure()
        
        # Add a line for each call type
        for call_type in sorted(df_sorted['call_type'].unique()):
            call_type_df = df_sorted[df_sorted['call_type'] == call_type]
            
            fig.add_trace(go.Scatter(
                x=call_type_df['date'],
                y=call_type_df['sentiment_score'],
                mode='lines+markers',
                name=call_type,
                line=dict(
                    color=color_map.get(call_type, default_color),
                    width=2
                ),
                marker=dict(size=6, symbol='circle'),
                hovertemplate=(
                    '<b>%{fullData.name}</b><br>' +
                    'Date: %{x|%m/%d/%Y}<br>' +
                    'Sentiment: %{y:.2f}/5.0<br>' +
                    '<extra></extra>'
                )
            ))
        
        # Add reference lines
        for line_name, line_config in ref_lines.items():
            fig.add_hline(
                y=line_config['y_value'],
                line_dash="dash",
                line_color=line_config['color'],
                opacity=line_config['opacity'],
                annotation_text=line_config['label'],
                annotation_position="right"
            )
        
        # Update layout
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Sentiment Score",
            yaxis=dict(range=[1, 5], dtick=0.5),
            height=viz_config['chart_height'],
            margin=dict(l=50, r=20, t=50, b=50),
            hovermode='closest',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="right",
                x=0.99
            )
        )
        
        return fig
    
    @staticmethod
    def calculate_trend_metrics(df, call_type, window_days=None):
        """
        Calculate sentiment trend metrics for a specific call type.
        
        Compares recent period (last N days) vs previous period (prior N days)
        to detect improving, declining, or stable trends.
        
        Trend Classification:
        - Improving: recent_avg > previous_avg + threshold
        - Declining: recent_avg < previous_avg - threshold
        - Stable: change within threshold range
        
        Args:
            df (pd.DataFrame): Full dataframe with all meetings
            call_type (str): Call type to analyze (e.g., 'Customer Support')
            window_days (int, optional): Number of days for trend window.
                If None, uses config value (default: 30)
                
        Returns:
            dict or None: Trend metrics including:
                - call_type: Call type name
                - recent_avg: Average sentiment in recent window
                - previous_avg: Average sentiment in previous window
                - change: Difference (recent - previous)
                - direction: 'improving', 'declining', or 'stable'
                - icon: Emoji representing direction (📈/📉/➡️)
                - recent_count: Number of meetings in recent window
                - previous_count: Number of meetings in previous window
            Returns None if no data available for this call type
        """
        config = SentimentAnalyzer.get_config()
        
        if window_days is None:
            window_days = config['trend_analysis']['window_days']
        
        threshold_improving = config['thresholds']['trend_improving']
        threshold_declining = config['thresholds']['trend_declining']
        
        call_type_df = df[df['call_type'] == call_type].copy()
        
        if len(call_type_df) == 0:
            return None
        
        # Sort by date descending (newest first)
        call_type_df = call_type_df.sort_values('date', ascending=False)
        
        # Calculate date thresholds
        latest_date = call_type_df['date'].max()
        window_start = latest_date - timedelta(days=window_days)
        previous_window_start = window_start - timedelta(days=window_days)
        
        # Recent period (last N days)
        recent_meetings = call_type_df[call_type_df['date'] >= window_start]
        recent_avg = recent_meetings['sentiment_score'].mean() if len(recent_meetings) > 0 else None
        
        # Previous period (prior N days)
        previous_meetings = call_type_df[
            (call_type_df['date'] >= previous_window_start) & 
            (call_type_df['date'] < window_start)
        ]
        previous_avg = previous_meetings['sentiment_score'].mean() if len(previous_meetings) > 0 else None
        
        # Calculate change and direction
        if recent_avg is not None and previous_avg is not None:
            change = recent_avg - previous_avg
            
            if change > threshold_improving:
                direction = 'improving'
                icon = '📈'
            elif change < threshold_declining:
                direction = 'declining'
                icon = '📉'
            else:
                direction = 'stable'
                icon = '➡️'
        else:
            change = None
            direction = 'unknown'
            icon = '❓'
        
        return {
            'call_type': call_type,
            'recent_avg': recent_avg,
            'previous_avg': previous_avg,
            'change': change,
            'direction': direction,
            'icon': icon,
            'recent_count': len(recent_meetings),
            'previous_count': len(previous_meetings)
        }
    
    @staticmethod
    def _check_at_risk_rule(df, metrics, config):
        """
        Rule 1: At-Risk Call Types
        
        Triggers when sentiment falls below risk threshold (default: 2.5).
        
        Args:
            df (pd.DataFrame): Full dataframe
            metrics (dict): Trend metrics for a call type
            config (dict): Configuration dictionary
            
        Returns:
            dict or None: Insight dict if rule triggers, None otherwise
        """
        risk_threshold = config['thresholds']['risk_threshold']
        
        if not config['insight_rules']['at_risk']['enabled']:
            return None
        
        if metrics['recent_avg'] is None or metrics['recent_avg'] >= risk_threshold:
            return None
        
        pct_below = ((risk_threshold - metrics['recent_avg']) / risk_threshold) * 100
        
        return {
            'icon': '⚠️',
            'priority': config['insight_rules']['at_risk']['priority'],
            'headline': f"{metrics['call_type']} Shows At-Risk Sentiment",
            'metrics': f"Current: {metrics['recent_avg']:.1f}/5.0 ({pct_below:.0f}% below safe threshold)",
            'explanation': f"This indicates dissatisfaction requiring immediate attention. Based on {metrics['recent_count']} meetings in the last {config['trend_analysis']['window_days']} days.",
            'why_matters': f"{metrics['call_type']} calls represent critical customer touchpoints. Low sentiment here correlates with increased churn risk.",
            'action': "Schedule executive check-in calls with affected accounts. Review recent meetings for common pain points."
        }
    
    @staticmethod
    def _check_declining_trend_rule(df, metrics, config):
        """
        Rule 2: Declining Trends
        
        Triggers when sentiment change is less than declining threshold (default: -0.3).
        
        Args:
            df (pd.DataFrame): Full dataframe
            metrics (dict): Trend metrics for a call type
            config (dict): Configuration dictionary
            
        Returns:
            dict or None: Insight dict if rule triggers, None otherwise
        """
        threshold = config['thresholds']['trend_declining']
        
        if not config['insight_rules']['declining_trend']['enabled']:
            return None
        
        if metrics['change'] is None or metrics['change'] >= threshold:
            return None
        
        pct_decline = abs((metrics['change'] / metrics['previous_avg']) * 100) if metrics['previous_avg'] else 0
        
        return {
            'icon': '📉',
            'priority': config['insight_rules']['declining_trend']['priority'],
            'headline': f"{metrics['call_type']} Sentiment Declining",
            'metrics': f"Trend: {metrics['previous_avg']:.1f} → {metrics['recent_avg']:.1f} ({metrics['change']:.1f} points, {pct_decline:.0f}% decline)",
            'explanation': f"Deteriorating experience detected over the past {config['trend_analysis']['window_days']} days across {metrics['recent_count']} meetings.",
            'why_matters': "Declining sentiment often precedes customer escalations and churn. Early intervention is critical.",
            'action': "Analyze recent meeting transcripts for emerging issues. Consider additional training or process improvements."
        }
    
    @staticmethod
    def _check_improving_trend_rule(df, metrics, config):
        """
        Rule 3: Improving Trends
        
        Triggers when sentiment change is greater than improving threshold (default: +0.3).
        
        Args:
            df (pd.DataFrame): Full dataframe
            metrics (dict): Trend metrics for a call type
            config (dict): Configuration dictionary
            
        Returns:
            dict or None: Insight dict if rule triggers, None otherwise
        """
        threshold = config['thresholds']['trend_improving']
        
        if not config['insight_rules']['improving_trend']['enabled']:
            return None
        
        if metrics['change'] is None or metrics['change'] <= threshold:
            return None
        
        pct_improvement = (metrics['change'] / metrics['previous_avg']) * 100 if metrics['previous_avg'] else 0
        
        return {
            'icon': '📈',
            'priority': config['insight_rules']['improving_trend']['priority'],
            'headline': f"{metrics['call_type']} Sentiment Improving",
            'metrics': f"Trend: {metrics['previous_avg']:.1f} → {metrics['recent_avg']:.1f} (+{metrics['change']:.1f} points, {pct_improvement:.0f}% improvement)",
            'explanation': f"Positive momentum detected across {metrics['recent_count']} recent meetings.",
            'why_matters': "Improving sentiment validates recent initiatives and should be reinforced.",
            'action': "Document what's working (processes, people, tools) to replicate across other call types."
        }
    
    @staticmethod
    def _check_outage_detection_rule(df, config):
        """
        Rule 4: Outage Detection
        
        Triggers when multiple conditions are met:
        1. Incident Response meetings exist
        2. Outage-related keywords in topics
        3. Average sentiment below outage threshold
        
        Args:
            df (pd.DataFrame): Full dataframe
            config (dict): Configuration dictionary
            
        Returns:
            dict or None: Insight dict if rule triggers, None otherwise
        """
        if not config['insight_rules']['outage_detection']['enabled']:
            return None
        
        # Filter for Incident Response meetings
        incident_meetings = df[df['category'] == 'Incident Response'].copy()
        
        min_count = config['insight_rules']['outage_detection']['min_incident_count']
        if len(incident_meetings) < min_count:
            return None
        
        incident_meetings = incident_meetings.sort_values('date', ascending=False)
        recent_incidents = incident_meetings.head(5)  # Last 5 incident meetings
        
        avg_incident_sentiment = recent_incidents['sentiment_score'].mean()
        outage_threshold = config['thresholds']['outage_sentiment']
        
        # Check for outage keywords in topics
        outage_keywords = config['insight_rules']['outage_detection']['keywords']
        has_outage = False
        outage_meetings = []
        
        for _, meeting in recent_incidents.iterrows():
            topics = str(meeting.get('topics', '')).lower()
            if any(keyword in topics for keyword in outage_keywords):
                has_outage = True
                outage_meetings.append(meeting)
        
        if not has_outage or avg_incident_sentiment >= outage_threshold:
            return None
        
        # Generate outage insight
        date_range = f"{recent_incidents['date'].min().strftime('%m/%d/%Y')} - {recent_incidents['date'].max().strftime('%m/%d/%Y')}"
        affected_orgs = recent_incidents['organization'].unique()
        incident_count = len(recent_incidents)
        
        churn_pct = config['business_impact']['churn_risk_increase_pct']
        followup_days = config['business_impact']['followup_timeline_days']
        priority_tiers = ', '.join(config['business_impact']['priority_tiers'])
        
        return {
            'icon': '🚨',
            'priority': config['insight_rules']['outage_detection']['priority'],
            'headline': "Outage Event Detected",
            'metrics': f"Period: {date_range} | Incident Meetings: {incident_count} | Avg Sentiment: {avg_incident_sentiment:.1f}/5.0",
            'explanation': f"Multiple incident response meetings with outage-related topics detected. Affected organizations: {', '.join(affected_orgs[:3])}{'...' if len(affected_orgs) > 3 else ''}",
            'why_matters': f"Outages significantly impact customer trust and retention. Historical data shows outages correlate with {churn_pct}% increased churn risk for affected accounts.",
            'action': f"1) Immediate executive calls to {priority_tiers} accounts. 2) Expedite post-mortem and remediation. 3) Schedule customer follow-ups within {followup_days} days."
        }
    
    @staticmethod
    def _check_inconsistent_experience_rule(df, trend_metrics_list, config):
        """
        Rule 5: Inconsistent Experience
        
        Triggers when variance between call types exceeds threshold (default: 1.0).
        
        Args:
            df (pd.DataFrame): Full dataframe
            trend_metrics_list (list): List of trend metrics for all call types
            config (dict): Configuration dictionary
            
        Returns:
            dict or None: Insight dict if rule triggers, None otherwise
        """
        if not config['insight_rules']['inconsistent_experience']['enabled']:
            return None
        
        min_call_types = config['insight_rules']['inconsistent_experience']['min_call_types']
        variance_threshold = config['thresholds']['high_variance']
        
        valid_metrics = [m for m in trend_metrics_list if m and m['recent_avg'] is not None]
        
        if len(valid_metrics) < min_call_types:
            return None
        
        sentiment_values = [m['recent_avg'] for m in valid_metrics]
        variance = max(sentiment_values) - min(sentiment_values)
        
        if variance <= variance_threshold:
            return None
        
        best_call_type = max(valid_metrics, key=lambda x: x['recent_avg'])
        worst_call_type = min(valid_metrics, key=lambda x: x['recent_avg'])
        
        return {
            'icon': '🔄',
            'priority': config['insight_rules']['inconsistent_experience']['priority'],
            'headline': "Inconsistent Experience Across Call Types",
            'metrics': f"Variance: {variance:.1f} points (Best: {best_call_type['call_type']} {best_call_type['recent_avg']:.1f}, Worst: {worst_call_type['call_type']} {worst_call_type['recent_avg']:.1f})",
            'explanation': "Large sentiment gaps suggest fragmented customer experience across different touchpoints.",
            'why_matters': "Customers expect consistent quality regardless of interaction type. Inconsistency erodes trust and satisfaction.",
            'action': f"Analyze what {best_call_type['call_type']} is doing well and apply those practices to {worst_call_type['call_type']}. Consider cross-training teams."
        }
    
    @staticmethod
    def generate_insights(df, trend_metrics_list):
        """
        Generate rule-based insights from sentiment data and trend metrics.
        
        Applies multiple rules to identify:
        1. At-risk call types (sentiment < risk threshold)
        2. Declining trends (change < declining threshold)
        3. Improving trends (change > improving threshold)
        4. Outage events (incident response + sentiment drops)
        5. Inconsistent experiences (high variance across call types)
        
        Rules are configurable via config/sentiment_analysis.yaml and can be
        enabled/disabled individually.
        
        Args:
            df (pd.DataFrame): Full dataframe with all meetings
            trend_metrics_list (list): List of trend metric dicts for each call type
                Each dict should contain call_type, recent_avg, previous_avg, change, etc.
                
        Returns:
            list: List of insight dicts, each containing:
                - icon: Emoji representing insight type
                - priority: critical/high/medium/low
                - headline: Brief summary
                - metrics: Specific numbers and data points
                - explanation: What's happening
                - why_matters: Business context
                - action: Recommended next steps
            Returns empty list if no insights triggered
        """
        config = SentimentAnalyzer.get_config()
        insights = []
        
        # Filter out None values from trend metrics
        valid_metrics = [m for m in trend_metrics_list if m is not None and m.get('recent_avg') is not None]
        
        if len(valid_metrics) == 0 and len(df) > 0:
            # If we have data but no valid metrics, it might be a config issue
            return insights
        
        # Apply individual insight rules for each call type
        for metrics in valid_metrics:
            # Rule 1: At-Risk Detection
            insight = SentimentAnalyzer._check_at_risk_rule(df, metrics, config)
            if insight:
                insights.append(insight)
            
            # Rule 2: Declining Trend
            insight = SentimentAnalyzer._check_declining_trend_rule(df, metrics, config)
            if insight:
                insights.append(insight)
            
            # Rule 3: Improving Trend
            insight = SentimentAnalyzer._check_improving_trend_rule(df, metrics, config)
            if insight:
                insights.append(insight)
        
        # Rule 4: Outage Detection (applied to full dataset)
        insight = SentimentAnalyzer._check_outage_detection_rule(df, config)
        if insight:
            insights.append(insight)
        
        # Rule 5: Inconsistent Experience (requires multiple call types)
        insight = SentimentAnalyzer._check_inconsistent_experience_rule(df, valid_metrics, config)
        if insight:
            insights.append(insight)
        
        # Sort insights by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        insights.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
        
        return insights
