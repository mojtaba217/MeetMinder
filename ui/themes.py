"""
Theme System for MeetMinder
Provides light and dark theme definitions with consistent styling
"""

import base64
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
    
    @classmethod
    def generate_stylesheet(cls, theme: ThemeColors, size_multiplier: float = 1.0) -> str:
        """Generate complete stylesheet for the given theme"""
        
        def scale(value: int) -> int:
            """Scale a value by the size multiplier"""
            return int(value * size_multiplier)
        
        def scale_font(size: int) -> int:
            """Scale a font size by the size multiplier"""
            return int(size * size_multiplier)
        
        # Generate comprehensive stylesheet
        stylesheet = f"""
        /* Main overlay styling */
        ModernOverlay {{
            background: {theme.overlay_background};
            border-radius: {scale(16)}px;
            color: {theme.text_primary};
        }}
        
        /* Bar container */
        QFrame#barContainer {{
            background: {theme.overlay_background};
            border: 2px solid {theme.border};
            border-radius: {scale(35)}px;
            color: {theme.text_primary};
        }}
        
        /* Expanded container */
        QFrame#expandedContainer {{
            background: {theme.background_secondary};
            border: 1px solid {theme.border_light};
            border-radius: {scale(12)}px;
            color: {theme.text_primary};
        }}
        
        /* Modern buttons */
        ModernButton {{
            background: {theme.background_tertiary};
            border: 2px solid {theme.border};
            border-radius: {scale(25)}px;
            color: {theme.text_primary};
            font-family: 'Segoe UI Variable';
            font-weight: 500;
            padding: {scale(8)}px {scale(16)}px;
        }}
        
        ModernButton:hover {{
            background: {theme.primary};
            border: 2px solid {theme.primary_hover};
            color: {theme.text_on_primary};
        }}
        
        ModernButton:pressed {{
            background: {theme.primary_pressed};
            border: 2px solid {theme.primary_pressed};
            color: {theme.text_on_primary};
        }}
        
        /* Ask AI button (special styling) */
        ModernButton#askAiButton {{
            background: {theme.primary};
            border: 2px solid {theme.primary};
            color: {theme.text_on_primary};
            font-weight: 600;
            font-size: {scale_font(14)}px;
        }}
        
        ModernButton#askAiButton:hover {{
            background: {theme.primary_hover};
            border: 2px solid {theme.primary_hover};
        }}
        
        /* Close button (red styling) */
        ModernButton#closeButton {{
            background: rgba(209, 52, 56, 0.1);
            border: 2px solid rgba(209, 52, 56, 0.3);
            color: {theme.error};
        }}
        
        ModernButton#closeButton:hover {{
            background: {theme.error};
            border: 2px solid {theme.error};
            color: {theme.text_on_primary};
        }}
        
        /* Labels */
        QLabel {{
            color: {theme.text_primary};
            font-family: 'Segoe UI Variable';
            background: transparent;
        }}
        
        /* Timer label */
        QLabel#timerLabel {{
            color: {theme.text_on_primary};
            font-size: {scale_font(16)}px;
            font-weight: 600;
            background: {theme.primary};
            border: 2px solid {theme.primary_hover};
            border-radius: {scale(18)}px;
            padding: {scale(8)}px {scale(16)}px;
            min-width: {scale(70)}px;
        }}
        
        /* Shortcut label */
        QLabel#shortcutLabel {{
            color: {theme.text_secondary};
            font-size: {scale_font(12)}px;
            background: {theme.background_tertiary};
            border: 1px solid {theme.border_light};
            border-radius: {scale(12)}px;
            padding: {scale(6)}px {scale(12)}px;
        }}
        
        /* Text areas */
        QTextEdit {{
            background: {theme.background_secondary};
            border: 1px solid {theme.border_light};
            border-radius: {scale(8)}px;
            color: {theme.text_primary};
            font-family: 'Segoe UI Variable';
            padding: {scale(12)}px;
        }}
        
        QTextEdit:focus {{
            border: 2px solid {theme.border_focus};
        }}
        
        /* Scroll bars */
        QScrollBar:vertical {{
            background: {theme.background_secondary};
            width: {scale(12)}px;
            border-radius: {scale(6)}px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {theme.border};
            border-radius: {scale(6)}px;
            min-height: {scale(20)}px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {theme.text_secondary};
        }}
        
        /* Panels and containers */
        QFrame {{
            background: transparent;
            border: none;
            color: {theme.text_primary};
        }}
        
        QFrame#panel {{
            background: {theme.background_secondary};
            border: 1px solid {theme.border_light};
            border-radius: {scale(8)}px;
            padding: {scale(12)}px;
        }}
        """
        
        return stylesheet

    @classmethod
    def generate_settings_stylesheet(cls, theme: ThemeColors, size_multiplier: float = 1.0) -> str:
        """Generate stylesheet specifically for the settings dialog"""
        
        def scale(value: int) -> int:
            """Scale a value by the size multiplier"""
            return int(value * size_multiplier)
        
        def scale_font(size: int) -> int:
            """Scale a font size by the size multiplier"""
            return int(size * size_multiplier)
        
        # Generate theme-appropriate SVG icons
        # Convert text color to hex for SVG (remove # if present)
        text_color_hex = theme.text_primary.replace('#', '')
        if theme.text_primary.startswith('rgba') or theme.text_primary.startswith('rgb'):
            # For RGB values, use white for dark theme, black for light theme
            text_color_hex = "ffffff" if theme.background == "#141414" else "000000"
        
        # Create base64 encoded SVGs with theme-appropriate colors
        import base64
        
        # Dropdown arrow SVG with theme color
        dropdown_arrow_svg = f'''<svg width="12" height="8" viewBox="0 0 12 8" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M1 1L6 6L11 1" stroke="#{text_color_hex}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
        dropdown_arrow_b64 = base64.b64encode(dropdown_arrow_svg.encode()).decode()
        
        # Checkbox checkmark SVG with white color (always white on colored background)
        checkmark_svg = '''<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M10 3L4.5 8.5L2 6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
        checkmark_b64 = base64.b64encode(checkmark_svg.encode()).decode()
        
        # Generate comprehensive settings dialog stylesheet
        stylesheet = f"""
            QDialog {{
                background: {theme.background};
                color: {theme.text_primary};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: {scale_font(14)}px;
            }}
            QWidget {{
                background: {theme.background};
            }}
            QScrollArea {{
                background: {theme.background};
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: {theme.background};
            }}
            QTabWidget::pane {{
                border: 1px solid {theme.border};
                border-radius: {scale(8)}px;
                background: {theme.background};
                margin-top: -1px;
            }}
            QTabWidget QWidget {{
                background: {theme.background};
            }}
            QTabBar::tab {{
                background: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-bottom: none;
                padding: {scale(12)}px {scale(24)}px;
                margin-right: 2px;
                border-top-left-radius: {scale(8)}px;
                border-top-right-radius: {scale(8)}px;
                min-width: {scale(120)}px;
                font-weight: 500;
                font-size: {scale_font(13)}px;
            }}
            QTabBar::tab:selected {{
                background: {theme.primary};
                color: {theme.text_on_primary};
                border: 1px solid {theme.primary};
            }}
            QTabBar::tab:hover:!selected {{
                background: {theme.background_tertiary};
            }}
            QGroupBox {{
                font-size: {scale_font(16)}px;
                font-weight: 600;
                border: 1px solid {theme.border};
                border-radius: {scale(8)}px;
                margin-top: {scale(15)}px;
                padding-top: {scale(10)}px;
                background: {theme.background_secondary};
                color: {theme.text_primary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {scale(20)}px;
                padding: 0 {scale(10)}px 0 {scale(10)}px;
                color: {theme.text_primary};
                font-size: {scale_font(15)}px;
                font-weight: 600;
            }}
            QLabel {{
                color: {theme.text_primary};
                font-size: {scale_font(14)}px;
                min-height: {scale(28)}px;
                padding: {scale(4)}px;
            }}
            QCheckBox {{
                color: {theme.text_primary};
                font-size: {scale_font(14)}px;
                spacing: {scale(12)}px;
                min-height: {scale(32)}px;
                padding: {scale(6)}px;
            }}
            QCheckBox::indicator {{
                width: {scale(20)}px;
                height: {scale(20)}px;
                border-radius: {scale(4)}px;
                border: 2px solid {theme.border};
                background: {theme.background_tertiary};
            }}
            QCheckBox::indicator:checked {{
                background: {theme.primary};
                border: 2px solid {theme.primary};
                image: url(data:image/svg+xml;base64,{checkmark_b64});
            }}
            QComboBox, QSpinBox, QLineEdit {{
                background: {theme.background_secondary};
                border: 1px solid {theme.border};
                border-radius: {scale(6)}px;
                color: {theme.text_primary};
                font-size: {scale_font(13)}px;
                padding: {scale(8)}px {scale(12)}px;
                min-height: {scale(30)}px;
            }}
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{
                background: {theme.background_tertiary};
                border: 1px solid {theme.primary};
            }}
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
                border: 1px solid {theme.primary};
                background: {theme.background_tertiary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: {scale(30)}px;
            }}
            QComboBox::down-arrow {{
                image: url(data:image/svg+xml;base64,{dropdown_arrow_b64});
            }}
            QComboBox QAbstractItemView {{
                background: {theme.background_secondary};
                border: 1px solid {theme.border};
                color: {theme.text_primary};
                selection-background-color: {theme.primary};
            }}
            QLineEdit::placeholder {{
                color: {theme.text_muted};
            }}
            QTextEdit {{
                background: {theme.background_tertiary};
                border: 2px solid {theme.border};
                border-radius: {scale(6)}px;
                color: {theme.text_primary};
                font-size: {scale_font(13)}px;
                padding: {scale(10)}px;
                font-family: 'Consolas', 'Monaco', monospace;
                line-height: 1.4;
            }}
            QTextEdit:focus {{
                border: 2px solid {theme.primary};
            }}
            QPushButton {{
                background: {theme.background_tertiary};
                border: 2px solid {theme.border};
                border-radius: {scale(6)}px;
                color: {theme.text_primary};
                font-size: {scale_font(13)}px;
                padding: {scale(10)}px {scale(20)}px;
                min-height: {scale(35)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {theme.background_secondary};
                border: 2px solid {theme.primary};
            }}
            QPushButton:pressed {{
                background: {theme.background_tertiary};
            }}
            QPushButton.primary {{
                background: {theme.primary};
                border: 2px solid {theme.primary};
                color: {theme.text_on_primary};
                font-weight: 600;
            }}
            QPushButton.primary:hover {{
                background: {theme.primary_hover};
                border: 2px solid {theme.primary_hover};
            }}
            QScrollBar:vertical {{
                background: {theme.background_tertiary};
                width: {scale(12)}px;
                border-radius: {scale(6)}px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.border};
                border-radius: {scale(6)}px;
                min-height: {scale(20)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme.text_secondary};
            }}
            QSlider::groove:horizontal {{
                background: {theme.border};
                height: {scale(8)}px;
                border-radius: {scale(4)}px;
            }}
            QSlider::handle:horizontal {{
                background: {theme.primary};
                border: 2px solid {theme.primary};
                width: {scale(20)}px;
                height: {scale(20)}px;
                border-radius: {scale(10)}px;
                margin: -{scale(6)}px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background: {theme.primary_hover};
                border: 2px solid {theme.primary_hover};
            }}
        """
        
        return stylesheet

def get_theme_preview_colors(theme_name: str) -> Dict[str, str]:
    """Get a small set of colors for theme preview"""
    theme = ThemeManager.get_theme(theme_name)
    return {
        "background": theme.background,
        "primary": theme.primary,
        "text": theme.text_primary,
        "secondary": theme.background_secondary
    }