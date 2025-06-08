"""
Async Pipeline System for MeetMinder
Handles background processing with priority queues and load balancing
"""

import asyncio
import threading
import time
import queue
from typing import Dict, Any, Optional, Callable, List, Union, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref

from utils.app_logger import logger
from utils.error_handler import handle_errors, MeetMinderError

class Priority(IntEnum):
    """Task priority levels (lower number = higher priority)"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

@dataclass
class PipelineTask:
    """Task for pipeline processing"""
    id: str
    priority: Priority
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """For priority queue sorting"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at

@dataclass
class PipelineResult:
    """Result from pipeline processing"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    processing_time: float = 0.0
    retry_count: int = 0

class ProcessingStage:
    """Individual processing stage in pipeline"""
    
    def __init__(self, name: str, processor: Callable, max_concurrent: int = 3):
        self.name = name
        self.processor = processor
        self.max_concurrent = max_concurrent
        self.active_tasks: weakref.WeakSet = weakref.WeakSet()
        self.completed_count = 0
        self.failed_count = 0
        self.total_processing_time = 0.0
        self.lock = threading.Lock()
    
    async def process(self, task: PipelineTask) -> PipelineResult:
        """Process a task through this stage"""
        with self.lock:
            if len(self.active_tasks) >= self.max_concurrent:
                raise MeetMinderError(f"Stage {self.name} at capacity")
        
        start_time = time.time()
        
        try:
            # Add to active tasks
            self.active_tasks.add(task)
            
            # Execute processor
            if asyncio.iscoroutinefunction(self.processor):
                result = await self.processor(*task.args, **task.kwargs)
            else:
                # Run in thread pool for blocking operations
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.processor, *task.args, **task.kwargs)
            
            processing_time = time.time() - start_time
            
            with self.lock:
                self.completed_count += 1
                self.total_processing_time += processing_time
            
            return PipelineResult(
                task_id=task.id,
                success=True,
                result=result,
                processing_time=processing_time,
                retry_count=task.retry_count
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            with self.lock:
                self.failed_count += 1
                self.total_processing_time += processing_time
            
            return PipelineResult(
                task_id=task.id,
                success=False,
                error=e,
                processing_time=processing_time,
                retry_count=task.retry_count
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stage statistics"""
        with self.lock:
            total_tasks = self.completed_count + self.failed_count
            avg_time = (self.total_processing_time / total_tasks) if total_tasks > 0 else 0.0
            
            return {
                'name': self.name,
                'max_concurrent': self.max_concurrent,
                'active_tasks': len(self.active_tasks),
                'completed': self.completed_count,
                'failed': self.failed_count,
                'success_rate': self.completed_count / total_tasks if total_tasks > 0 else 0.0,
                'avg_processing_time': avg_time
            }

