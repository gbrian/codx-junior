import time
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def profile_function(func):
    """Decorator to profile a function and log the execution time."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            time_taken = end_time - start_time
            logger.info(f'Profiler: {{"module": "{func.__module__}", "method": "{func.__name__}", "time_taken": {time_taken:.3f} }}')
    return wrapper
