import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, Any, Optional

class EnhancedOverlay:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.root = None
        self.is_visible = False
        self.is_fading = False
        self.auto_hide_timer = None
        
        # Content variables (will be initialized after root)
        self.profile_text = None
        self.ai_response_text = None
        self.topic_guidance_text = None
        
        # Positioning
        self.current_position = config.get('position', 'top_right')
        
        self._create_overlay()
    
    def _create_overlay(self):
        """Create the enhanced stealth overlay window"""
        self.root = tk.Tk()
        
        # Now initialize StringVar objects after root window exists
        self.profile_text = tk.StringVar()
        self.ai_response_text = tk.StringVar()
        self.topic_guidance_text = tk.StringVar()
        
        # Configure window for stealth mode
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.wm_attributes('-topmost', True)  # Always on top
        self.root.wm_attributes('-alpha', 0.0)  # Start invisible
        
        # Window properties
        width = self.config.get('width', 350)
        height = self.config.get('height', 200)
        self.root.geometry(f"{width}x{height}")
        
        # Position window
        self._position_window()
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame with dark theme
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Configure dark style
        style.configure('Dark.TFrame', background='#2d2d2d')
        style.configure('Profile.TLabel', background='#2d2d2d', foreground='#87ceeb', 
                       font=('Arial', 8), wraplength=340)
        style.configure('AI.TLabel', background='#2d2d2d', foreground='#ffffff', 
                       font=('Arial', 10), wraplength=340)
        style.configure('Topic.TLabel', background='#2d2d2d', foreground='#98fb98', 
                       font=('Arial', 8), wraplength=340)
        
        # Profile section (if enabled)
        if self.config.get('show_profile_section', True):
            profile_frame = ttk.Frame(main_frame, style='Dark.TFrame')
            profile_frame.pack(fill='x', padx=5, pady=(5, 2))
            
            profile_title = ttk.Label(profile_frame, text="👤 Profile:", 
                                    style='Profile.TLabel', font=('Arial', 8, 'bold'))
            profile_title.pack(anchor='w')
            
            self.profile_label = ttk.Label(profile_frame, textvariable=self.profile_text, 
                                         style='Profile.TLabel')
            self.profile_label.pack(anchor='w', fill='x')
        
        # AI Response section (main)
        ai_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        ai_frame.pack(fill='both', expand=True, padx=5, pady=2)
        
        ai_title = ttk.Label(ai_frame, text="🤖 AI Assistant:", 
                           style='AI.TLabel', font=('Arial', 10, 'bold'))
        ai_title.pack(anchor='w')
        
        self.ai_label = ttk.Label(ai_frame, textvariable=self.ai_response_text, 
                                style='AI.TLabel')
        self.ai_label.pack(anchor='w', fill='both', expand=True)
        
        # Topic guidance section (if enabled)
        if self.config.get('show_topic_guidance', True):
            topic_frame = ttk.Frame(main_frame, style='Dark.TFrame')
            topic_frame.pack(fill='x', padx=5, pady=(2, 5))
            
            topic_title = ttk.Label(topic_frame, text="🎯 Topic Guidance:", 
                                  style='Topic.TLabel', font=('Arial', 8, 'bold'))
            topic_title.pack(anchor='w')
            
            self.topic_label = ttk.Label(topic_frame, textvariable=self.topic_guidance_text, 
                                       style='Topic.TLabel')
            self.topic_label.pack(anchor='w', fill='x')
        
        # Bind mouse events for dragging
        main_frame.bind('<Button-1>', self._start_drag)
        main_frame.bind('<B1-Motion>', self._on_drag)
        
        # Start with hidden window
        self.root.withdraw()
    
    def _position_window(self):
        """Position window based on configuration"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        width = self.config.get('width', 350)
        height = self.config.get('height', 200)
        
        positions = {
            'top_left': (10, 10),
            'top_right': (screen_width - width - 10, 10),
            'bottom_left': (10, screen_height - height - 50),
            'bottom_right': (screen_width - width - 10, screen_height - height - 50)
        }
        
        x, y = positions.get(self.current_position, positions['top_right'])
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def show_overlay(self):
        """Show the overlay with fade-in animation"""
        def _show():
            if self.is_visible:
                return
                
            self.is_visible = True
            self.root.deiconify()
            self._fade_in()
            
            # Start auto-hide timer
            auto_hide_seconds = self.config.get('auto_hide_seconds', 5)
            if auto_hide_seconds > 0:
                self._reset_auto_hide_timer()
        
        if self.root:
            self.root.after(0, _show)
    
    def hide_overlay(self):
        """Hide the overlay with fade-out animation"""
        def _hide():
            if not self.is_visible:
                return
                
            self.is_visible = False
            self._fade_out()
            
            # Cancel auto-hide timer
            if self.auto_hide_timer:
                self.auto_hide_timer.cancel()
                self.auto_hide_timer = None
        
        if self.root:
            self.root.after(0, _hide)
    
    def toggle_overlay(self):
        """Toggle overlay visibility"""
        if self.is_visible:
            self.hide_overlay()
        else:
            self.show_overlay()
    
    def update_profile(self, profile_text: str):
        """Update profile section content"""
        def _update():
            self.profile_text.set(profile_text)
            self._reset_auto_hide_timer()
        
        if self.root:
            self.root.after(0, _update)
    
    def update_ai_response(self, response_text: str):
        """Update AI response section"""
        def _update():
            self.ai_response_text.set(response_text)
            self._reset_auto_hide_timer()
        
        if self.root:
            self.root.after(0, _update)
    
    def append_ai_response(self, text_chunk: str):
        """Append text to AI response (for streaming)"""
        def _append():
            current = self.ai_response_text.get()
            self.ai_response_text.set(current + text_chunk)
            self._reset_auto_hide_timer()
        
        if self.root:
            self.root.after(0, _append)
    
    def update_topic_guidance(self, topic_text: str):
        """Update topic guidance section"""
        def _update():
            self.topic_guidance_text.set(topic_text)
            self._reset_auto_hide_timer()
        
        if self.root:
            self.root.after(0, _update)
    
    def clear_all_content(self):
        """Clear all sections"""
        def _clear():
            self.profile_text.set("")
            self.ai_response_text.set("")
            self.topic_guidance_text.set("")
        
        if self.root:
            self.root.after(0, _clear)
    
    def move_overlay(self, direction: str):
        """Move overlay in specified direction"""
        positions = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
        current_index = positions.index(self.current_position) if self.current_position in positions else 0
        
        if direction == 'left':
            new_index = (current_index - 1) % len(positions)
        elif direction == 'right':
            new_index = (current_index + 1) % len(positions)
        elif direction == 'up':
            new_index = (current_index - 2) % len(positions)
        elif direction == 'down':
            new_index = (current_index + 2) % len(positions)
        else:
            return
        
        self.current_position = positions[new_index]
        self._position_window()
    
    def _fade_in(self):
        """Animate fade-in effect"""
        if self.is_fading:
            return
            
        self.is_fading = True
        threading.Thread(target=self._animate_fade_in, daemon=True).start()
    
    def _fade_out(self):
        """Animate fade-out effect"""
        if self.is_fading:
            return
            
        self.is_fading = True
        threading.Thread(target=self._animate_fade_out, daemon=True).start()
    
    def _animate_fade_in(self):
        """Fade-in animation thread"""
        steps = self.config.get('fade_animation_steps', 5)
        target_opacity = self.config.get('opacity', 0.9)
        
        for i in range(steps + 1):
            opacity = (i / steps) * target_opacity
            self.root.after(0, lambda op=opacity: self.root.wm_attributes('-alpha', op))
            time.sleep(0.05)
        
        self.is_fading = False
    
    def _animate_fade_out(self):
        """Fade-out animation thread"""
        steps = self.config.get('fade_animation_steps', 5)
        current_opacity = self.config.get('opacity', 0.9)
        
        for i in range(steps + 1):
            opacity = current_opacity * (1 - i / steps)
            self.root.after(0, lambda op=opacity: self.root.wm_attributes('-alpha', op))
            time.sleep(0.05)
        
        self.root.after(0, self.root.withdraw)
        self.is_fading = False
    
    def _reset_auto_hide_timer(self):
        """Reset the auto-hide timer"""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
        
        auto_hide_seconds = self.config.get('auto_hide_seconds', 5)
        if auto_hide_seconds > 0 and self.is_visible:
            self.auto_hide_timer = threading.Timer(auto_hide_seconds, self.hide_overlay)
            self.auto_hide_timer.start()
    
    def _start_drag(self, event):
        """Start dragging the window"""
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
    
    def _on_drag(self, event):
        """Handle window dragging"""
        if hasattr(self, 'drag_start_x'):
            x = self.root.winfo_x() + (event.x_root - self.drag_start_x)
            y = self.root.winfo_y() + (event.y_root - self.drag_start_y)
            self.root.geometry(f"+{x}+{y}")
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
    
    def run_event_loop(self):
        """Run the Tkinter event loop (call from main thread)"""
        self.root.mainloop()
    
    def destroy(self):
        """Clean up and destroy the overlay"""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
        
        if self.root:
            self.root.quit()
            self.root.destroy() 