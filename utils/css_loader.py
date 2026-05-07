"""
CSS Loader Utility for Aegis Transcript Intelligence
====================================================

This module provides a centralized way to load CSS styles across all pages.
Instead of embedding CSS in each Python file, we maintain a single CSS file
that is loaded consistently.

Author: Aegis Transcript Intelligence Team
Date: 2026-05-06
"""

import streamlit as st
from pathlib import Path


def load_css():
    """
    Load global CSS styles from assets/style.css and inject into Streamlit page.
    
    This function should be called at the beginning of each page to ensure
    consistent styling across the application.
    
    Usage:
        >>> from utils.css_loader import load_css
        >>> load_css()
    
    Returns:
        None: CSS is injected directly into the page via st.markdown()
    """
    # Get path to CSS file
    css_file = Path(__file__).parent.parent / 'assets' / 'style.css'
    
    if not css_file.exists():
        st.warning("⚠️ CSS file not found. Using default Streamlit styling.")
        return
    
    # Read CSS content
    try:
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Inject CSS into page
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        
    except Exception as e:
        st.warning(f"⚠️ Error loading CSS: {e}")


def apply_custom_styles():
    """
    Apply custom CSS overrides and additional styling not in the main CSS file.
    
    This function can be used for page-specific styling that doesn't belong
    in the global stylesheet.
    
    Usage:
        >>> from utils.css_loader import apply_custom_styles
        >>> apply_custom_styles()
    """
    # Additional custom styles can be added here
    # For example, hiding Streamlit's default elements
    st.markdown("""
        <style>
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Reduce top padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Improve sidebar appearance */
        section[data-testid="stSidebar"] {
            background-color: #F8FAFC;
        }
        </style>
    """, unsafe_allow_html=True)


def format_badge(text, badge_type='neutral', size='normal'):
    """
    Generate HTML for a styled badge.
    
    Args:
        text (str): Badge text content
        badge_type (str): Badge style - 'positive', 'negative', 'neutral', 
                         'high', 'medium', 'low', etc.
        size (str): Badge size - 'normal', 'sm' (small), 'lg' (large)
    
    Returns:
        str: HTML string for the badge
        
    Examples:
        >>> format_badge("High", "high", "sm")
        '<span class="badge badge-sm badge-high">High</span>'
    """
    size_class = f' badge-{size}' if size != 'normal' else ''
    type_class = f' badge-{badge_type.lower().replace(" ", "-")}'
    
    return f'<span class="badge{size_class}{type_class}">{text}</span>'


def format_box(content, box_type='info'):
    """
    Generate HTML for a styled content box.
    
    Args:
        content (str): HTML content to display in the box
        box_type (str): Box style - 'info', 'warning', 'success', 'danger'
    
    Returns:
        str: HTML string for the box
        
    Examples:
        >>> format_box("<p>Important message</p>", "warning")
        '<div class="warning-box"><p>Important message</p></div>'
    """
    return f'<div class="{box_type}-box">{content}</div>'
