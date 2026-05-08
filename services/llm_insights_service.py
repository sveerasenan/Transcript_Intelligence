"""
LLM Insights Service for Aegis Transcript Intelligence
=======================================================

This module provides LLM-powered deep insights for meeting transcripts.

Features:
- Multi-provider support (OpenAI, Google Gemini)
- Privacy-safe data processing with PII redaction
- Configurable prompts and parameters
- Response caching to minimize API costs
- Validation and retry logic

Author: Aegis Transcript Intelligence Team
Date: 2026-05-07
"""

import os
import json
import hashlib
import time
import re
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from dotenv import load_dotenv

from services.llm_utils import LLMDataTokenizer, load_meeting_files


class LLMInsightsService:
    """
    Service for generating LLM-powered insights from meeting transcripts.
    
    Supports multiple LLM providers (OpenAI, Gemini) with configurable
    parameters, privacy guardrails, and response caching.
    """
    
    def __init__(self, config_path: str = None, provider: str = None):
        """
        Initialize LLM Insights Service.
        
        Args:
            config_path (str, optional): Path to llm.yaml config file
            provider (str, optional): LLM provider to use ('openai' or 'gemini').
                If None, uses default from config.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'llm.yaml'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Set provider
        self.provider = provider or self.config.get('provider', 'openai')
        
        # Initialize tokenizer
        self.tokenizer = LLMDataTokenizer(config_path)
        
        # Initialize cache directory
        if self.config['cache']['enabled']:
            self.cache_dir = Path(self.config['cache']['cache_dir'])
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize provider clients (lazy loading)
        self._openai_client = None
        self._gemini_client = None
    
    def _get_openai_client(self):
        """
        Get OpenAI client (lazy initialization).
        
        Returns:
            OpenAI client instance
        """
        if self._openai_client is None:
            try:
                from openai import OpenAI
                
                api_key_env = self.config['openai']['api_key_env_var']
                api_key = os.environ.get(api_key_env)
                
                if not api_key:
                    raise ValueError(
                        f"OpenAI API key not found. Please set {api_key_env} environment variable."
                    )
                
                self._openai_client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Run: pip install openai"
                )
        
        return self._openai_client
    
    def _get_gemini_client(self):
        """
        Get Gemini client (lazy initialization).
        
        Returns:
            Gemini client instance
        """
        if self._gemini_client is None:
            try:
                import google.generativeai as genai
                
                api_key_env = self.config['gemini']['api_key_env_var']
                api_key = os.environ.get(api_key_env)
                
                if not api_key:
                    raise ValueError(
                        f"Gemini API key not found. Please set {api_key_env} environment variable."
                    )
                
                genai.configure(api_key=api_key)
                
                model_name = self.config['gemini']['model']
                self._gemini_client = genai.GenerativeModel(model_name)
            except ImportError:
                raise ImportError(
                    "Google Generative AI package not installed. Run: pip install google-generativeai"
                )
        
        return self._gemini_client
    
    def _build_prompt(self, tokenized_data: Dict[str, Any]) -> str:
        """
        Build LLM prompt from tokenized data.
        
        Args:
            tokenized_data (dict): Tokenized meeting data
            
        Returns:
            str: Formatted prompt string
        """
        prompt_template = self.config['prompt']['user_prompt_template']
        
        return prompt_template.format(
            meeting_id=tokenized_data['meeting_id'],
            date=tokenized_data['date'],
            summary=tokenized_data['summary'],
            topics=tokenized_data['topics'],
            sentiment_score=tokenized_data['sentiment_score']
        )
    
    def _get_cache_key(self, meeting_id: str, provider: str) -> str:
        """
        Generate cache key for meeting insights.
        
        Args:
            meeting_id (str): Meeting ID
            provider (str): LLM provider name
            
        Returns:
            str: Cache key (hash)
        """
        cache_input = f"{meeting_id}_{provider}_{self.config[provider]['model']}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _get_cached_insights(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached insights if available and not expired.
        
        Args:
            meeting_id (str): Meeting ID
            
        Returns:
            dict or None: Cached insights if available, None otherwise
        """
        if not self.config['cache']['enabled']:
            return None
        
        cache_key = self._get_cache_key(meeting_id, self.provider)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        # Check if cache is expired
        cache_age = time.time() - cache_file.stat().st_mtime
        ttl = self.config['cache']['ttl_seconds']
        
        if cache_age > ttl:
            # Cache expired, delete it
            cache_file.unlink()
            return None
        
        # Load cached insights
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    def _cache_insights(self, meeting_id: str, insights: Dict[str, Any]):
        """
        Cache insights to disk.
        
        Args:
            meeting_id (str): Meeting ID
            insights (dict): Insights to cache
        """
        if not self.config['cache']['enabled']:
            return
        
        cache_key = self._get_cache_key(meeting_id, self.provider)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(insights, f, indent=2)
    
    def _call_openai(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """
        Call OpenAI API to generate insights.
        
        Args:
            prompt (str): User prompt
            system_prompt (str): System prompt
            
        Returns:
            dict: Parsed JSON response
        """
        client = self._get_openai_client()
        config = self.config['openai']
        
        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config['max_tokens'],
            temperature=config['temperature'],
            response_format={"type": "json_object"} if self.config['validation']['require_json'] else None
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse OpenAI response as JSON: {e}")
    
    def _call_gemini(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """
        Call Google Gemini API to generate insights.
        
        Args:
            prompt (str): User prompt
            system_prompt (str): System prompt
            
        Returns:
            dict: Parsed JSON response
        """
        client = self._get_gemini_client()
        config = self.config['gemini']
        
        # Combine system and user prompts for Gemini with explicit JSON-only instruction
        full_prompt = f"""{system_prompt}

CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object. Do not include:
- Markdown formatting or code blocks (no ``` markers)
- Any explanatory text before or after the JSON
- Any comments within the JSON

Start your response directly with {{ and end with }}

{prompt}"""
        
        # Configure generation parameters
        # Note: response_mime_type may not be supported by all API versions
        generation_config = {
            "temperature": config['temperature'],
            "max_output_tokens": config['max_tokens'],
        }
        
        try:
            # Try with response_mime_type first (newer API versions)
            generation_config["response_mime_type"] = "application/json"
            response = client.generate_content(
                full_prompt,
                generation_config=generation_config
            )
        except Exception as e:
            # Fallback without response_mime_type
            print(f"⚠️ Gemini API call with response_mime_type failed, retrying without it: {e}")
            generation_config.pop("response_mime_type", None)
            response = client.generate_content(
                full_prompt,
                generation_config=generation_config
            )
        
        # Check if response was truncated
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = str(candidate.finish_reason)
                print(f"🔍 Gemini finish_reason: {finish_reason}")
                if 'MAX_TOKENS' in finish_reason or 'LENGTH' in finish_reason:
                    raise ValueError(f"Gemini response truncated due to max_tokens limit. Increase max_tokens in config. Finish reason: {finish_reason}")
        
        content = response.text
        
        # Debug: Print first 500 chars of response for troubleshooting
        print(f"📋 Gemini Response Preview (first 500 chars):\n{content[:500]}\n{'='*80}")
        
        # Clean up common issues
        content_clean = content.strip()
        
        # Parse JSON response (handle markdown code blocks)
        try:
            return json.loads(content_clean)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code block
            # Match ```json ... ``` or ``` ... ```
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content_clean, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(1).strip()
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON from code block failed: {e}")
                    print(f"Extracted content: {json_str[:200]}...")
            
            # Try finding JSON object directly (first { to last })
            first_brace = content_clean.find('{')
            last_brace = content_clean.rfind('}')
            
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_str = content_clean[first_brace:last_brace + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON extraction failed: {e}")
                    print(f"Extracted JSON (first 500 chars): {json_str[:500]}...")
                    
                    # Try to fix common JSON issues
                    # Remove trailing commas before closing braces/brackets
                    json_str_fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
                    try:
                        return json.loads(json_str_fixed)
                    except json.JSONDecodeError:
                        pass
            
            print(f"❌ Full Gemini response:\n{content}\n{'='*80}")
            raise ValueError(f"Failed to parse Gemini response as JSON: No valid JSON found in response")
    
    def _validate_response(self, insights: Dict[str, Any]) -> bool:
        """
        Validate LLM response contains required fields.
        
        Args:
            insights (dict): LLM response
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = self.config['validation']['required_fields']
        
        for field in required_fields:
            if field not in insights:
                print(f"WARNING: Required field '{field}' missing from LLM response")
                return False
        
        return True
    
    def get_meeting_insights(
        self, 
        meeting_id: str, 
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get LLM-powered insights for a meeting.
        
        This is the main public method. It:
        1. Checks cache (unless force_refresh=True)
        2. Loads meeting files
        3. Tokenizes and sanitizes data
        4. Calls configured LLM provider
        5. Validates response
        6. Caches result
        
        Args:
            meeting_id (str): Meeting ID to analyze
            force_refresh (bool): Skip cache and generate fresh insights
            
        Returns:
            dict: LLM insights with keys:
                - overall_summary: Concise summary
                - customer_sentiment: Sentiment analysis
                - what_went_well: Positive aspects
                - what_did_not_go_well: Issues and problems
                - key_customer_issues: Main complaints
                - agent_performance: Agent evaluation
                - resolution_status: resolved/unresolved/partially
                - escalation_risk: low/medium/high with explanation
                - churn_risk: low/medium/high with explanation
                - actionable_recommendations: Next steps
                - compliance_flags: Policy concerns
                - key_phrases: Important quotes
                - sentiment_recovery_score: Did sentiment improve?
                - metadata: Processing info (provider, model, cache_hit)
                
        Raises:
            ValueError: If API keys not set or response invalid
            FileNotFoundError: If meeting files not found
        """
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_insights(meeting_id)
            if cached:
                cached['metadata']['cache_hit'] = True
                return cached
        
        # Load meeting files
        try:
            meeting_files = load_meeting_files(meeting_id)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Meeting files not found for {meeting_id}: {e}")
        
        # Tokenize and sanitize data (no transcript needed, only summary)
        tokenized_data = self.tokenizer.tokenize_meeting_data(
            meeting_files['meeting_info'],
            meeting_files['summary']
        )
        
        # Validate tokenized data (no PII)
        if not self.tokenizer.validate_tokenized_data(tokenized_data):
            raise ValueError("Tokenized data failed PII validation. Contains sensitive information.")
        
        # Build prompt
        system_prompt = self.config['prompt']['system_prompt']
        user_prompt = self._build_prompt(tokenized_data)
        
        # Log prompt to console for review
        print("\n" + "="*80)
        print(f"🤖 LLM PROMPT SENT TO {self.provider.upper()}")
        print("="*80)
        print(f"\n📋 SYSTEM PROMPT:\n{system_prompt}\n")
        print(f"📝 USER PROMPT:\n{user_prompt}\n")
        print("="*80 + "\n")
        
        # Call LLM provider with retry logic
        max_retries = self.config[self.provider]['max_retries']
        max_validation_retries = self.config['validation']['max_validation_retries']
        
        insights = None
        for attempt in range(max_retries):
            try:
                if self.provider == 'openai':
                    insights = self._call_openai(user_prompt, system_prompt)
                elif self.provider == 'gemini':
                    insights = self._call_gemini(user_prompt, system_prompt)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                
                # Validate response
                if self._validate_response(insights):
                    break
                else:
                    if attempt < max_validation_retries:
                        print(f"Validation failed, retrying... (attempt {attempt + 1}/{max_validation_retries})")
                        continue
                    else:
                        raise ValueError("LLM response validation failed after max retries")
            
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"LLM call failed, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        # Add metadata
        insights['metadata'] = {
            'provider': self.provider,
            'model': self.config[self.provider]['model'],
            'meeting_id': meeting_id,
            'cache_hit': False,
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Cache insights
        self._cache_insights(meeting_id, insights)
        
        return insights
    
    def get_insights_for_multiple_meetings(
        self, 
        meeting_ids: list,
        max_concurrent: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get insights for multiple meetings (with rate limiting).
        
        Args:
            meeting_ids (list): List of meeting IDs
            max_concurrent (int): Max concurrent API calls
            
        Returns:
            dict: Mapping of meeting_id -> insights
        """
        results = {}
        
        for meeting_id in meeting_ids:
            try:
                insights = self.get_meeting_insights(meeting_id)
                results[meeting_id] = insights
            except Exception as e:
                print(f"Failed to get insights for {meeting_id}: {e}")
                results[meeting_id] = {
                    'error': str(e),
                    'meeting_id': meeting_id
                }
        
        return results
    
    def get_batch_insights(
        self,
        meetings_df,
        period_start: str,
        period_end: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get LLM insights for a batch of meetings in a time period.
        
        Sends all meeting summaries in a single prompt for aggregate analysis.
        
        Args:
            meetings_df (DataFrame): DataFrame with meetings to analyze (must have columns:
                meetingId, date, summary, organization, sentiment_score, topics)
            period_start (str): Start date (YYYY-MM-DD)
            period_end (str): End date (YYYY-MM-DD)
            force_refresh (bool): Skip cache and generate fresh insights
            
        Returns:
            dict: Batch insights with keys:
                - period_overview: Summary of the time period
                - common_themes: Recurring issues
                - escalation_patterns: Meetings needing attention
                - churn_risk_assessment: High-risk accounts
                - agent_performance_trends: Overall agent effectiveness
                - product_issues: Technical problems
                - actionable_recommendations: Next steps
                - sentiment_analysis: Sentiment distribution
                - resolution_effectiveness: Resolution stats
                - executive_summary: Key takeaways
                - metadata: Processing info
                
        Raises:
            ValueError: If API keys not set or response invalid
        """
        # Generate cache key based on meeting IDs and date range
        meeting_ids_hash = hashlib.md5(
            ''.join(sorted(meetings_df['meetingId'].tolist())).encode()
        ).hexdigest()
        cache_key = f"batch_{meeting_ids_hash}_{self.provider}"
        
        # Check cache first
        if not force_refresh and self.config['cache']['enabled']:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_age = time.time() - cache_file.stat().st_mtime
                ttl = self.config['cache']['ttl_seconds']
                if cache_age <= ttl:
                    with open(cache_file, 'r') as f:
                        cached = json.load(f)
                        cached['metadata']['cache_hit'] = True
                        return cached
        
        # Load and tokenize all meetings
        meetings_data_lines = []
        for _, row in meetings_df.iterrows():
            try:
                # Load meeting files
                meeting_files = load_meeting_files(row['meetingId'])
                
                # Tokenize data
                tokenized = self.tokenizer.tokenize_meeting_data(
                    meeting_files['meeting_info'],
                    meeting_files['summary']
                )
                
                # Format as: Meeting ID, Date, Summary
                meeting_line = f"{tokenized['meeting_id']}, {tokenized['date']}, \"{tokenized['summary']}\""
                meetings_data_lines.append(meeting_line)
                
            except Exception as e:
                print(f"Warning: Could not load meeting {row['meetingId']}: {e}")
                continue
        
        # Build batch prompt
        system_prompt = self.config['prompt']['system_prompt']
        batch_template = self.config['prompt']['batch_prompt_template']
        
        # Calculate sentiment statistics
        min_sentiment = meetings_df['sentiment_score'].min()
        max_sentiment = meetings_df['sentiment_score'].max()
        avg_sentiment = meetings_df['sentiment_score'].mean()
        
        user_prompt = batch_template.format(
            meetings_data='\n\n'.join(meetings_data_lines),
            period_start=period_start,
            period_end=period_end,
            total_meetings=len(meetings_data_lines),
            min_sentiment=f"{min_sentiment:.2f}",
            max_sentiment=f"{max_sentiment:.2f}",
            avg_sentiment=f"{avg_sentiment:.2f}"
        )
        
        # Log prompt to console for review
        print("\n" + "="*80)
        print(f"🤖 BATCH LLM PROMPT SENT TO {self.provider.upper()}")
        print("="*80)
        print(f"\n📋 SYSTEM PROMPT:\n{system_prompt}\n")
        print(f"📝 USER PROMPT (showing first 1000 chars):\n{user_prompt[:1000]}...\n")
        print(f"📊 Total meetings in batch: {len(meetings_data_lines)}")
        print("="*80 + "\n")
        
        # Call LLM provider
        max_retries = self.config[self.provider]['max_retries']
        insights = None
        
        for attempt in range(max_retries):
            try:
                if self.provider == 'openai':
                    insights = self._call_openai(user_prompt, system_prompt)
                elif self.provider == 'gemini':
                    insights = self._call_gemini(user_prompt, system_prompt)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                
                # Validate batch response
                required_fields = self.config['validation'].get('batch_required_fields', [])
                if all(field in insights for field in required_fields):
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"Batch validation failed, retrying... (attempt {attempt + 1}/{max_retries})")
                        continue
                    else:
                        raise ValueError("Batch LLM response validation failed")
            
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Batch LLM call failed, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2 ** attempt)
                else:
                    raise
        
        # Add metadata
        insights['metadata'] = {
            'provider': self.provider,
            'model': self.config[self.provider]['model'],
            'period_start': period_start,
            'period_end': period_end,
            'total_meetings': len(meetings_data_lines),
            'cache_hit': False,
            'timestamp': time.time()
        }
        
        # Cache insights
        if self.config['cache']['enabled']:
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(insights, f, indent=2)
        
        return insights
