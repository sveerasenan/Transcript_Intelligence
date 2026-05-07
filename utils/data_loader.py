"""
Data Loader Module for Aegis Transcript Intelligence
====================================================

This module extracts and normalizes meeting data from JSON files across all dataset folders.

Key Functions:
- load_all_meetings(): Main entry point to load all meeting data into a DataFrame
- extract_organization(): Extracts company name from meeting titles
- derive_call_type(): Determines if call is Customer Support, External, or Internal

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import os
import json
import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime
import re


def load_organization_mapping():
    """
    Load organization name mapping from organizations.yaml.
    
    Returns:
        dict: Mapping configuration with canonical names and keywords
    """
    config_path = Path(__file__).parent.parent / 'config' / 'organizations.yaml'
    
    if not config_path.exists():
        print("⚠️  organizations.yaml not found, using raw organization names")
        return {'organizations': {}}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️  Error loading organizations.yaml: {e}")
        return {'organizations': {}}


def normalize_organization_name(raw_org_name, org_mapping=None):
    """
    Normalize organization name using mapping configuration.
    
    Matches raw organization name against keywords in organizations.yaml
    and returns the canonical name.
    
    Args:
        raw_org_name (str): Raw organization name extracted from title/email
        org_mapping (dict): Organization mapping config (loaded from YAML)
        
    Returns:
        str: Canonical organization name
        
    Examples:
        >>> normalize_organization_name("blackridgeinvest", mapping)
        'Blackridge Investments'
        >>> normalize_organization_name("blackridge investments custom", mapping)
        'Blackridge Investments'
    """
    if not org_mapping:
        org_mapping = load_organization_mapping()
    
    raw_org_lower = raw_org_name.lower().strip()
    
    # Check each canonical organization
    for canonical_name, config in org_mapping.get('organizations', {}).items():
        keywords = config.get('keywords', [])
        
        # Check if raw name matches any keyword
        for keyword in keywords:
            if keyword.lower() in raw_org_lower or raw_org_lower in keyword.lower():
                return canonical_name
    
    # Check special mappings
    if raw_org_lower == 'internal':
        return 'Internal'
    
    if raw_org_lower in ['unknown', '']:
        return 'Unknown'
    
    # No mapping found, return original with title case
    return raw_org_name.title() if raw_org_name else 'Unknown'


def extract_organization(title, all_emails):
    """
    Extract organization name from meeting title using pattern matching.
    
    Strategy:
    1. Look for "Aegis / Organization" pattern in title
    2. Look for "Support Case #... - Organization" pattern
    3. Check if all emails are internal (return 'Internal')
    4. Extract from external email domain as fallback
    
    Args:
        title (str): Meeting title from meeting-info.json
        all_emails (list): List of participant email addresses
        
    Returns:
        str: Organization name or 'Internal' if no external organization
        
    Examples:
        >>> extract_organization("Aegis / Steelpoint Manufacturing - Contract Review", [...])
        'Steelpoint Manufacturing'
        
        >>> extract_organization("Support Case #9279 - Summit Trust Billing Inquiry", [...])
        'Summit Trust'
    """
    # Pattern 1: "Aegis / Organization - ..."
    match = re.search(r'Aegis\s*/\s*([^-]+)', title)
    if match:
        org_name = match.group(1).strip()
        return org_name
    
    # Pattern 2: "Support Case #... - Organization ..."
    match = re.search(r'Support Case #\d+\s*-\s*([A-Z][a-zA-Z\s]+)', title)
    if match:
        org_name = match.group(1).strip()
        # Extract just the organization name (first 1-3 capitalized words)
        words = org_name.split()
        org_words = []
        for word in words:
            if word[0].isupper():
                org_words.append(word)
            else:
                break
        return ' '.join(org_words[:3]) if org_words else "Unknown"
    
    # Pattern 3: Check if all emails are internal
    external_emails = [e for e in all_emails if 'aegiscloud.com' not in e.lower()]
    if not external_emails:
        return "Internal"
    
    # Pattern 4: Extract from external email domain
    if external_emails:
        domain = external_emails[0].split('@')[1] if '@' in external_emails[0] else ""
        if domain:
            # Convert domain to company name
            # e.g., steelpointmfg.com -> Steelpoint
            # e.g., summittrust.com -> Summit Trust
            company = domain.split('.')[0]
            company = company.replace('mfg', '').replace('corp', '').strip()
            # Add spaces before capital letters (camelCase)
            company = re.sub(r'([a-z])([A-Z])', r'\1 \2', company)
            return company.title() if company else "Unknown"
    
    return "Unknown"


def derive_call_type(title, all_emails):
    """
    Derive call type based on meeting title and participant email composition.
    
    Logic:
    1. Customer Support: Title contains "Support Case #"
    2. Internal: All participants are @aegiscloud.com
    3. External: Mix of internal and customer emails
    
    Args:
        title (str): Meeting title from meeting-info.json
        all_emails (list): List of participant email addresses
        
    Returns:
        str: One of 'Customer Support', 'External', 'Internal', or 'Unknown'
        
    Examples:
        >>> derive_call_type("Support Case #9279 - Billing", [...])
        'Customer Support'
        
        >>> derive_call_type("Quarterly Planning", ["user1@aegiscloud.com", "user2@aegiscloud.com"])
        'Internal'
        
        >>> derive_call_type("Renewal Discussion", ["am@aegiscloud.com", "client@company.com"])
        'External'
    """
    # Rule 1: Support Case in title = Customer Support
    if 'Support Case #' in title or 'Support Case#' in title:
        return "Customer Support"
    
    # Count internal vs external emails
    internal_count = sum(1 for e in all_emails if 'aegiscloud.com' in e.lower())
    external_count = len(all_emails) - internal_count
    
    # Rule 2: All internal emails = Internal call
    if external_count == 0 and internal_count > 0:
        return "Internal"
    
    # Rule 3: Mix of internal and external = External call
    if external_count > 0:
        return "External"
    
    return "Unknown"


def load_meeting_data(meeting_folder):
    """
    Load all JSON files from a single meeting folder and combine into one dict.
    
    Files loaded:
    - meeting-info.json: Meeting metadata, participants, timestamps
    - summary.json: AI-generated summary, sentiment, topics, action items
    - transcript.json: Sentence-level transcript with sentiment (optional)
    
    Args:
        meeting_folder (Path): Path to meeting folder (e.g., dataset/01KQ03B...)
        
    Returns:
        dict: Combined meeting data with all fields, or None if loading fails
        
    Dictionary keys:
        - meetingId: Unique meeting identifier
        - title: Meeting title
        - date: Meeting start time (ISO format)
        - duration: Meeting duration in minutes
        - all_emails: List of all participant emails
        - participants: List of invitees
        - overall_sentiment: Overall sentiment label (positive/negative/mixed/neutral)
        - sentiment_score: Numerical sentiment score (typically 1-5 scale)
        - summary_text: Meeting summary text
        - topics: List of topics discussed
        - action_items: List of action items with assignees
        - key_moments: List of important moments (churn signals, technical issues, etc.)
        - transcript: Full transcript data (sentence-level)
        - organization: Derived organization name
        - call_type: Derived call type
    """
    try:
        # Load meeting-info.json
        with open(meeting_folder / 'meeting-info.json', 'r', encoding='utf-8') as f:
            meeting_info = json.load(f)
        
        # Load summary.json
        with open(meeting_folder / 'summary.json', 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        # Load transcript.json (optional - for future use)
        transcript_path = meeting_folder / 'transcript.json'
        transcript = None
        if transcript_path.exists():
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
                transcript = transcript_data.get('data', [])
        
        # Combine all data into single dictionary
        combined_data = {
            'meetingId': meeting_info.get('meetingId', ''),
            'title': meeting_info.get('title', ''),
            'date': meeting_info.get('startTime', ''),
            'duration': meeting_info.get('duration', 0),
            'all_emails': meeting_info.get('allEmails', []),
            'participants': meeting_info.get('invitees', []),
            'overall_sentiment': summary.get('overallSentiment', 'neutral'),
            'sentiment_score': summary.get('sentimentScore', 3.0),
            'summary_text': summary.get('summary', ''),
            'topics': summary.get('topics', []),
            'action_items': summary.get('actionItems', []),
            'key_moments': summary.get('keyMoments', []),
            'transcript': transcript
        }
        
        # Derive additional fields using helper functions
        combined_data['organization'] = extract_organization(
            combined_data['title'], 
            combined_data['all_emails']
        )
        combined_data['call_type'] = derive_call_type(
            combined_data['title'],
            combined_data['all_emails']
        )
        
        return combined_data
        
    except Exception as e:
        print(f"⚠️  Error loading {meeting_folder.name}: {str(e)}")
        return None


def load_all_meetings(dataset_path):
    """
    Load all meetings from the dataset directory into a pandas DataFrame.
    
    This is the main entry point for data loading. It:
    1. Scans the dataset directory for meeting folders
    2. Loads each meeting's JSON files
    3. Combines into a single DataFrame
    4. Converts dates to datetime objects
    5. Sorts by date (newest first)
    
    Args:
        dataset_path (str): Path to dataset directory containing meeting folders
                           (e.g., "dataset" or "/full/path/to/dataset")
        
    Returns:
        pd.DataFrame: DataFrame with all meeting data, one row per meeting
        
    Raises:
        FileNotFoundError: If dataset_path does not exist
        
    DataFrame columns:
        - meetingId, title, date, duration, organization, call_type
        - overall_sentiment, sentiment_score
        - all_emails, participants, topics, action_items, key_moments
        - summary_text, transcript
        
    Example:
        >>> df = load_all_meetings("dataset")
        Found 100 meeting folders. Loading...
        Successfully loaded 100 meetings.
        >>> print(df.shape)
        (100, 14)
    """
    dataset_dir = Path(dataset_path)
    
    # Validate dataset path exists
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset path not found: {dataset_path}")
    
    # Get all subdirectories (each is a meeting folder)
    meeting_folders = [f for f in dataset_dir.iterdir() if f.is_dir() and not f.name.startswith('.')]
    
    print(f"📁 Found {len(meeting_folders)} meeting folders. Loading...")
    
    meetings_data = []
    errors = []
    
    # Load each meeting
    for folder in meeting_folders:
        data = load_meeting_data(folder)
        if data:
            meetings_data.append(data)
        else:
            errors.append(folder.name)
    
    print(f"✅ Successfully loaded {len(meetings_data)} meetings.")
    if errors:
        print(f"⚠️  Failed to load {len(errors)} meetings: {', '.join(errors[:5])}{'...' if len(errors) > 5 else ''}")
    
    # Convert to DataFrame
    df = pd.DataFrame(meetings_data)
    
    # Convert date string to datetime object for easier filtering/sorting
    # Remove timezone information to avoid tz-naive vs tz-aware comparison errors
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    
    # Normalize organization names using mapping
    print("🏢 Normalizing organization names...")
    org_mapping = load_organization_mapping()
    df['organization'] = df['organization'].apply(
        lambda x: normalize_organization_name(x, org_mapping)
    )
    
    # Convert list columns to strings to avoid pandas hashing errors
    # These columns need to be converted because pandas cannot hash lists
    
    # Simple list columns - convert to comma-separated strings
    simple_list_columns = ['all_emails', 'participants', 'topics', 'action_items']
    for col in simple_list_columns:
        if col in df.columns:
            # Convert list to comma-separated string, handle empty lists
            df[col] = df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) and x else '')
    
    # Complex list columns (containing dicts) - convert to JSON strings
    import json
    if 'key_moments' in df.columns:
        df['key_moments'] = df['key_moments'].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else '[]'
        )
    
    # Keep transcript as JSON string since it's large
    if 'transcript' in df.columns:
        df['transcript'] = df['transcript'].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else '[]'
        )
    
    # Sort by date (newest first)
    df = df.sort_values('date', ascending=False).reset_index(drop=True)
    
    return df


# Self-test code (runs when module is executed directly)
if __name__ == "__main__":
    print("Testing data loader...")
    
    # Test with dataset path
    dataset_path = "dataset"
    
    try:
        df = load_all_meetings(dataset_path)
        print(f"\n📊 DataFrame shape: {df.shape}")
        print(f"📋 Columns: {df.columns.tolist()}")
        print(f"\n📅 Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"\n🏢 Organizations: {df['organization'].nunique()} unique")
        print(f"\n📞 Call types:\n{df['call_type'].value_counts()}")
        print(f"\n🎯 Sample data:\n{df[['title', 'organization', 'call_type', 'overall_sentiment']].head()}")
    except Exception as e:
        print(f"❌ Error: {e}")
