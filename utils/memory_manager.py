"""
Smart Memory Management System for MeetMinder
Handles lazy loading, buffer pools, and intelligent cleanup
"""

import gc
import threading
import time
import weakref
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from collections import deque
import psutil
from PyQt5.QtCore import QObject, pyqtSignal

from utils.app_logger import logger
from utils.error_handler import handle_errors

@dataclass
class BufferInfo:
    """Information about a managed buffer"""
    buffer: Any
    size_bytes: int
    created_at: float
    last_used: float
    usage_count: int = 0
    
    def update_usage(self):
        self.last_used = time.time()
        self.usage_count += 1

class LazyLoader:
    """Lazy loading manager for expensive resources"""
    
    def __init__(self):
        self.loaders: Dict[str, Callable] = {}
        self.loaded_resources: Dict[str, Any] = {}
        self.resource_locks: Dict[str, threading.Lock] = {}
        self.access_times: Dict[str, float] = {}
        self.loading_flags: Dict[str, bool] = {}
    
    def register_loader(self, name: str, loader_func: Callable):
        """Register a lazy loader function"""
        self.loaders[name] = loader_func
        self.resource_locks[name] = threading.Lock()
        self.loading_flags[name] = False
        logger.info(f"📦 Registered lazy loader: {name}")
    
    def get_resource(self, name: str, force_reload: bool = False) -> Optional[Any]:
        """Get resource, loading if necessary"""
        if name not in self.loaders:
            logger.warning(f"Unknown resource: {name}")
            return None
        
        with self.resource_locks[name]:
            # Return cached resource if available and not forcing reload
            if name in self.loaded_resources and not force_reload:
                self.access_times[name] = time.time()
                return self.loaded_resources[name]
            
            # Prevent multiple concurrent loads
            if self.loading_flags[name]:
                logger.info(f"🔄 Resource {name} is already loading, waiting...")
                # Wait for loading to complete (with timeout)
                timeout = 30  # 30 seconds
                start_time = time.time()
                while self.loading_flags[name] and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                
                if name in self.loaded_resources:
                    return self.loaded_resources[name]
                else:
                    logger.error(f"Failed to load resource {name} after waiting")
                    return None
            
            # Load resource
            logger.info(f"📥 Loading resource: {name}")
            self.loading_flags[name] = True
            
            try:
                resource = self.loaders[name]()
                self.loaded_resources[name] = resource
                self.access_times[name] = time.time()
                logger.info(f"✅ Successfully loaded resource: {name}")
                return resource
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to load resource {name}: {e}")
                return None
            finally:
                self.loading_flags[name] = False
    
    def unload_resource(self, name: str):
        """Unload resource to free memory"""
        with self.resource_locks.get(name, threading.Lock()):
            if name in self.loaded_resources:
                del self.loaded_resources[name]
                if name in self.access_times:
                    del self.access_times[name]
                logger.info(f"🗑️ Unloaded resource: {name}")
                
                # Force garbage collection
                gc.collect()
    
    def unload_unused(self, max_age_seconds: float = 600):
        """Unload resources that haven't been used recently"""
        current_time = time.time()
        to_unload = []
        
        for name, last_access in self.access_times.items():
            if current_time - last_access > max_age_seconds:
                to_unload.append(name)
        
        for name in to_unload:
            self.unload_resource(name)
            logger.info(f"[CLEANUP] Auto-unloaded unused resource: {name}")
    
    def get_resource_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all resources"""
        info = {}
        current_time = time.time()
        
        for name in self.loaders.keys():
            is_loaded = name in self.loaded_resources
            last_access = self.access_times.get(name, 0)
            age = current_time - last_access if last_access > 0 else None
            
            info[name] = {
                'loaded': is_loaded,
                'loading': self.loading_flags.get(name, False),
                'last_access': last_access,
                'age_seconds': age
            }
        
        return info

class BufferPool:
    """Memory buffer pool for reusable audio/image buffers"""
    
    def __init__(self, buffer_size: int, max_buffers: int = 20):
        self.buffer_size = buffer_size
        self.max_buffers = max_buffers
        self.available_buffers: deque = deque()
        self.in_use_buffers: weakref.WeakSet = weakref.WeakSet()
        self.buffer_info: Dict[int, BufferInfo] = {}  # id -> BufferInfo
        self.lock = threading.Lock()
        self.total_created = 0
        
        logger.info(f"💾 Created buffer pool: {buffer_size} bytes, max {max_buffers} buffers")
    
    def acquire_buffer(self) -> Optional[bytearray]:
        """Acquire a buffer from the pool"""
        with self.lock:
            if self.available_buffers:
                buffer = self.available_buffers.popleft()
                buffer_id = id(buffer)
                if buffer_id in self.buffer_info:
                    self.buffer_info[buffer_id].update_usage()
                self.in_use_buffers.add(buffer)
                return buffer
            
            # Create new buffer if under limit
            if self.total_created < self.max_buffers:
                buffer = bytearray(self.buffer_size)
                self.total_created += 1
                buffer_id = id(buffer)
                
                self.buffer_info[buffer_id] = BufferInfo(
                    buffer=buffer,
                    size_bytes=self.buffer_size,
                    created_at=time.time(),
                    last_used=time.time(),
                    usage_count=1
                )
                
                self.in_use_buffers.add(buffer)
                logger.debug(f"📦 Created new buffer #{self.total_created}")
                return buffer
            
            logger.warning(f"Buffer pool exhausted (max: {self.max_buffers})")
            return None
    
    def release_buffer(self, buffer: bytearray):
        """Return buffer to pool"""
        with self.lock:
            if buffer in self.in_use_buffers:
                # Clear buffer contents
                buffer[:] = bytearray(self.buffer_size)
                self.available_buffers.append(buffer)
                logger.debug("📤 Buffer returned to pool")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer pool statistics"""
        with self.lock:
            return {
                'buffer_size': self.buffer_size,
                'max_buffers': self.max_buffers,
                'total_created': self.total_created,
                'available': len(self.available_buffers),
                'in_use': len(self.in_use_buffers),
                'total_memory_mb': (self.total_created * self.buffer_size) / (1024 * 1024)
            }

