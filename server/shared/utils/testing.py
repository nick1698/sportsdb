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


def assert_list_envelope(
    data: dict, *, limit: int | None = None, offset: int | None = None
):
    assert "items" in data and isinstance(data["items"], list)
    assert "limit" in data and isinstance(data["limit"], int)
    assert "offset" in data and isinstance(data["offset"], int)
    assert "total" in data and isinstance(data["total"], int)

    if limit is not None:
        assert data["limit"] == limit
    if offset is not None:
        assert data["offset"] == offset
