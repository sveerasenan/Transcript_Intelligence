"""
LLM Utilities Module for Aegis Transcript Intelligence
=======================================================

This module provides utility functions for:
- PII detection and redaction
- Data tokenization for LLM consumption
- Privacy guardrails and compliance
- Transcript truncation and formatting

Author: Aegis Transcript Intelligence Team
Date: 2026-05-07
"""

import re
import json
from typing import Dict, Any, List
from pathlib import Path
import yaml


class LLMDataTokenizer:
    """
    Handles tokenization and PII removal from meeting data before sending to LLM.
    
    Ensures compliance with privacy policies by:
    - Redacting emails, phone numbers, IP addresses
    - Replacing person names with role-based tokens (Agent, Customer)
    - Replacing organization names with generic tokens (ORG-A, ORG-B)
    - Truncating long transcripts to fit model context windows
    """
    
    # Regex patterns for PII detection
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}'
    IP_PATTERN = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    
    def __init__(self, config_path: str = None):
        """
        Initialize tokenizer with configuration.
        
        Args:
            config_path (str, optional): Path to llm.yaml config file.
                Defaults to config/llm.yaml relative to project root.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'llm.yaml'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.privacy_config = self.config.get('privacy', {})
        self.max_transcript_length = self.privacy_config.get('max_transcript_length', 15000)
        self.truncation_strategy = self.privacy_config.get('truncation_strategy', 'middle')
    
    def redact_email(self, text: str) -> str:
        """
        Redact email addresses from text.
        
        Args:
            text (str): Input text
            
        Returns:
            str: Text with emails replaced with [EMAIL]
        """
        return re.sub(self.EMAIL_PATTERN, '[EMAIL]', text)
    
    def redact_phone(self, text: str) -> str:
        """
        Redact phone numbers from text.
        
        Args:
            text (str): Input text
            
        Returns:
            str: Text with phone numbers replaced with [PHONE]
        """
        return re.sub(self.PHONE_PATTERN, '[PHONE]', text)
    
    def redact_ip(self, text: str) -> str:
        """
        Redact IP addresses from text.
        
        Args:
            text (str): Input text
            
        Returns:
            str: Text with IPs replaced with [IP_ADDRESS]
        """
        return re.sub(self.IP_PATTERN, '[IP_ADDRESS]', text)
    
    def tokenize_speaker_names(self, transcript_data: List[Dict]) -> List[Dict]:
        """
        Replace speaker names with role-based tokens.
        
        Identifies internal (agent) vs external (customer) speakers based on
        email domain and replaces names with Agent-1, Agent-2, Customer-1, etc.
        
        Args:
            transcript_data (list): List of transcript sentence dicts
            
        Returns:
            list: Transcript with tokenized speaker names
        """
        # Create speaker mapping
        speaker_map = {}
        agent_count = 0
        customer_count = 0
        
        for entry in transcript_data:
            speaker_id = entry.get('speaker_id')
            speaker_name = entry.get('speaker_name', '')
            
            if speaker_id not in speaker_map:
                # Check if internal speaker (simple heuristic: contains @aegiscloud.com in name)
                # In production, this would use the meeting metadata
                if 'aegis' in speaker_name.lower() or speaker_id == 0:
                    agent_count += 1
                    speaker_map[speaker_id] = f"Agent-{agent_count}"
                else:
                    customer_count += 1
                    speaker_map[speaker_id] = f"Customer-{customer_count}"
        
        # Replace speaker names in transcript
        tokenized_transcript = []
        for entry in transcript_data:
            tokenized_entry = entry.copy()
            speaker_id = entry.get('speaker_id')
            tokenized_entry['speaker_name'] = speaker_map.get(speaker_id, f"Speaker-{speaker_id}")
            tokenized_transcript.append(tokenized_entry)
        
        return tokenized_transcript
    
    def truncate_transcript(self, transcript_text: str) -> str:
        """
        Truncate transcript to fit within max length using configured strategy.
        
        Args:
            transcript_text (str): Full transcript text
            
        Returns:
            str: Truncated transcript with indicator if truncation occurred
        """
        if len(transcript_text) <= self.max_transcript_length:
            return transcript_text
        
        if self.truncation_strategy == "start":
            # Keep beginning
            truncated = transcript_text[:self.max_transcript_length]
            return truncated + "\n\n[TRANSCRIPT TRUNCATED - SHOWING BEGINNING]"
        
        elif self.truncation_strategy == "end":
            # Keep ending
            truncated = transcript_text[-self.max_transcript_length:]
            return "[TRANSCRIPT TRUNCATED - SHOWING END]\n\n" + truncated
        
        else:  # "middle" (default)
            # Keep beginning and end, remove middle
            keep_length = self.max_transcript_length // 2
            beginning = transcript_text[:keep_length]
            ending = transcript_text[-keep_length:]
            return beginning + "\n\n[MIDDLE PORTION TRUNCATED]\n\n" + ending
    
    def format_transcript_for_llm(self, transcript_data: List[Dict]) -> str:
        """
        Format transcript data into readable text for LLM.
        
        Args:
            transcript_data (list): List of transcript sentence dicts
            
        Returns:
            str: Formatted transcript text
        """
        lines = []
        for entry in transcript_data:
            speaker = entry.get('speaker_name', 'Unknown')
            text = entry.get('sentence', '')
            time = entry.get('time', 0)
            sentiment = entry.get('sentimentType', 'neutral')
            
            # Format: [MM:SS] Speaker (sentiment): Text
            minutes = int(time // 60)
            seconds = int(time % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            lines.append(f"[{time_str}] {speaker} ({sentiment}): {text}")
        
        return "\n".join(lines)
    
    def redact_organization_names(self, text: str, org_list: List[str]) -> str:
        """
        Replace organization names with generic tokens.
        
        Args:
            text (str): Input text
            org_list (list): List of organization names to redact
            
        Returns:
            str: Text with org names replaced with ORG-A, ORG-B, etc.
        """
        org_map = {}
        for idx, org_name in enumerate(org_list):
            if org_name not in org_map:
                org_map[org_name] = f"ORG-{chr(65 + idx)}"  # ORG-A, ORG-B, etc.
        
        # Replace organization names (case insensitive)
        for org_name, token in org_map.items():
            text = re.sub(re.escape(org_name), token, text, flags=re.IGNORECASE)
        
        return text
    
    def optimize_text_for_llm(self, text: str) -> str:
        """
        Optimize text to reduce token usage by removing filler words and compressing phrases.
        
        Optimizations applied:
        - Remove common filler words (actually, basically, really, etc.)
        - Compress verbose phrases ("in order to" -> "to")
        - Remove redundant whitespace
        - Preserve important context and readability
        
        Args:
            text (str): Input text to optimize
            
        Returns:
            str: Optimized text with reduced token count (~10-20% reduction)
        """
        if not self.config.get('text_optimization', {}).get('enabled', True):
            return text
        
        original_length = len(text)
        
        # Step 1: Compress verbose phrases (must do before word removal)
        if self.config.get('text_optimization', {}).get('compress_phrases', True):
            phrase_compressions = self.config.get('text_optimization', {}).get('phrase_compressions', {})
            for verbose_phrase, compressed in phrase_compressions.items():
                # Case-insensitive replacement
                text = re.sub(re.escape(verbose_phrase), compressed, text, flags=re.IGNORECASE)
        
        # Step 2: Remove filler words
        if self.config.get('text_optimization', {}).get('remove_filler_words', True):
            filler_words = self.config.get('text_optimization', {}).get('filler_words', [])
            
            for filler in filler_words:
                # Remove filler words with word boundaries to avoid partial matches
                # Examples: "really" won't match "reality", "just" won't match "justice"
                pattern = r'\b' + re.escape(filler) + r'\b'
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Step 3: Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces -> single space
        text = re.sub(r'\s*,\s*', ', ', text)  # Clean comma spacing
        text = re.sub(r'\s*\.\s*', '. ', text)  # Clean period spacing
        text = text.strip()
        
        # Log optimization results (optional)
        optimized_length = len(text)
        reduction_pct = ((original_length - optimized_length) / original_length * 100) if original_length > 0 else 0
        
        if reduction_pct > 1:  # Only log if meaningful reduction
            print(f"📊 Text optimization: {original_length} -> {optimized_length} chars ({reduction_pct:.1f}% reduction)")
        
        return text
    
    def tokenize_meeting_data(
        self, 
        meeting_info: Dict[str, Any],
        summary_data: Dict[str, Any],
        transcript_data: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Tokenize and sanitize meeting data for LLM consumption.
        
        Applies privacy guardrails:
        - Redacts PII (emails, phones, IPs)
        - Redacts organization names
        - Extracts only allowed fields
        
        Args:
            meeting_info (dict): Meeting metadata from meeting-info.json
            summary_data (dict): Summary data from summary.json
            transcript_data (list, optional): Not used (kept for backward compatibility)
            
        Returns:
            dict: Tokenized data safe for LLM processing with keys:
                - meeting_id: Meeting identifier
                - date: Meeting date (YYYY-MM-DD)
                - summary: Redacted summary text
                - topics: Comma-separated topics
                - sentiment_score: Numerical sentiment score
                - overall_sentiment: Sentiment label
                - key_moments: Redacted key moments
        """
        # Extract allowed fields
        meeting_id = meeting_info.get('meetingId', '')
        date = meeting_info.get('startTime', '')[:10]  # YYYY-MM-DD
        summary = summary_data.get('summary', '')
        topics = summary_data.get('topics', [])
        sentiment_score = summary_data.get('sentimentScore', 3.0)
        overall_sentiment = summary_data.get('overallSentiment', 'neutral')
        key_moments = summary_data.get('keyMoments', [])
        
        # Redact PII from summary
        summary = self.redact_email(summary)
        summary = self.redact_phone(summary)
        summary = self.redact_ip(summary)
        
        # Extract organization names for tokenization
        all_emails = meeting_info.get('allEmails', [])
        org_names = list(set([email.split('@')[1].split('.')[0] for email in all_emails if '@' in email]))
        
        # Redact organization names in summary
        summary = self.redact_organization_names(summary, org_names)
        
        # Optimize text to reduce tokens (remove filler words, compress phrases)
        summary = self.optimize_text_for_llm(summary)
        
        # Redact key moments
        tokenized_key_moments = []
        for moment in key_moments:
            tokenized_moment = moment.copy()
            text = moment.get('text', '')
            text = self.redact_email(text)
            text = self.redact_phone(text)
            text = self.redact_organization_names(text, org_names)
            
            # Optimize key moment text
            text = self.optimize_text_for_llm(text)
            
            # Tokenize speaker name
            speaker = moment.get('speaker', '')
            if 'aegis' in speaker.lower():
                tokenized_moment['speaker'] = 'Agent'
            else:
                tokenized_moment['speaker'] = 'Customer'
            
            tokenized_moment['text'] = text
            tokenized_key_moments.append(tokenized_moment)
        
        return {
            'meeting_id': meeting_id,
            'date': date,
            'summary': summary,
            'topics': ', '.join(topics) if isinstance(topics, list) else topics,
            'sentiment_score': sentiment_score,
            'overall_sentiment': overall_sentiment,
            'key_moments': tokenized_key_moments
        }
    
    def validate_tokenized_data(self, tokenized_data: Dict[str, Any]) -> bool:
        """
        Validate that tokenized data contains no PII.
        
        Args:
            tokenized_data (dict): Tokenized meeting data
            
        Returns:
            bool: True if validation passes, False if PII detected
        """
        # Check for email patterns
        for key, value in tokenized_data.items():
            if isinstance(value, str):
                if re.search(self.EMAIL_PATTERN, value):
                    print(f"WARNING: Email pattern detected in {key}")
                    return False
                if re.search(self.PHONE_PATTERN, value):
                    print(f"WARNING: Phone pattern detected in {key}")
                    return False
        
        return True


def load_meeting_files(meeting_id: str, dataset_path: str = None) -> Dict[str, Any]:
    """
    Load all meeting files (meeting-info.json, summary.json, transcript.json).
    
    Args:
        meeting_id (str): Meeting ID (folder name)
        dataset_path (str, optional): Path to dataset directory
        
    Returns:
        dict: Dictionary with keys 'meeting_info', 'summary', 'transcript'
    """
    if dataset_path is None:
        dataset_path = Path(__file__).parent.parent / 'dataset'
    else:
        dataset_path = Path(dataset_path)
    
    meeting_dir = dataset_path / meeting_id
    
    # Load meeting-info.json
    with open(meeting_dir / 'meeting-info.json', 'r') as f:
        meeting_info = json.load(f)
    
    # Load summary.json
    with open(meeting_dir / 'summary.json', 'r') as f:
        summary = json.load(f)
    
    # Load transcript.json
    with open(meeting_dir / 'transcript.json', 'r') as f:
        transcript = json.load(f)
    
    return {
        'meeting_info': meeting_info,
        'summary': summary,
        'transcript': transcript
    }