class Pipeline:
    """Multi-stage processing pipeline"""
    
    def __init__(self, name: str):
        self.name = name
        self.stages: List[ProcessingStage] = []
        self.input_queue: asyncio.PriorityQueue = None
        self.output_callbacks: List[Callable] = []
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.processed_tasks: Dict[str, PipelineResult] = {}
        self.max_history = 1000
    
    def add_stage(self, name: str, processor: Callable, max_concurrent: int = 3):
        """Add processing stage to pipeline"""
        stage = ProcessingStage(name, processor, max_concurrent)
        self.stages.append(stage)
        logger.info(f"➕ Added stage '{name}' to pipeline '{self.name}'")
    
    def add_output_callback(self, callback: Callable):
        """Add callback for completed tasks"""
        self.output_callbacks.append(callback)
    
    async def start(self, max_workers: int = 5):
        """Start pipeline processing"""
        if self.is_running:
            return
        
        self.is_running = True
        self.input_queue = asyncio.PriorityQueue(maxsize=200)
        
        # Start worker tasks
        for i in range(max_workers):
            task = asyncio.create_task(self._worker(f"worker_{i}"))
            self.worker_tasks.append(task)
        
        logger.info(f"🚀 Started pipeline '{self.name}' with {max_workers} workers")
    
    async def stop(self):
        """Stop pipeline processing"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
        
        logger.info(f"🛑 Stopped pipeline '{self.name}'")
    
    async def submit_task(self, task: PipelineTask) -> bool:
        """Submit task to pipeline"""
        if not self.is_running:
            logger.error(f"Pipeline '{self.name}' is not running")
            return False
        
        try:
            await self.input_queue.put(task)
            logger.debug(f"📤 Submitted task {task.id} to pipeline '{self.name}'")
            return True
        except asyncio.QueueFull:
            logger.warning(f"Pipeline '{self.name}' queue is full")
            return False
    
    async def _worker(self, worker_name: str):
        """Worker coroutine for processing tasks"""
        logger.debug(f"🔄 Worker {worker_name} started for pipeline '{self.name}'")
        
        while self.is_running:
            try:
                # Get task from queue
                task = await asyncio.wait_for(self.input_queue.get(), timeout=1.0)
                
                # Process through all stages
                current_result = None
                for stage in self.stages:
                    try:
                        current_result = await stage.process(task)
                        
                        if not current_result.success:
                            # Handle failure
                            if task.retry_count < task.max_retries:
                                task.retry_count += 1
                                await self.input_queue.put(task)  # Retry
                                logger.info(f"🔄 Retrying task {task.id} (attempt {task.retry_count})")
                            else:
                                logger.error(f"❌ Task {task.id} failed after {task.max_retries} retries")
                                await self._handle_task_completion(current_result)
                            break
                    
                    except Exception as e:
                        logger.error(f"Stage {stage.name} error: {e}")
                        current_result = PipelineResult(
                            task_id=task.id,
                            success=False,
                            error=e,
                            retry_count=task.retry_count
                        )
                        break
                
                # Task completed successfully
                if current_result and current_result.success:
                    await self._handle_task_completion(current_result)
                
                self.input_queue.task_done()
                
            except asyncio.TimeoutError:
                continue  # Normal timeout, check if still running
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
    
    async def _handle_task_completion(self, result: PipelineResult):
        """Handle completed task"""
        # Store result
        self.processed_tasks[result.task_id] = result
        
        # Limit history size
        if len(self.processed_tasks) > self.max_history:
            oldest_key = min(self.processed_tasks.keys())
            del self.processed_tasks[oldest_key]
        
        # Call output callbacks
        for callback in self.output_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Output callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            'name': self.name,
            'running': self.is_running,
            'queue_size': self.input_queue.qsize() if self.input_queue else 0,
            'workers': len(self.worker_tasks),
            'stages': [stage.get_stats() for stage in self.stages],
            'processed_tasks': len(self.processed_tasks),
            'total_completed': sum(1 for r in self.processed_tasks.values() if r.success),
            'total_failed': sum(1 for r in self.processed_tasks.values() if not r.success)
        }

class AsyncPipelineManager:
    """Manager for multiple async pipelines"""
    
    def __init__(self):
        self.pipelines: Dict[str, Pipeline] = {}
        self.global_stats = {
            'total_tasks_processed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0
        }
        self.is_running = False
        
        logger.info("🔧 Async Pipeline Manager initialized")
    
    def create_pipeline(self, name: str) -> Pipeline:
        """Create new pipeline"""
        pipeline = Pipeline(name)
        self.pipelines[name] = pipeline
        logger.info(f"✅ Created pipeline: {name}")
        return pipeline
    
    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """Get pipeline by name"""
        return self.pipelines.get(name)
    
    async def start_all(self):
        """Start all pipelines"""
        if self.is_running:
            return
        
        self.is_running = True
        
        for pipeline in self.pipelines.values():
            await pipeline.start()
        
        logger.info("🚀 All pipelines started")
    
    async def stop_all(self):
        """Stop all pipelines"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        for pipeline in self.pipelines.values():
            await pipeline.stop()
        
        logger.info("🛑 All pipelines stopped")
    
    async def submit_to_pipeline(self, pipeline_name: str, task: PipelineTask) -> bool:
        """Submit task to specific pipeline"""
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            logger.error(f"Pipeline '{pipeline_name}' not found")
            return False
        
        return await pipeline.submit_task(task)
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get statistics for all pipelines"""
        all_stats = {}
        
        for name, pipeline in self.pipelines.items():
            all_stats[name] = pipeline.get_stats()
        
        # Calculate global metrics
        total_completed = sum(stats['total_completed'] for stats in all_stats.values())
        total_failed = sum(stats['total_failed'] for stats in all_stats.values())
        
        return {
            'pipelines': all_stats,
            'global': {
                'total_pipelines': len(self.pipelines),
                'running_pipelines': sum(1 for stats in all_stats.values() if stats['running']),
                'total_completed': total_completed,
                'total_failed': total_failed,
                'success_rate': total_completed / (total_completed + total_failed) if (total_completed + total_failed) > 0 else 0.0
            }
        }

# Global pipeline manager
pipeline_manager = AsyncPipelineManager()

# Convenience functions
async def create_audio_pipeline():
    """Create pipeline for audio processing"""
    pipeline = pipeline_manager.create_pipeline("audio_processing")
    
    # Add stages
    pipeline.add_stage("capture", lambda *args: args, max_concurrent=2)
    pipeline.add_stage("transcribe", lambda *args: args, max_concurrent=1)  # CPU intensive
    pipeline.add_stage("analyze", lambda *args: args, max_concurrent=3)
    
    return pipeline

async def create_ai_pipeline():
    """Create pipeline for AI processing"""
    pipeline = pipeline_manager.create_pipeline("ai_processing")
    
    # Add stages
    pipeline.add_stage("preprocess", lambda *args: args, max_concurrent=5)
    pipeline.add_stage("ai_request", lambda *args: args, max_concurrent=3)  # Limited by API
    pipeline.add_stage("postprocess", lambda *args: args, max_concurrent=5)
    
    return pipeline

async def create_screen_pipeline():
    """Create pipeline for screen processing"""
    pipeline = pipeline_manager.create_pipeline("screen_processing")
    
    # Add stages
    pipeline.add_stage("capture", lambda *args: args, max_concurrent=2)
    pipeline.add_stage("analyze", lambda *args: args, max_concurrent=3)
    pipeline.add_stage("cache", lambda *args: args, max_concurrent=5)
    
    return pipeline

# Decorator for pipeline processing
def pipeline_task(pipeline_name: str, priority: Priority = Priority.NORMAL, 
                 timeout: Optional[float] = None, max_retries: int = 3):
    """Decorator for submitting function to pipeline"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            task = PipelineTask(
                id=f"{func.__name__}_{time.time()}",
                priority=priority,
                func=func,
                args=args,
                kwargs=kwargs,
                timeout=timeout,
                max_retries=max_retries
            )
            
            success = await pipeline_manager.submit_to_pipeline(pipeline_name, task)
            if not success:
                logger.error(f"Failed to submit task to pipeline {pipeline_name}")
                # Fallback to direct execution
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        
        return wrapper
    return decorator 