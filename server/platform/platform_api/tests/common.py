# --- add this helper at the end of test fns ---
def ok(msg):
    """works with verbosity=1, unless using --buffer"""

    print(f"\n✅ OK: {msg}")
