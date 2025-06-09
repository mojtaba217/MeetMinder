"""
Theme System for MeetMinder
Provides light and dark theme definitions with consistent styling
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ThemeColors:
    """Color definitions for a theme"""
    # Main colors
    primary: str           # Main accent color (blue)
    primary_hover: str     # Hover state for primary
    primary_pressed: str   # Pressed state for primary
    
    # Background colors
    background: str        # Main background
    background_secondary: str  # Secondary background (panels, cards)
    background_tertiary: str   # Tertiary background (hover states)
    
    # Text colors
    text_primary: str      # Main text color
    text_secondary: str    # Secondary text (descriptions, hints)
    text_muted: str       # Muted text (timestamps, metadata)
    text_on_primary: str  # Text on primary color background
    
    # Border colors
    border: str           # Default border color
    border_light: str     # Light border for subtle divisions
    border_focus: str     # Focus state border
    
    # Status colors
    success: str          # Success/positive actions
    warning: str          # Warning states
    error: str           # Error states
    info: str            # Information states
    
    # Special colors
    overlay_background: str    # Semi-transparent overlay background
    shadow: str               # Drop shadow color
    recording_active: str     # Recording indicator color
    ai_response: str         # AI response background

class ThemeManager:
    """Manages theme definitions and switching"""
    
    # Light Theme (matching the image)
    LIGHT_THEME = ThemeColors(
        # Primary blue (like in the image)
        primary="#0078D4",           # Microsoft blue
        primary_hover="#106EBE",     # Darker blue on hover
        primary_pressed="#005A9E",   # Even darker when pressed
        
        # Light backgrounds
        background="#FFFFFF",         # Pure white background
        background_secondary="#F8F9FA",  # Very light gray for panels
        background_tertiary="#F0F2F5",   # Slightly darker for hover
        
        # Dark text on light background
        text_primary="#1C1C1C",      # Almost black for main text
        text_secondary="#605E5C",    # Gray for secondary text
        text_muted="#8A8886",        # Light gray for muted text
        text_on_primary="#FFFFFF",   # White text on blue background
        
        # Light theme borders
        border="#E1E1E1",            # Light gray border
        border_light="#F3F2F1",      # Very light border
        border_focus="#0078D4",      # Blue focus border
        
        # Status colors (adjusted for light theme)
        success="#107C10",           # Green
        warning="#FF8C00",           # Orange
        error="#D13438",             # Red
        info="#0078D4",              # Blue
        
        # Special colors for light theme
        overlay_background="rgba(255, 255, 255, 0.95)",  # Almost opaque white
        shadow="rgba(0, 0, 0, 0.15)",                     # Subtle shadow
        recording_active="#D13438",                        # Red for recording
        ai_response="#F8F9FA"                             # Light background for AI
    )
    
    # Dark Theme (current theme)
    DARK_THEME = ThemeColors(
        # Primary colors
        primary="#0078D4",
        primary_hover="#106EBE",
        primary_pressed="#005A9E",
        
        # Dark backgrounds
        background="#141414",
        background_secondary="#1A1A1A",
        background_tertiary="#262626",
        
        # Light text on dark background
        text_primary="#FFFFFF",
        text_secondary="#C8C6C4",
        text_muted="#8A8886",
        text_on_primary="#FFFFFF",
        
        # Dark theme borders
        border="#404040",
        border_light="#2D2D2D",
        border_focus="#0078D4",
        
        # Status colors
        success="#107C10",
        warning="#FF8C00",
        error="#D13438",
        info="#0078D4",
        
        # Special colors for dark theme
        overlay_background="rgba(20, 20, 20, 0.90)",
        shadow="rgba(0, 0, 0, 0.5)",
        recording_active="#D13438",
        ai_response="#1A1A1A"
    )
    
    @classmethod
    def get_theme(cls, theme_name: str) -> ThemeColors:
        """Get theme by name"""
        if theme_name.lower() == "light":
            return cls.LIGHT_THEME
        elif theme_name.lower() == "dark":
            return cls.DARK_THEME
        else:
            # Default to dark theme
            return cls.DARK_THEME
    
    @classmethod
    def get_available_themes(cls) -> Dict[str, str]:
        """Get list of available themes"""
        return {
            "light": "Light Mode",
            "dark": "Dark Mode"
        }

def get_theme_preview_colors(theme_name: str) -> Dict[str, str]:
    """Get a small set of colors for theme preview"""
    theme = ThemeManager.get_theme(theme_name)
    return {
        "background": theme.background,
        "primary": theme.primary,
        "text": theme.text_primary,
        "secondary": theme.background_secondary
    }