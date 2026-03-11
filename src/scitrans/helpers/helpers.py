import time
from functools import wraps


def print_timing(message):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(message)
            t0 = time.perf_counter()
            result = func(*args, **kwargs)
            print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
            return result
        return wrapper
    return decorator
