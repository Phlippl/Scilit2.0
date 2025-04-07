# Backend/utils/resource_monitor.py

import os
import psutil
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Monitor system resources and provide warnings/termination for excessive usage
    """
    def __init__(self, 
                 warn_cpu_percent=70, 
                 critical_cpu_percent=85,
                 warn_memory_percent=75, 
                 critical_memory_percent=90,
                 check_interval=5):
        """
        Initialize the resource monitor
        
        Args:
            warn_cpu_percent: CPU usage percentage to trigger warnings
            critical_cpu_percent: CPU usage percentage to trigger critical alerts
            warn_memory_percent: Memory usage percentage for warnings
            critical_memory_percent: Memory usage percentage for critical alerts
            check_interval: How often to check resources (seconds)
        """
        self.warn_cpu_percent = warn_cpu_percent
        self.critical_cpu_percent = critical_cpu_percent
        self.warn_memory_percent = warn_memory_percent
        self.critical_memory_percent = critical_memory_percent
        self.check_interval = check_interval
        
        self.running = False
        self.monitor_thread = None
        self.process = psutil.Process(os.getpid())
        
        # Resource usage history
        self.history = {
            'cpu': [],
            'memory': [],
            'timestamp': []
        }
        
        # Current state
        self.current_cpu = 0
        self.current_memory = 0
        self.current_memory_mb = 0
        self.system_memory_total = psutil.virtual_memory().total / (1024 * 1024)  # MB
        
        # Alert state
        self.cpu_warning_count = 0
        self.memory_warning_count = 0
        
        # Registered callbacks
        self.warning_callbacks = []
        self.critical_callbacks = []
    
    def register_warning_callback(self, callback):
        """Register a function to be called when resource warning occurs"""
        self.warning_callbacks.append(callback)
    
    def register_critical_callback(self, callback):
        """Register a function to be called when resource critical level occurs"""
        self.critical_callbacks.append(callback)
    
    def _check_resources(self):
        """Check current resource usage and trigger alerts if needed"""
        try:
            # Get CPU usage (interval=0.1 means it measures over 100ms)
            self.current_cpu = self.process.cpu_percent(interval=5000)
            
            # Get memory usage
            mem_info = self.process.memory_info()
            self.current_memory_mb = mem_info.rss / (1024 * 1024)  # Convert to MB
            self.current_memory = (self.current_memory_mb / self.system_memory_total) * 100
            
            # Record history (keep last 100 points)
            timestamp = datetime.now().isoformat()
            self.history['cpu'].append(self.current_cpu)
            self.history['memory'].append(self.current_memory)
            self.history['timestamp'].append(timestamp)
            
            # Limit history length
            max_history = 100
            if len(self.history['cpu']) > max_history:
                self.history['cpu'] = self.history['cpu'][-max_history:]
                self.history['memory'] = self.history['memory'][-max_history:]
                self.history['timestamp'] = self.history['timestamp'][-max_history:]
            
            # Check CPU warning threshold
            if self.current_cpu > self.warn_cpu_percent:
                self.cpu_warning_count += 1
                if self.cpu_warning_count >= 3:  # Three consecutive warnings
                    logger.warning(f"High CPU usage detected: {self.current_cpu:.1f}%")
                    for callback in self.warning_callbacks:
                        try:
                            callback('cpu', self.current_cpu)
                        except Exception as e:
                            logger.error(f"Error in CPU warning callback: {e}")
            else:
                self.cpu_warning_count = 0
            
            # Check memory warning threshold
            if self.current_memory > self.warn_memory_percent:
                self.memory_warning_count += 1
                if self.memory_warning_count >= 3:  # Three consecutive warnings
                    logger.warning(f"High memory usage detected: {self.current_memory:.1f}% ({self.current_memory_mb:.1f} MB)")
                    for callback in self.warning_callbacks:
                        try:
                            callback('memory', self.current_memory)
                        except Exception as e:
                            logger.error(f"Error in memory warning callback: {e}")
            else:
                self.memory_warning_count = 0
            
            # Check critical thresholds
            if self.current_cpu > self.critical_cpu_percent or self.current_memory > self.critical_memory_percent:
                logger.error(f"CRITICAL RESOURCE USAGE - CPU: {self.current_cpu:.1f}%, Memory: {self.current_memory:.1f}%")
                for callback in self.critical_callbacks:
                    try:
                        callback('system', {'cpu': self.current_cpu, 'memory': self.current_memory})
                    except Exception as e:
                        logger.error(f"Error in critical resource callback: {e}")
        
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop that runs in a separate thread"""
        logger.info("Resource monitoring started")
        while self.running:
            self._check_resources()
            time.sleep(self.check_interval)
        logger.info("Resource monitoring stopped")
    
    def start(self):
        """Start the resource monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop(self):
        """Stop the resource monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def get_status(self):
        """Get current resource status"""
        return {
            'cpu_percent': self.current_cpu,
            'memory_percent': self.current_memory,
            'memory_mb': self.current_memory_mb,
            'total_memory_mb': self.system_memory_total
        }
    
    def get_history(self):
        """Get resource usage history"""
        return self.history


# Example usage:

# Create a global instance
resource_monitor = ResourceMonitor()

def handle_resource_warning(resource_type, value):
    """Handle resource warning notifications"""
    logger.warning(f"Resource warning for {resource_type}: {value:.1f}%")
    
    # You could throttle certain operations here
    if resource_type == 'cpu' and value > 80:
        # For example, reduce thread pool size temporarily
        pass
    
    if resource_type == 'memory' and value > 85:
        # Force garbage collection
        import gc
        gc.collect()

def handle_critical_resources(resource_type, values):
    """Handle critical resource situations"""
    logger.error(f"Critical resource situation: {values}")
    
    # In extreme cases, you might want to restart the application
    # or terminate certain operations
    
    # For example, you could cancel all background tasks:
    # from api.documents import background_executor
    # background_executor.shutdown(wait=False)


# Register callbacks
resource_monitor.register_warning_callback(handle_resource_warning)
resource_monitor.register_critical_callback(handle_critical_resources)

# In production, start this when the app initializes
# resource_monitor.start()