from functools import wraps
from contextlib import contextmanager

from django.test import TestCase


# --- use this decorator for each test fn ---
def print_exit(msg: str):
    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"🧪 Testing: {msg}")
            try:
                ret = func(*args, **kwargs)
                print("✅ All passed!\n")
                return ret
            except Exception as e:
                print("⛔ Fail\n")
                print(e)
                raise

        return wrapper

    return decorator


# --- use this instead of self.subTest ---
@contextmanager
def subtest(testcase: TestCase, msg: str):
    print(f"   ↳ Subtest: {msg}")
    try:
        with testcase.subTest(msg):
            yield
        print("   ✅ Passed!")
    except Exception as e:
        print("   ⛔ Fail")
        print(f"   {e}")
        raise
