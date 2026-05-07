"""
Rule-Based Categorizer Module for Aegis Transcript Intelligence
===============================================================

This module implements a keyword-based scoring system to categorize meetings
into predefined categories based on title, topics, and summary content.

Algorithm:
1. For each category, calculate a score based on keyword matches
2. Apply different weights to matches in title (highest), topics (medium), summary (lowest)
3. Apply sentiment boost for certain categories when sentiment is negative
4. Check requirements (e.g., customer emails required for External categories)
5. Assign the category with the highest score

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import yaml
from pathlib import Path
import pandas as pd


class RuleBasedCategorizer:
    """
    Categorizes meetings using keyword-based scoring algorithm.
    
    This class loads category definitions from a YAML config file and
    provides methods to score and categorize individual meetings or
    entire DataFrames of meetings.
    
    Attributes:
        categories (dict): Category definitions loaded from YAML config
        
    Example:
        >>> categorizer = RuleBasedCategorizer('config/categories.yaml')
        >>> result = categorizer.categorize_meeting(meeting_data)
        >>> print(result['category'], result['category_score'])
        'Customer Support' 12
    """
    
    def __init__(self, config_path='config/categories.yaml'):
        """
        Initialize categorizer with configuration file.
        
        Args:
            config_path (str): Path to YAML file containing category definitions
                              Default: 'config/categories.yaml'
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.categories = config['categories']
        print(f"✅ Loaded {len(self.categories)} category definitions")
    
    def score_category(self, meeting_data, category_key, category_config):
        """
        Calculate score for a specific category based on keyword matches.
        
        Scoring Logic:
        --------------
        1. Title matches: weight × 3 (most important)
        2. Topic matches: weight × 2 (medium importance)
        3. Summary matches: weight × 1 (least important)
        4. Sentiment boost: +N points if sentiment is negative (for applicable categories)
        5. Requirements check: Score set to 0 if requirements not met
        
        Args:
            meeting_data (dict): Meeting data dictionary with keys:
                                - title, topics, summary_text, sentiment_score, all_emails
            category_key (str): Category identifier (e.g., 'customer_support')
            category_config (dict): Category configuration with keywords, weights, requirements
            
        Returns:
            tuple: (score (int), keyword_matches (dict))
                  - score: Total points for this category
                  - keyword_matches: Dict mapping keywords to their contribution scores
                  
        Example:
            >>> score, matches = categorizer.score_category(meeting_data, 'customer_support', config)
            >>> print(f"Score: {score}, Matches: {matches}")
            Score: 12, Matches: {'Support Case': 3, 'issue': 3, 'billing': 2}
        """
        score = 0
        keyword_matches = {}
        
        # Get weights from config (with defaults)
        weights = category_config.get('weights', {})
        title_weight = weights.get('title', 2)
        topics_weight = weights.get('topics', 2)
        summary_weight = weights.get('summary', 1)
        
        # Normalize text fields to lowercase for case-insensitive matching
        title = meeting_data.get('title', '').lower()
        
        # Topics are now comma-separated strings, not lists
        topics_str = meeting_data.get('topics', '')
        if topics_str and topics_str.strip():
            topics = [t.lower().strip() for t in topics_str.split(',') if t.strip()]
        else:
            topics = []
        
        summary = meeting_data.get('summary_text', '').lower()
        
        # Score each keyword across all text fields
        for keyword in category_config.get('keywords', []):
            keyword_lower = keyword.lower()
            
            # Check title for keyword
            if keyword_lower in title:
                score += title_weight
                keyword_matches[keyword] = keyword_matches.get(keyword, 0) + title_weight
            
            # Check each topic for keyword
            for topic in topics:
                if keyword_lower in topic:
                    score += topics_weight
                    keyword_matches[keyword] = keyword_matches.get(keyword, 0) + topics_weight
            
            # Check summary for keyword
            if keyword_lower in summary:
                score += summary_weight
                keyword_matches[keyword] = keyword_matches.get(keyword, 0) + summary_weight
        
        # Parse all_emails once for requirements and boost checks
        # Handle both string (comma-separated) and list formats
        all_emails_raw = meeting_data.get('all_emails', [])
        if isinstance(all_emails_raw, str):
            all_emails = [e.strip() for e in all_emails_raw.split(',') if e.strip()]
        else:
            all_emails = all_emails_raw
        
        external_emails = [e for e in all_emails if 'aegiscloud.com' not in e.lower()]
        
        # Apply sentiment boost if configured (for Incident Response, Escalation, etc.)
        if category_config.get('sentiment_boost', False):
            sentiment_score = meeting_data.get('sentiment_score', 3.0)
            if sentiment_score < 2.5:  # Threshold for negative sentiment
                boost = category_config.get('boost_value', 2)
                score += boost
                keyword_matches['[Negative Sentiment Boost]'] = boost
        
        # Apply internal boost if configured (for Internal Planning, etc.)
        # This gives a bonus to internal-only categories when all participants are internal
        if category_config.get('internal_boost', False):
            if not external_emails and all_emails:  # All internal
                boost = category_config.get('boost_value', 3)
                score += boost
                keyword_matches['[Internal Meeting Boost]'] = boost
        
        # Apply renewal boost if configured (for External - Renewal)
        # This gives a bonus when "renewal" keyword appears in the title
        if category_config.get('renewal_boost', False):
            title = meeting_data.get('title', '').lower()
            if 'renewal' in title:
                boost = category_config.get('boost_value', 10)
                score += boost
                keyword_matches['[Renewal Title Boost]'] = boost
        
        # Apply churn risk boost if configured (for Escalation)
        # This gives a bonus when "churn" appears in topics
        if category_config.get('churn_risk_boost', False):
            topics_str = meeting_data.get('topics', '').lower()
            if 'churn' in topics_str:
                boost = category_config.get('churn_boost_value', 8)
                score += boost
                keyword_matches['[Churn Risk Boost]'] = boost
        
        # Check requirements and disqualify if not met
        
        # Requirement: Must have customer emails
        if category_config.get('requires_customer', False):
            if not external_emails:
                score = 0  # Disqualify - no customer present
        
        # Requirement: Must be internal-only
        if category_config.get('requires_internal_only', False):
            if external_emails:
                score = 0  # Disqualify - customer emails present
        
        return score, keyword_matches
    
    def categorize_meeting(self, meeting_data):
        """
        Categorize a single meeting by scoring all categories and selecting the best match.
        
        Process:
        --------
        1. Score all categories
        2. Select category with highest score
        3. Calculate confidence based on score distribution
        4. Generate detailed explanation of categorization logic
        
        Args:
            meeting_data (dict or pd.Series): Meeting data with required fields
            
        Returns:
            dict: Categorization result with keys:
                - category (str): Best matching category name
                - category_score (int): Score for the selected category
                - confidence (str): 'High', 'Medium', or 'Low'
                - keyword_matches (dict): Keywords that contributed to score
                - explanation (str): Detailed explanation for comments field
                
        Confidence Levels:
            - High: >70% of total score (clear winner)
            - Medium: 50-70% of total score (reasonable match)
            - Low: <50% of total score (ambiguous)
        """
        category_scores = {}
        category_matches = {}
        
        # CRITICAL OVERRIDE: Check for negative sentiment escalation first
        # If sentiment is mixed-negative or very-negative, force escalation category
        overall_sentiment = meeting_data.get('overall_sentiment', '').lower()
        negative_sentiments = ['mixed-negative', 'very-negative', 'negative']
        
        if overall_sentiment in negative_sentiments:
            # Check if escalation category has negative_sentiment_override enabled
            escalation_config = self.categories.get('escalation', {})
            if escalation_config.get('negative_sentiment_override', False):
                # Force escalation category - bypass normal scoring
                score, matches = self.score_category(meeting_data, 'escalation', escalation_config)
                # Add override indicator to matches
                matches['[NEGATIVE SENTIMENT OVERRIDE]'] = 999
                return {
                    'category': escalation_config.get('name', 'Escalation'),
                    'category_score': score + 999,  # Add override weight
                    'confidence': 'High',
                    'keyword_matches': matches,
                    'explanation': f"🚨 OVERRIDE: {overall_sentiment.upper()} sentiment detected. Auto-escalated regardless of other factors."
                }
        
        # Score all categories (normal path)
        for cat_key, cat_config in self.categories.items():
            score, matches = self.score_category(meeting_data, cat_key, cat_config)
            if score > 0:
                category_scores[cat_key] = score
                category_matches[cat_key] = matches
        
        # Fallback: If no category matched, use call_type as default
        if not category_scores:
            call_type = meeting_data.get('call_type', 'Unknown')
            return {
                'category': f"{call_type} (Uncategorized)",
                'category_score': 0,
                'confidence': 'Low',
                'keyword_matches': {},
                'explanation': f"No keywords matched. Defaulted to call type: {call_type}."
            }
        
        # Select best category (highest score)
        best_category_key = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category_key]
        best_matches = category_matches[best_category_key]
        
        # Calculate confidence based on score distribution
        total_score = sum(category_scores.values())
        confidence_pct = (best_score / total_score * 100) if total_score > 0 else 0
        
        if confidence_pct >= 70:
            confidence = 'High'
        elif confidence_pct >= 50:
            confidence = 'Medium'
        else:
            confidence = 'Low'
        
        # Get category display name
        category_name = self.categories[best_category_key]['name']
        
        # Build detailed explanation for comments field
        # Format: "Category: X | Score: Y | Confidence: Z (%) | Matched keywords: ..."
        matched_keywords_str = ', '.join([f"{k} ({v})" for k, v in best_matches.items()])
        explanation = (
            f"Category: {category_name} | Score: {best_score} | "
            f"Confidence: {confidence} ({confidence_pct:.1f}%) | "
            f"Matched keywords: {matched_keywords_str}"
        )
        
        # Add information about competing categories if close matches exist
        competitors = [
            (k, v) for k, v in category_scores.items() 
            if k != best_category_key and v >= best_score * 0.7
        ]
        if competitors:
            comp_names = ', '.join([
                f"{self.categories[k]['name']} ({v})" 
                for k, v in competitors
            ])
            explanation += f" | Also considered: {comp_names}"
        
        return {
            'category': category_name,
            'category_score': best_score,
            'confidence': confidence,
            'keyword_matches': best_matches,
            'explanation': explanation
        }
    
    def categorize_dataframe(self, df):
        """
        Categorize all meetings in a DataFrame.
        
        This method applies categorization to each row in parallel and
        adds new columns: category, category_score, confidence, comments
        
        Args:
            df (pd.DataFrame): DataFrame with meeting data
                              Must contain columns: title, topics, summary_text,
                              sentiment_score, all_emails, call_type
            
        Returns:
            pd.DataFrame: DataFrame with added columns:
                         - category: Assigned category name
                         - category_score: Numerical score
                         - confidence: High/Medium/Low
                         - comments: Detailed explanation
                         
        Example:
            >>> df = load_all_meetings('dataset')
            >>> categorizer = RuleBasedCategorizer()
            >>> df = categorizer.categorize_dataframe(df)
            >>> print(df['category'].value_counts())
            Customer Support        25
            External - Review       18
            Internal Planning       15
            ...
        """
        print(f"🔄 Categorizing {len(df)} meetings...")
        
        # Apply categorization to each row
        # Using apply with lambda to convert each row to dict
        results = df.apply(lambda row: self.categorize_meeting(row.to_dict()), axis=1)
        
        # Extract fields from results into separate columns
        df['category'] = results.apply(lambda x: x['category'])
        df['category_score'] = results.apply(lambda x: x['category_score'])
        df['confidence'] = results.apply(lambda x: x['confidence'])
        df['comments'] = results.apply(lambda x: x['explanation'])
        
        print(f"✅ Categorization complete!")
        print(f"\n📊 Category distribution:")
        print(df['category'].value_counts().to_string())
        
        return df


# Self-test code (runs when module is executed directly)
if __name__ == "__main__":
    print("Testing rule-based categorizer...")
    
    # Import data loader to test with real data
    from data_loader import load_all_meetings
    
    try:
        # Load data
        dataset_path = "dataset"
        df = load_all_meetings(dataset_path)
        
        # Initialize categorizer
        categorizer = RuleBasedCategorizer()
        
        # Categorize all meetings
        df = categorizer.categorize_dataframe(df)
        
        # Show results
        print(f"\n📋 Sample categorizations:")
        sample_cols = ['title', 'category', 'category_score', 'confidence']
        print(df[sample_cols].head(10).to_string())
        
        print(f"\n💯 Confidence distribution:")
        print(df['confidence'].value_counts().to_string())
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
