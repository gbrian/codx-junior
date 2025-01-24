import time
import logging
import json
import asyncio
import functools
from contextlib import contextmanager

import cProfile, pstats, io
from pstats import SortKey

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def profile_function(func):
    """Decorator to profile a function and log the execution time."""
    @contextmanager
    def wrapping_logic(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        all_args = [str(arg) for arg in args]
        for arg, value in kwargs.items():
            all_args.append(f"{arg}={value}")

        start_time = time.time()
        
        yield
        
        end_time = time.time()
        time_taken = end_time - start_time

        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        profile_stats = s.getvalue()
        profile_stats = ""
        func_data = {
            "module": func.__module__,
            "method": func.__name__,
            "time_taken": time_taken,
            "profile_stats": profile_stats,
            "args": all_args
        }
        logger.info(f'Profiler: { json.dumps(func_data) }')

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not asyncio.iscoroutinefunction(func):
            with wrapping_logic(*args, **kwargs):
                return func(*args, **kwargs)
        else:
            async def tmp():
                with wrapping_logic(*args, **kwargs):
                    return (await func(*args, **kwargs))
            return tmp()
    return wrapper
