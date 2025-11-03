"""
Central Performance Management System for MeetMinder
Coordinates caching, memory management, and async operations for optimal performance
"""

import asyncio
import threading
import time
import gc
import weakref
from typing import Dict, Any, Optional, Callable, List, Union, AsyncGenerator
from dataclasses import dataclass, field
from functools import wraps, lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from utils.app_logger import logger
from utils.error_handler import handle_errors, MeetMinderError

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    memory_usage_mb: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    cache_hit_rate: float = 0.0
    avg_response_time: float = 0.0
    active_threads: int = 0
    queue_size: int = 0
    timestamp: float = field(default_factory=time.time)

@dataclass
class CacheEntry:
    """Cache entry with TTL and access tracking"""
    data: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: float = 300.0  # 5 minutes default
    
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl
    
    def access(self):
        self.last_accessed = time.time()
        self.access_count += 1

class SmartCache:
    """Multi-level cache with intelligent eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []
        self.lock = threading.RLock()
        
        # Cache statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value with LRU tracking"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    entry.access()
                    # Move to end of access order (most recently used)
                    if key in self.access_order:
                        self.access_order.remove(key)
                    self.access_order.append(key)
                    self.hits += 1
                    return entry.data
                else:
                    # Remove expired entry
                    del self.cache[key]
                    if key in self.access_order:
                        self.access_order.remove(key)
            
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set cached value with eviction if needed"""
        with self.lock:
            # Clean up if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            ttl = ttl or self.default_ttl
            self.cache[key] = CacheEntry(
                data=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl
            )
            
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
    
    def _evict_lru(self):
        """Evict least recently used entries"""
        if not self.access_order:
            return
        
        # Evict oldest entry
        lru_key = self.access_order.pop(0)
        if lru_key in self.cache:
            del self.cache[lru_key]
            self.evictions += 1
    
    def clear_expired(self):
        """Clear all expired entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'evictions': self.evictions
        }

class ResourcePool:
    """Generic resource pool with lifecycle management"""
    
    def __init__(self, factory: Callable, max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self.pool: List[Any] = []
        self.in_use: weakref.WeakSet = weakref.WeakSet()
        self.lock = threading.Lock()
        self.created_count = 0
    
    def acquire(self):
        """Acquire resource from pool"""
        with self.lock:
            if self.pool:
                resource = self.pool.pop()
            else:
                resource = self.factory()
                self.created_count += 1
            
            self.in_use.add(resource)
            return resource
    
    def release(self, resource):
        """Return resource to pool"""
        with self.lock:
            if resource in self.in_use:
                if len(self.pool) < self.max_size:
                    self.pool.append(resource)
                # Resource will be garbage collected if pool is full
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        return {
            'available': len(self.pool),
            'in_use': len(self.in_use),
            'total_created': self.created_count,
            'max_size': self.max_size
        }

class AsyncTaskQueue:
    """Priority task queue with backpressure management"""
    
    def __init__(self, max_workers: int = 8, max_queue_size: int = 100):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="PerfMgr")
        self.max_queue_size = max_queue_size
        self.queue: asyncio.PriorityQueue = None
        self.running_tasks: weakref.WeakSet = weakref.WeakSet()
        self.completed_tasks = 0
        self.failed_tasks = 0
    
    async def submit(self, priority: int, coro_or_func, *args, **kwargs):
        """Submit task with priority (lower number = higher priority)"""
        if self.queue is None:
            self.queue = asyncio.PriorityQueue(maxsize=self.max_queue_size)
        
        try:
            await self.queue.put((priority, time.time(), coro_or_func, args, kwargs))
        except asyncio.QueueFull:
            logger.warning("Task queue full, dropping task")
            raise MeetMinderError("Task queue is at capacity")
    
    async def process_tasks(self):
        """Process tasks from queue"""
        if self.queue is None:
            return
        
        while True:
            try:
                priority, timestamp, task, args, kwargs = await self.queue.get()
                
                # Execute task
                if asyncio.iscoroutinefunction(task):
                    result = await task(*args, **kwargs)
                else:
                    # Run in thread pool for blocking operations
                    result = await asyncio.get_event_loop().run_in_executor(
                        self.executor, task, *args, **kwargs
                    )
                
                self.completed_tasks += 1
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                self.failed_tasks += 1
                self.queue.task_done()
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            'queue_size': self.queue.qsize() if self.queue else 0,
            'completed': self.completed_tasks,
            'failed': self.failed_tasks,
            'running': len(self.running_tasks)
        }

class PerformanceManager(QObject):
    """Central performance management coordinator"""
    
    # Signals for performance events
    performance_alert = pyqtSignal(str, dict)  # alert_type, metrics
    cache_stats_updated = pyqtSignal(dict)
    resource_stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.cache = SmartCache(max_size=2000, default_ttl=300.0)
        self.task_queue = AsyncTaskQueue(max_workers=8)
        self.resource_pools: Dict[str, ResourcePool] = {}
        
        # Performance monitoring
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = 100
        
        # Background task management
        self.background_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_metrics)
        
        logger.info("[PERF] Performance Manager initialized")
    
    def start(self):
        """Start performance management"""
        if not self.is_running:
            self.is_running = True
            
            # Start monitoring
            self.monitor_timer.start(10000)  # 10 seconds
            
            # Start background task processing
            loop = asyncio.get_event_loop()
            task = loop.create_task(self.task_queue.process_tasks())
            self.background_tasks.append(task)
            
            logger.info("✅ Performance Manager started")
    
    def stop(self):
        """Stop performance management"""
        if self.is_running:
            self.is_running = False
            
            # Stop monitoring
            self.monitor_timer.stop()
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            self.background_tasks.clear()
            
            # Shutdown executor
            self.task_queue.executor.shutdown(wait=False)
            
            logger.info("🛑 Performance Manager stopped")
    
    def create_resource_pool(self, name: str, factory: Callable, max_size: int = 10):
        """Create a new resource pool"""
        self.resource_pools[name] = ResourcePool(factory, max_size)
        logger.info(f"✅ Created resource pool: {name} (max_size: {max_size})")
    
    def get_resource_pool(self, name: str) -> Optional[ResourcePool]:
        """Get resource pool by name"""
        return self.resource_pools.get(name)
    
    @handle_errors(show_user_message=False)
    def _collect_metrics(self):
        """Collect current performance metrics"""
        try:
            process = psutil.Process()
            
            # System metrics
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            cpu_percent = process.cpu_percent()
            
            # Cache metrics
            cache_stats = self.cache.get_stats()
            cache_hit_rate = cache_stats['hit_rate']
            
            # Queue metrics
            queue_stats = self.task_queue.get_stats()
            
            metrics = PerformanceMetrics(
                memory_usage_mb=memory_mb,
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                cache_hit_rate=cache_hit_rate,
                active_threads=threading.active_count(),
                queue_size=queue_stats['queue_size']
            )
            
            # Store metrics
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            # Check for performance alerts
            self._check_performance_alerts(metrics)
            
            # Emit signals
            self.cache_stats_updated.emit(cache_stats)
            self.resource_stats_updated.emit({
                'pools': {name: pool.get_stats() for name, pool in self.resource_pools.items()},
                'queue': queue_stats
            })
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
    
    def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """Check for performance issues and emit alerts"""
        alerts = []
        
        if metrics.memory_percent > 80:
            alerts.append(('high_memory', {'usage': metrics.memory_percent}))
        
        if metrics.cpu_percent > 90:
            alerts.append(('high_cpu', {'usage': metrics.cpu_percent}))
        
        if metrics.cache_hit_rate < 0.3:  # Less than 30% hit rate
            alerts.append(('low_cache_efficiency', {'hit_rate': metrics.cache_hit_rate}))
        
        if metrics.queue_size > 50:
            alerts.append(('queue_backlog', {'size': metrics.queue_size}))
        
        for alert_type, data in alerts:
            self.performance_alert.emit(alert_type, data)
    
    def cleanup_resources(self):
        """Perform resource cleanup"""
        logger.info("🧹 Starting performance cleanup...")
        
        # Clear expired cache entries
        self.cache.clear_expired()
        
        # Force garbage collection
        collected = gc.collect()
        
        logger.info(f"✅ Cleanup complete. Collected {collected} objects")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.metrics_history:
            return {}
        
        latest = self.metrics_history[-1]
        
        # Calculate averages over last 10 samples
        recent_metrics = self.metrics_history[-10:]
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        
        return {
            'current': {
                'memory_mb': latest.memory_usage_mb,
                'memory_percent': latest.memory_percent,
                'cpu_percent': latest.cpu_percent,
                'cache_hit_rate': latest.cache_hit_rate,
                'active_threads': latest.active_threads,
                'queue_size': latest.queue_size
            },
            'averages': {
                'memory_percent': avg_memory,
                'cpu_percent': avg_cpu,
                'cache_hit_rate': avg_cache_hit
            },
            'cache': self.cache.get_stats(),
            'pools': {name: pool.get_stats() for name, pool in self.resource_pools.items()},
            'queue': self.task_queue.get_stats()
        }

# Global performance manager instance
performance_manager = PerformanceManager()

# Performance decorators
def cached(ttl: float = 300.0, key_func: Optional[Callable] = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try cache first
            result = performance_manager.cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            performance_manager.cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def background_task(priority: int = 5):
    """Decorator for running tasks in background"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await performance_manager.task_queue.submit(priority, func, *args, **kwargs)
        return wrapper
    return decorator

def performance_monitor(func):
    """Decorator for monitoring function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"⏱️ {func.__name__} took {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ {func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper 