# Backend/utils/performance_utils.py
"""
Utility functions for performance monitoring, timeouts, and resource management.
"""
import os
import logging
import threading
import time
import psutil
import functools
from typing import Any, Callable

logger = logging.getLogger(__name__)

def timeout_handler(max_seconds=120, cpu_limit=70):
    """
    Decorator to limit function execution time and CPU usage
    
    Args:
        max_seconds: Maximum execution time in seconds
        cpu_limit: CPU usage limit in percent
        
    Returns:
        Function decorator that monitors execution time and CPU usage
        
    Example:
        @timeout_handler(max_seconds=60, cpu_limit=80)
        def long_running_function():
            # Function that might take a long time
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e
            
            # Start function in a separate thread
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            
            # Monitor execution time and CPU usage
            start_time = time.time()
            process = psutil.Process(os.getpid())
            
            while thread.is_alive():
                thread.join(timeout=1.0)
                elapsed = time.time() - start_time
                
                # Check time limit
                if elapsed > max_seconds:
                    error[0] = TimeoutError(f"Function execution exceeded {max_seconds} seconds")
                    break
                
                # Check CPU usage
                try:
                    cpu_percent = process.cpu_percent(interval=0.5)
                    if cpu_percent > cpu_limit:
                        error[0] = Exception(f"CPU usage too high: {cpu_percent}% (limit: {cpu_limit}%)")
                        break
                except Exception:
                    pass
            
            if error[0]:
                raise error[0]
            
            return result[0]
        
        return wrapper
    return decorator

def memory_profile(func):
    """
    Decorator to profile memory usage of a function
    
    Args:
        func: Function to profile
        
    Returns:
        Wrapped function that logs memory usage before and after execution
        
    Example:
        @memory_profile
        def memory_intensive_function():
            # Function that might use a lot of memory
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get current memory usage
        process = psutil.Process(os.getpid())
        before_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        start_time = time.time()
        
        # Call the original function
        result = func(*args, **kwargs)
        
        # Get memory usage after function execution
        after_memory = process.memory_info().rss / (1024 * 1024)  # MB
        elapsed_time = time.time() - start_time
        
        # Log memory usage and execution time
        memory_diff = after_memory - before_memory
        logger.info(f"Function {func.__name__}: Memory before: {before_memory:.2f}MB, "
                   f"after: {after_memory:.2f}MB, diff: {memory_diff:.2f}MB, "
                   f"time: {elapsed_time:.2f}s")
        
        return result
    
    return wrapper