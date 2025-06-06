"""
Resource monitoring and management system for MeetMinder
"""

import psutil
import threading
import time
import gc
import os
import sys
from typing import Dict, Any, Callable, List
from dataclasses import dataclass
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    thread_count: int
    open_files: int
    timestamp: float

class ResourceMonitor(QObject):
    """Monitor system resources and trigger cleanup when needed"""
    
    # Signals for resource alerts
    memory_warning = pyqtSignal(float)  # Memory usage percentage
    cpu_warning = pyqtSignal(float)     # CPU usage percentage
    cleanup_triggered = pyqtSignal(str) # Cleanup reason
    
    def __init__(self, check_interval: int = 30):
        super().__init__()
        self.check_interval = check_interval  # seconds
        self.is_monitoring = False
        self.process = psutil.Process()
        
        # Thresholds
        self.memory_warning_threshold = 70.0  # %
        self.memory_critical_threshold = 85.0  # %
        self.cpu_warning_threshold = 80.0     # %
        
        # Metrics history
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history_size = 100
        
        # Cleanup callbacks
        self.cleanup_callbacks: Dict[str, Callable] = {}
        
        # Timer for monitoring
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_resources)
        
        # Resource baseline
        self.baseline_memory = self._get_current_memory()
        
    def start_monitoring(self):
        """Start resource monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_timer.start(self.check_interval * 1000)
            print(f"🔍 Resource monitoring started (interval: {self.check_interval}s)")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            self.monitor_timer.stop()
            print("🛑 Resource monitoring stopped")
    
    def check_resources(self):
        """Check current resource usage"""
        try:
            metrics = self._collect_metrics()
            self.metrics_history.append(metrics)
            
            # Trim history
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)
            
            # Check thresholds
            self._check_memory_thresholds(metrics)
            self._check_cpu_thresholds(metrics)
            
            # Log periodic summary
            if len(self.metrics_history) % 10 == 0:  # Every 10 checks
                self._log_resource_summary(metrics)
                
        except Exception as e:
            print(f"❌ Error in resource monitoring: {e}")
    
    def _collect_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics"""
        # Memory info
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = self.process.memory_percent()
        
        # CPU info
        cpu_percent = self.process.cpu_percent()
        
        # Thread and file info
        thread_count = self.process.num_threads()
        try:
            open_files = len(self.process.open_files())
        except:
            open_files = 0
        
        return ResourceMetrics(
            memory_usage_mb=memory_mb,
            memory_percent=memory_percent,
            cpu_percent=cpu_percent,
            thread_count=thread_count,
            open_files=open_files,
            timestamp=time.time()
        )
    
    def _check_memory_thresholds(self, metrics: ResourceMetrics):
        """Check memory usage thresholds"""
        if metrics.memory_percent > self.memory_critical_threshold:
            print(f"🚨 CRITICAL: Memory usage at {metrics.memory_percent:.1f}%")
            self.memory_warning.emit(metrics.memory_percent)
            self._trigger_emergency_cleanup("critical_memory")
            
        elif metrics.memory_percent > self.memory_warning_threshold:
            print(f"⚠️ WARNING: Memory usage at {metrics.memory_percent:.1f}%")
            self.memory_warning.emit(metrics.memory_percent)
            self._trigger_cleanup("high_memory")
    
    def _check_cpu_thresholds(self, metrics: ResourceMetrics):
        """Check CPU usage thresholds"""
        if metrics.cpu_percent > self.cpu_warning_threshold:
            print(f"⚠️ WARNING: CPU usage at {metrics.cpu_percent:.1f}%")
            self.cpu_warning.emit(metrics.cpu_percent)
            self._trigger_cleanup("high_cpu")
    
    def _log_resource_summary(self, current: ResourceMetrics):
        """Log resource usage summary"""
        avg_memory = sum(m.memory_percent for m in self.metrics_history[-10:]) / min(10, len(self.metrics_history))
        avg_cpu = sum(m.cpu_percent for m in self.metrics_history[-10:]) / min(10, len(self.metrics_history))
        
        print(f"📊 Resource Summary: Memory: {current.memory_usage_mb:.1f}MB ({current.memory_percent:.1f}%), "
              f"CPU: {current.cpu_percent:.1f}%, Threads: {current.thread_count}, "
              f"Files: {current.open_files}")
        print(f"   10-sample averages - Memory: {avg_memory:.1f}%, CPU: {avg_cpu:.1f}%")
    
    def _trigger_cleanup(self, reason: str):
        """Trigger gentle cleanup"""
        print(f"🧹 Triggering cleanup: {reason}")
        self.cleanup_triggered.emit(reason)
        
        # Execute registered cleanup callbacks
        for name, callback in self.cleanup_callbacks.items():
            try:
                print(f"   Running {name} cleanup...")
                callback()
            except Exception as e:
                print(f"   ❌ Error in {name} cleanup: {e}")
        
        # Force garbage collection
        gc.collect()
    
    def _trigger_emergency_cleanup(self, reason: str):
        """Trigger aggressive cleanup for critical situations"""
        print(f"🚨 Emergency cleanup: {reason}")
        self.cleanup_triggered.emit(f"emergency_{reason}")
        
        # More aggressive cleanup
        self._trigger_cleanup(reason)
        
        # Multiple garbage collection cycles
        for _ in range(3):
            gc.collect()
    
    def register_cleanup_callback(self, name: str, callback: Callable):
        """Register a cleanup callback"""
        self.cleanup_callbacks[name] = callback
        print(f"✅ Registered cleanup callback: {name}")
    
    def unregister_cleanup_callback(self, name: str):
        """Unregister a cleanup callback"""
        if name in self.cleanup_callbacks:
            del self.cleanup_callbacks[name]
            print(f"🗑️ Unregistered cleanup callback: {name}")
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get current resource summary"""
        if not self.metrics_history:
            return {}
        
        current = self.metrics_history[-1]
        return {
            'current_memory_mb': current.memory_usage_mb,
            'current_memory_percent': current.memory_percent,
            'current_cpu_percent': current.cpu_percent,
            'thread_count': current.thread_count,
            'open_files': current.open_files,
            'baseline_memory_mb': self.baseline_memory,
            'memory_growth_mb': current.memory_usage_mb - self.baseline_memory,
            'monitoring_duration': len(self.metrics_history) * self.check_interval
        }
    
    def _get_current_memory(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def force_cleanup(self):
        """Force immediate cleanup"""
        self._trigger_cleanup("manual")

# Default cleanup functions
def cleanup_audio_buffers():
    """Cleanup audio processing buffers"""
    # This would be implemented to clear audio queues
    pass

def cleanup_ai_cache():
    """Cleanup AI response cache"""
    # This would be implemented to clear AI caches
    pass

def cleanup_ui_resources():
    """Cleanup UI resources"""
    # This would be implemented to clear UI caches, update buffers, etc.
    pass

# Global resource monitor instance
global_resource_monitor = ResourceMonitor()

# Register default cleanup callbacks
global_resource_monitor.register_cleanup_callback("audio_buffers", cleanup_audio_buffers)
global_resource_monitor.register_cleanup_callback("ai_cache", cleanup_ai_cache)
global_resource_monitor.register_cleanup_callback("ui_resources", cleanup_ui_resources) 