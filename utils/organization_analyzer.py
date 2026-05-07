"""
Organization Analyzer Module for Aegis Transcript Intelligence
=============================================================

This module provides organization-level insights including:
- Sentiment metrics and trends
- Product mentions extraction
- Churn risk assessment
- Renewal status tracking

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class OrganizationAnalyzer:
    """
    Analyzes organization-level metrics and provides business intelligence.
    
    This class provides static methods for analyzing:
    - Sentiment patterns and trends
    - Product usage and mentions
    - Churn risk factors
    - Renewal timing and status
    
    All methods are static as they operate on DataFrames and don't require state.
    """
    
    @staticmethod
    def get_organization_meetings(df, organization):
        """
        Filter meetings for a specific organization, sorted by date (newest first).
        
        Args:
            df (pd.DataFrame): All meetings DataFrame
            organization (str): Organization name to filter
            
        Returns:
            pd.DataFrame: Filtered meetings for the organization
        """
        return df[df['organization'] == organization].sort_values('date', ascending=False)
    
    @staticmethod
    def calculate_sentiment_metrics(org_df):
        """
        Calculate comprehensive sentiment metrics for an organization.
        
        Metrics calculated:
        -------------------
        1. Average sentiment score (1-5 scale)
        2. Sentiment trend (improving/declining/stable)
        3. Sentiment distribution (% positive/neutral/negative)
        
        Trend Logic:
        - Compare average of 3 most recent meetings vs. 3 oldest meetings
        - Improving: Recent > Older + 0.3
        - Declining: Recent < Older - 0.3
        - Stable: Otherwise
        
        Args:
            org_df (pd.DataFrame): Organization's meetings
            
        Returns:
            dict: Sentiment metrics with keys:
                - avg_sentiment: Overall average sentiment score
                - sentiment_trend: 'improving', 'declining', or 'stable'
                - positive_pct: Percentage of positive sentiment meetings
                - neutral_pct: Percentage of neutral sentiment meetings
                - negative_pct: Percentage of negative sentiment meetings
        """
        if len(org_df) == 0:
            return {
                'avg_sentiment': 3.0,
                'sentiment_trend': 'stable',
                'positive_pct': 0,
                'neutral_pct': 0,
                'negative_pct': 0
            }
        
        # Calculate average sentiment across all meetings
        avg_sentiment = org_df['sentiment_score'].mean()
        
        # Calculate trend by comparing recent vs. older meetings
        if len(org_df) >= 3:
            recent_avg = org_df.head(3)['sentiment_score'].mean()
            older_avg = org_df.tail(3)['sentiment_score'].mean()
            
            if recent_avg > older_avg + 0.3:
                trend = 'improving'
            elif recent_avg < older_avg - 0.3:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'  # Not enough data to determine trend
        
        # Calculate sentiment distribution from overall_sentiment field
        total = len(org_df)
        positive_count = org_df['overall_sentiment'].apply(
            lambda x: 'positive' in x.lower() and 'negative' not in x.lower()
        ).sum()
        negative_count = org_df['overall_sentiment'].apply(
            lambda x: 'negative' in x.lower()
        ).sum()
        neutral_count = total - positive_count - negative_count
        
        return {
            'avg_sentiment': round(avg_sentiment, 2),
            'sentiment_trend': trend,
            'positive_pct': round(positive_count / total * 100, 1) if total > 0 else 0,
            'neutral_pct': round(neutral_count / total * 100, 1) if total > 0 else 0,
            'negative_pct': round(negative_count / total * 100, 1) if total > 0 else 0
        }
    
    @staticmethod
    def extract_product_mentions(org_df):
        """
        Extract product mentions from meetings (Detect, Comply, Protect).
        
        Strategy:
        ---------
        1. Scan topics for product names
        2. Scan summary text for product names
        3. Count mentions and collect context examples
        
        Args:
            org_df (pd.DataFrame): Organization's meetings
            
        Returns:
            dict: Product mentions data with keys:
                - counts: Dict mapping product names to mention counts
                - contexts: Dict mapping product names to example contexts (max 3)
                
        Example:
            >>> products = extract_product_mentions(org_df)
            >>> print(products['counts'])
            {'Detect': 8, 'Comply': 3, 'Protect': 0}
        """
        products = {'Detect': 0, 'Comply': 0, 'Protect': 0}
        contexts = {product: [] for product in products.keys()}
        
        for _, meeting in org_df.iterrows():
            # Check topics for product mentions
            # Topics are now comma-separated strings, not lists
            topics_str = meeting['topics']
            if topics_str and topics_str.strip():
                topics_list = [t.strip() for t in topics_str.split(',') if t.strip()]
                for topic in topics_list:
                    for product in products.keys():
                        if product.lower() in topic.lower():
                            products[product] += 1
                            # Keep max 3 example contexts per product
                            if len(contexts[product]) < 3:
                                contexts[product].append({
                                    'title': meeting['title'],
                                    'context': topic,
                                    'date': meeting['date']
                                })
            
            # Check summary text for product mentions
            summary = meeting['summary_text']
            for product in products.keys():
                if product.lower() in summary.lower():
                    products[product] += 1
        
        return {'counts': products, 'contexts': contexts}
    
    @staticmethod
    def calculate_churn_risk(org_df):
        """
        Calculate churn risk score and identify risk factors.
        
        Risk Factors Considered:
        ------------------------
        1. Low recent sentiment (< 2.5 avg in last 3 meetings): +3 points
        2. Moderate recent sentiment (< 3.0 avg): +1 point
        3. Declining sentiment trend: +2 points
        4. Explicit churn signals in key moments: +1 per signal (max +3)
        5. High support ticket volume (> 3 calls): +2 points
        6. Moderate support volume (> 1 call): +1 point
        7. Negative External calls (sentiment < 2.5): +2 points
        
        Risk Levels:
        ------------
        - High: Score >= 7 (immediate executive attention needed)
        - Medium: Score >= 4 (proactive monitoring required)
        - Low: Score < 4 (standard account management)
        
        Args:
            org_df (pd.DataFrame): Organization's meetings (must include category column)
            
        Returns:
            dict: Churn risk assessment with keys:
                - risk_level: 'High', 'Medium', or 'Low'
                - risk_score: Numerical risk score
                - risk_factors: List of identified risk factors (strings)
                - recommendations: List of recommended actions (strings)
        """
        if len(org_df) == 0:
            return {
                'risk_level': 'Low',
                'risk_score': 0,
                'risk_factors': ['No meeting data available'],
                'recommendations': ['Reach out to establish communication']
            }
        
        risk_score = 0
        risk_factors = []
        recommendations = []
        
        # Risk Factor 1: Recent sentiment analysis
        recent_meetings = org_df.head(min(3, len(org_df)))
        recent_sentiment_avg = recent_meetings['sentiment_score'].mean()
        
        if recent_sentiment_avg < 2.5:
            risk_score += 3
            risk_factors.append(f"⚠️ Low recent sentiment (avg: {recent_sentiment_avg:.2f}/5.0)")
            recommendations.append("Schedule executive check-in call immediately")
        elif recent_sentiment_avg < 3.0:
            risk_score += 1
            risk_factors.append(f"⚡ Moderate recent sentiment (avg: {recent_sentiment_avg:.2f}/5.0)")
        
        # Risk Factor 2: Sentiment trend
        sentiment_metrics = OrganizationAnalyzer.calculate_sentiment_metrics(org_df)
        if sentiment_metrics['sentiment_trend'] == 'declining':
            risk_score += 2
            risk_factors.append("📉 Sentiment declining over time")
            recommendations.append("Investigate root causes of dissatisfaction")
        
        # Risk Factor 3: Churn signals from key moments
        import json
        churn_signal_count = 0
        churn_examples = []
        for _, meeting in org_df.iterrows():
            # Parse key_moments from JSON string
            key_moments_str = meeting['key_moments']
            if key_moments_str and key_moments_str.strip() and key_moments_str != '[]':
                try:
                    key_moments_list = json.loads(key_moments_str)
                    for moment in key_moments_list:
                        if moment.get('type') == 'churn_signal':
                            churn_signal_count += 1
                            if len(churn_examples) < 2:
                                churn_examples.append(f"'{moment.get('text', '')[:60]}...'")
                except json.JSONDecodeError:
                    pass  # Skip malformed JSON
        
        if churn_signal_count > 0:
            risk_score += min(churn_signal_count, 3)  # Cap at +3
            examples_str = '; '.join(churn_examples) if churn_examples else ''
            risk_factors.append(
                f"🚨 {churn_signal_count} explicit churn signal(s) detected" +
                (f": {examples_str}" if examples_str else "")
            )
            recommendations.append("Address specific concerns raised in churn signals")
        
        # Risk Factor 4: Support ticket volume
        support_calls = org_df[org_df['call_type'] == 'Customer Support']
        if len(support_calls) > 3:
            risk_score += 2
            risk_factors.append(f"🎫 High support call volume ({len(support_calls)} calls)")
            recommendations.append("Review product quality and support effectiveness")
        elif len(support_calls) > 1:
            risk_score += 1
            risk_factors.append(f"🎫 Moderate support call volume ({len(support_calls)} calls)")
        
        # Risk Factor 5: Negative External calls
        external_calls = org_df[org_df['call_type'] == 'External']
        negative_external = external_calls[external_calls['sentiment_score'] < 2.5]
        if len(negative_external) > 0:
            risk_score += 2
            risk_factors.append(f"📞 {len(negative_external)} negative external call(s)")
            recommendations.append("Review account management strategy")
        
        # Classify risk level based on total score
        if risk_score >= 7:
            risk_level = 'High'
            if "Schedule executive check-in call immediately" not in recommendations:
                recommendations.append("⚠️ Immediate executive intervention required")
        elif risk_score >= 4:
            risk_level = 'Medium'
            if not recommendations:
                recommendations.append("Monitor closely and schedule proactive outreach")
        else:
            risk_level = 'Low'
            if not risk_factors:
                risk_factors.append("✅ No significant risk factors detected")
            if not recommendations:
                recommendations.append("Continue regular account management")
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendations': recommendations
        }
    
    @staticmethod
    def check_renewal_status(org_df):
        """
        Check renewal status and timing for an organization.
        
        Logic:
        ------
        1. Find meetings with renewal keywords in title or category
        2. Determine status based on most recent renewal discussion:
           - Active Discussions: Within last 30 days
           - Recent Activity: 30-90 days ago
           - Due Soon: > 90 days ago or detected but no explicit discussions
           - No Recent Activity: No renewal keywords found
        
        Args:
            org_df (pd.DataFrame): Organization's meetings
            
        Returns:
            dict: Renewal status with keys:
                - status: 'Active Discussions', 'Recent Activity', 'Due Soon', or 'No Recent Activity'
                - last_discussion: Date of last renewal meeting (or None)
                - details: Human-readable description
        """
        renewal_keywords = ['renewal', 'contract', 'pricing', 'negotiate', 'subscription']
        
        # Find meetings with renewal category
        renewal_meetings = org_df[org_df['category'].str.contains('Renewal', case=False, na=False)]
        
        # Also check for renewal keywords in title
        keyword_meetings = org_df[
            org_df['title'].str.lower().str.contains('|'.join(renewal_keywords), na=False)
        ]
        
        # Combine both
        all_renewal_meetings = pd.concat([renewal_meetings, keyword_meetings]).drop_duplicates()
        
        if len(all_renewal_meetings) == 0:
            return {
                'status': 'No Recent Activity',
                'last_discussion': None,
                'details': 'No renewal discussions detected in meeting history'
            }
        
        # Get most recent renewal meeting
        latest_renewal = all_renewal_meetings.iloc[0]  # Already sorted by date desc
        latest_renewal_date = latest_renewal['date']
        
        # Calculate days since last renewal discussion
        # Use timezone-naive datetime to match DataFrame dates
        days_ago = (datetime.now() - latest_renewal_date).days
        
        # Determine status based on recency
        if days_ago <= 30:
            status = 'Active Discussions'
            details = f"Active renewal discussions (last meeting {days_ago} days ago)"
        elif days_ago <= 90:
            status = 'Recent Activity'
            details = f"Renewal discussed {days_ago} days ago - follow-up may be needed"
        else:
            status = 'Due Soon'
            details = f"Last renewal discussion was {days_ago} days ago - likely due for renewal"
        
        return {
            'status': status,
            'last_discussion': latest_renewal_date,
            'details': details,
            'days_since_discussion': days_ago
        }


# Self-test code (runs when module is executed directly)
if __name__ == "__main__":
    print("Testing organization analyzer...")
    
    # Import required modules
    from data_loader import load_all_meetings
    from rule_based_categorizer import RuleBasedCategorizer
    
    try:
        # Load and categorize data
        print("Loading data...")
        dataset_path = "dataset"
        df = load_all_meetings(dataset_path)
        
        print("Categorizing meetings...")
        categorizer = RuleBasedCategorizer()
        df = categorizer.categorize_dataframe(df)
        
        # Get list of organizations (exclude Internal)
        analyzer = OrganizationAnalyzer()
        orgs = df[df['organization'] != 'Internal']['organization'].unique()
        
        print(f"\n🏢 Found {len(orgs)} organizations")
        
        if len(orgs) > 0:
            # Test with first organization
            test_org = orgs[0]
            print(f"\n📊 Analyzing: {test_org}")
            print("=" * 60)
            
            org_df = analyzer.get_organization_meetings(df, test_org)
            print(f"📅 Meetings: {len(org_df)}")
            
            sentiment = analyzer.calculate_sentiment_metrics(org_df)
            print(f"\n💭 Sentiment:")
            print(f"  Average: {sentiment['avg_sentiment']}/5.0")
            print(f"  Trend: {sentiment['sentiment_trend']}")
            print(f"  Distribution: {sentiment['positive_pct']}% pos, "
                  f"{sentiment['neutral_pct']}% neu, {sentiment['negative_pct']}% neg")
            
            products = analyzer.extract_product_mentions(org_df)
            print(f"\n📦 Products:")
            for product, count in products['counts'].items():
                print(f"  {product}: {count} mentions")
            
            risk = analyzer.calculate_churn_risk(org_df)
            print(f"\n⚠️  Churn Risk: {risk['risk_level']} (Score: {risk['risk_score']})")
            print(f"  Factors:")
            for factor in risk['risk_factors']:
                print(f"    • {factor}")
            print(f"  Recommendations:")
            for rec in risk['recommendations']:
                print(f"    ✓ {rec}")
            
            renewal = analyzer.check_renewal_status(org_df)
            print(f"\n🔄 Renewal Status: {renewal['status']}")
            print(f"  {renewal['details']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
