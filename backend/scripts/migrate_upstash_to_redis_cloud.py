"""
One-off migration: Upstash -> Redis Cloud.
Uses REDIS_URL_SOURCE (Upstash) and REDIS_URL_TARGET (Redis Cloud).
Run from backend/ with: python scripts/migrate_upstash_to_redis_cloud.py
"""
import os
import sys

# Ensure backend utils are importable when run from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import redis


def _progress(current: int, total: int, width: int = 40, prefix: str = ""):
    if total <= 0:
        return
    pct = current / total
    filled = int(width * pct)
    bar = "=" * filled + "-" * (width - filled)
    sys.stderr.write(f"\r{prefix}[{bar}] {current}/{total} ({100*pct:.0f}%)")
    sys.stderr.flush()


def main():
    source_url = os.getenv("REDIS_URL_SOURCE")
    target_url = os.getenv("REDIS_URL_TARGET")
    if not source_url or not target_url:
        print("Set REDIS_URL_SOURCE (Upstash) and REDIS_URL_TARGET (Redis Cloud)")
        sys.exit(1)
    if source_url == target_url:
        print("Source and target must differ")
        sys.exit(1)

    upstash = redis.from_url(source_url, decode_responses=False)
    redis_cloud = redis.from_url(target_url, decode_responses=False)

    # Use SCAN instead of KEYS to avoid "too many keys" error on Upstash
    print("Scanning keys from Upstash (using SCAN)...")
    keys = []
    cursor = 0
    while True:
        cursor, batch = upstash.scan(cursor=cursor, count=500)
        keys.extend(batch)
        if cursor == 0:
            break
    n = len(keys)
    print(f"Migrating {n} keys...")

    migrated = 0
    errors = 0
    for i, key in enumerate(keys):
        try:
            ttl = upstash.ttl(key)
            value = upstash.dump(key)
            if value is None:
                continue
            restore_ttl = (ttl * 1000) if ttl > 0 else 0
            redis_cloud.restore(key, restore_ttl, value, replace=True)
            migrated += 1
        except Exception as e:
            errors += 1
            print(f"\nError on key {key}: {e}", file=sys.stderr)
        _progress(i + 1, n, prefix="Migration ")

    print(f"\nMigration complete. Migrated: {migrated}, Errors: {errors}")


if __name__ == "__main__":
    main()