class MemoryManager(QObject):
    """Central memory management coordinator"""
    
    # Signals for memory events
    memory_warning = pyqtSignal(float)  # usage percentage
    memory_critical = pyqtSignal(float)
    cleanup_completed = pyqtSignal(dict)  # cleanup stats
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.lazy_loader = LazyLoader()
        self.buffer_pools: Dict[str, BufferPool] = {}
        self.cleanup_callbacks: List[Callable] = []
        
        # Memory monitoring
        self.process = psutil.Process()
        self.baseline_memory = self._get_current_memory()
        self.memory_history: List[float] = []
        self.max_history = 50
        
        # Thresholds
        self.warning_threshold = 80.0  # %
        self.critical_threshold = 90.0  # %
        self.cleanup_threshold = 85.0  # %
        
        # Auto-cleanup settings
        self.auto_cleanup_enabled = True
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        logger.info("[MEMORY] Memory Manager initialized")
    
    def register_lazy_loader(self, name: str, loader_func: Callable):
        """Register a lazy loader"""
        self.lazy_loader.register_loader(name, loader_func)
    
    def get_lazy_resource(self, name: str, force_reload: bool = False) -> Optional[Any]:
        """Get lazily loaded resource"""
        return self.lazy_loader.get_resource(name, force_reload)
    
    def create_buffer_pool(self, name: str, buffer_size: int, max_buffers: int = 20):
        """Create a new buffer pool"""
        self.buffer_pools[name] = BufferPool(buffer_size, max_buffers)
        logger.info(f"✅ Created buffer pool '{name}': {buffer_size} bytes x {max_buffers}")
    
    def get_buffer_pool(self, name: str) -> Optional[BufferPool]:
        """Get buffer pool by name"""
        return self.buffer_pools.get(name)
    
    def register_cleanup_callback(self, callback: Callable):
        """Register cleanup callback"""
        self.cleanup_callbacks.append(callback)
        logger.info(f"✅ Registered cleanup callback: {callback.__name__}")
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Check current memory usage"""
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # Track history
            self.memory_history.append(memory_percent)
            if len(self.memory_history) > self.max_history:
                self.memory_history.pop(0)
            
            # Check thresholds
            if memory_percent > self.critical_threshold:
                logger.warning(f"🚨 CRITICAL: Memory usage at {memory_percent:.1f}%")
                self.memory_critical.emit(memory_percent)
                if self.auto_cleanup_enabled:
                    self.force_cleanup("critical_memory")
                    
            elif memory_percent > self.warning_threshold:
                logger.warning(f"⚠️ Memory usage high: {memory_percent:.1f}%")
                self.memory_warning.emit(memory_percent)
                if self.auto_cleanup_enabled and memory_percent > self.cleanup_threshold:
                    self.gentle_cleanup("high_memory")
            
            return {
                'memory_mb': memory_mb,
                'memory_percent': memory_percent,
                'baseline_mb': self.baseline_memory,
                'growth_mb': memory_mb - self.baseline_memory,
                'trend': self._get_memory_trend()
            }
            
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
            return {}
    
    def _get_memory_trend(self) -> str:
        """Get memory usage trend"""
        if len(self.memory_history) < 5:
            return "unknown"
        
        recent = self.memory_history[-5:]
        if all(recent[i] > recent[i-1] for i in range(1, len(recent))):
            return "increasing"
        elif all(recent[i] < recent[i-1] for i in range(1, len(recent))):
            return "decreasing"
        else:
            return "stable"
    
    def _get_current_memory(self) -> float:
        """Get current memory usage in MB"""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    @handle_errors(show_user_message=False)
    def gentle_cleanup(self, reason: str = "scheduled"):
        """Perform gentle memory cleanup"""
        if time.time() - self.last_cleanup < 60:  # Don't cleanup too frequently
            return
        
        logger.info(f"[CLEANUP] Starting gentle cleanup: {reason}")
        start_memory = self._get_current_memory()
        
        cleanup_stats = {
            'reason': reason,
            'start_memory_mb': start_memory,
            'actions': []
        }
        
        # Unload unused lazy resources
        self.lazy_loader.unload_unused(max_age_seconds=300)  # 5 minutes
        cleanup_stats['actions'].append('unloaded_unused_resources')
        
        # Run registered cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
                cleanup_stats['actions'].append(f'callback_{callback.__name__}')
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
        
        # Garbage collection
        collected = gc.collect()
        cleanup_stats['actions'].append(f'gc_collected_{collected}')
        
        end_memory = self._get_current_memory()
        freed_mb = start_memory - end_memory
        cleanup_stats.update({
            'end_memory_mb': end_memory,
            'freed_mb': freed_mb,
            'objects_collected': collected
        })
        
        self.last_cleanup = time.time()
        logger.info(f"✅ Gentle cleanup complete. Freed {freed_mb:.1f}MB")
        self.cleanup_completed.emit(cleanup_stats)
    
    @handle_errors(show_user_message=False)
    def force_cleanup(self, reason: str = "critical"):
        """Perform aggressive memory cleanup"""
        logger.warning(f"🚨 Starting force cleanup: {reason}")
        start_memory = self._get_current_memory()
        
        cleanup_stats = {
            'reason': reason,
            'start_memory_mb': start_memory,
            'actions': []
        }
        
        # Unload all unused lazy resources immediately
        self.lazy_loader.unload_unused(max_age_seconds=0)  # Force unload all
        cleanup_stats['actions'].append('force_unloaded_all_resources')
        
        # Run cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
                cleanup_stats['actions'].append(f'callback_{callback.__name__}')
            except Exception as e:
                logger.error(f"Force cleanup callback failed: {e}")
        
        # Aggressive garbage collection
        collected = 0
        for _ in range(3):  # Multiple GC cycles
            collected += gc.collect()
        cleanup_stats['actions'].append(f'aggressive_gc_collected_{collected}')
        
        end_memory = self._get_current_memory()
        freed_mb = start_memory - end_memory
        cleanup_stats.update({
            'end_memory_mb': end_memory,
            'freed_mb': freed_mb,
            'objects_collected': collected
        })
        
        self.last_cleanup = time.time()
        logger.warning(f"🚨 Force cleanup complete. Freed {freed_mb:.1f}MB")
        self.cleanup_completed.emit(cleanup_stats)
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get comprehensive memory summary"""
        memory_stats = self.check_memory_usage()
        
        return {
            'current': memory_stats,
            'lazy_resources': self.lazy_loader.get_resource_info(),
            'buffer_pools': {
                name: pool.get_stats() 
                for name, pool in self.buffer_pools.items()
            },
            'cleanup': {
                'auto_enabled': self.auto_cleanup_enabled,
                'last_cleanup': self.last_cleanup,
                'callbacks_registered': len(self.cleanup_callbacks)
            }
        }

# Global memory manager instance
memory_manager = MemoryManager()

# Memory management decorators
def lazy_load(resource_name: str):
    """Decorator for lazy loading expensive resources"""
    def decorator(func):
        # Register the function as a lazy loader
        memory_manager.register_lazy_loader(resource_name, func)
        
        def wrapper(*args, **kwargs):
            return memory_manager.get_lazy_resource(resource_name)
        
        return wrapper
    return decorator

def memory_efficient(func):
    """Decorator for memory-efficient function execution"""
    def wrapper(*args, **kwargs):
        # Check memory before execution
        memory_manager.check_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Trigger cleanup if memory usage is high
            current_memory = memory_manager.check_memory_usage()
            if current_memory.get('memory_percent', 0) > 80:
                memory_manager.gentle_cleanup("post_function_execution")
    
    return wrapper 