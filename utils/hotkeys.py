import keyboard
import asyncio
import threading
from typing import Dict, Callable, Any
from core.config import HotkeysConfig

class HotkeyManager:
    def __init__(self, config: HotkeysConfig):
        self.config = config
        self.callbacks: Dict[str, Callable] = {}
        self.is_active = False
        
    def register_callback(self, action: str, callback: Callable):
        """Register a callback for a specific action"""
        self.callbacks[action] = callback
    
    def start_listening(self):
        """Start listening for global hotkeys"""
        if self.is_active:
            return
            
        self.is_active = True
        
        # Register all hotkeys
        try:
            keyboard.add_hotkey(self.config.trigger_assistance, 
                              lambda: self._trigger_callback('trigger_assistance'))
            keyboard.add_hotkey(self.config.take_screenshot, 
                              lambda: self._trigger_callback('take_screenshot'))
            keyboard.add_hotkey(self.config.toggle_overlay, 
                              lambda: self._trigger_callback('toggle_overlay'))
            keyboard.add_hotkey(self.config.move_left, 
                              lambda: self._trigger_callback('move_left'))
            keyboard.add_hotkey(self.config.move_right, 
                              lambda: self._trigger_callback('move_right'))
            keyboard.add_hotkey(self.config.move_up, 
                              lambda: self._trigger_callback('move_up'))
            keyboard.add_hotkey(self.config.move_down, 
                              lambda: self._trigger_callback('move_down'))
            keyboard.add_hotkey(self.config.emergency_reset, 
                              lambda: self._trigger_callback('emergency_reset'))
            
            print("✓ Global hotkeys registered")
            print(f"  • Trigger assistance: {self.config.trigger_assistance}")
            print(f"  • Take screenshot: {self.config.take_screenshot}")
            print(f"  • Toggle overlay: {self.config.toggle_overlay}")
            print(f"  • Move overlay: {self.config.move_left}/{self.config.move_right}/{self.config.move_up}/{self.config.move_down}")
            print(f"  • Emergency reset: {self.config.emergency_reset}")
            
        except Exception as e:
            print(f"Error registering hotkeys: {e}")
    
    def _trigger_callback(self, action: str):
        """Trigger the callback for a specific action"""
        if action in self.callbacks:
            try:
                callback = self.callbacks[action]
                
                # Handle async callbacks
                if asyncio.iscoroutinefunction(callback):
                    # Run async callback in a new thread
                    threading.Thread(
                        target=lambda: asyncio.run(callback()), 
                        daemon=True
                    ).start()
                else:
                    # Run sync callback directly
                    callback()
                    
            except Exception as e:
                print(f"Error executing callback for {action}: {e}")
        else:
            print(f"No callback registered for action: {action}")
    
    def stop_listening(self):
        """Stop listening for hotkeys"""
        if not self.is_active:
            return
            
        try:
            keyboard.unhook_all_hotkeys()
            self.is_active = False
            print("✓ Stopped hotkey listening")
        except Exception as e:
            print(f"Error stopping hotkey listening: {e}")
    
    def update_config(self, new_config: HotkeysConfig):
        """Update hotkey configuration"""
        was_active = self.is_active
        
        if was_active:
            self.stop_listening()
        
        self.config = new_config
        
        if was_active:
            self.start_listening()

class AsyncHotkeyManager:
    """Async version of hotkey manager for better integration with async code"""
    
    def __init__(self, config: HotkeysConfig):
        self.config = config
        self.callbacks: Dict[str, Callable] = {}
        self.is_active = False
        self._hotkey_thread = None
    
    def register_callback(self, action: str, callback: Callable):
        """Register a callback for a specific action"""
        self.callbacks[action] = callback
    
    async def start_listening(self):
        """Start listening for global hotkeys in async context"""
        if self.is_active:
            return
            
        self.is_active = True
        
        # Start hotkey listening in a separate thread
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_listener_thread, 
            daemon=True
        )
        self._hotkey_thread.start()
        
        print("✓ Async hotkey manager started")
    
    def _hotkey_listener_thread(self):
        """Thread function for hotkey listening"""
        try:
            # Register all hotkeys
            keyboard.add_hotkey(self.config.trigger_assistance, 
                              lambda: self._schedule_callback('trigger_assistance'))
            keyboard.add_hotkey(self.config.take_screenshot, 
                              lambda: self._schedule_callback('take_screenshot'))
            keyboard.add_hotkey(self.config.toggle_overlay, 
                              lambda: self._schedule_callback('toggle_overlay'))
            keyboard.add_hotkey(self.config.move_left, 
                              lambda: self._schedule_callback('move_left'))
            keyboard.add_hotkey(self.config.move_right, 
                              lambda: self._schedule_callback('move_right'))
            keyboard.add_hotkey(self.config.move_up, 
                              lambda: self._schedule_callback('move_up'))
            keyboard.add_hotkey(self.config.move_down, 
                              lambda: self._schedule_callback('move_down'))
            keyboard.add_hotkey(self.config.emergency_reset, 
                              lambda: self._schedule_callback('emergency_reset'))
            
            # Keep the thread alive
            while self.is_active:
                keyboard.wait()
                
        except Exception as e:
            print(f"Error in hotkey listener thread: {e}")
    
    def _schedule_callback(self, action: str):
        """Schedule callback execution"""
        if action in self.callbacks:
            try:
                callback = self.callbacks[action]
                
                # Create a new thread for callback execution
                threading.Thread(
                    target=self._execute_callback,
                    args=(callback,),
                    daemon=True
                ).start()
                
            except Exception as e:
                print(f"Error scheduling callback for {action}: {e}")
    
    def _execute_callback(self, callback: Callable):
        """Execute callback in appropriate context"""
        try:
            if asyncio.iscoroutinefunction(callback):
                # Create new event loop for async callback
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(callback())
                loop.close()
            else:
                callback()
        except Exception as e:
            print(f"Error executing callback: {e}")
    
    async def stop_listening(self):
        """Stop listening for hotkeys"""
        if not self.is_active:
            return
            
        self.is_active = False
        
        try:
            keyboard.unhook_all_hotkeys()
            print("✓ Stopped async hotkey listening")
        except Exception as e:
            print(f"Error stopping async hotkey listening: {e}") 