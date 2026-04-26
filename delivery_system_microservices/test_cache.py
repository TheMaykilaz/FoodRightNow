"""
Cache Performance Test
======================
Compares response times with and without Redis caching.
Checks X-Cache header (HIT / MISS) to verify caching works.

Usage:
    python test_cache.py
"""
import httpx
import time
import sys

ORDER_URL = "http://localhost:8001"
COURIER_URL = "http://localhost:8002"
TRACKING_URL = "http://localhost:8003"
REPORT_URL = "http://localhost:8004"

ENDPOINTS = [
    ("Orders List",    f"{ORDER_URL}/orders/?limit=10"),
    ("Order #100",     f"{ORDER_URL}/orders/100"),
    ("Users List",     f"{ORDER_URL}/users/"),
    ("Couriers List",  f"{COURIER_URL}/couriers/"),
    ("Tracking #104",  f"{TRACKING_URL}/tracking/104"),
    ("General Report", f"{REPORT_URL}/reports/deliveries"),
    ("Weekly Report",  f"{REPORT_URL}/reports/weekly"),
]


def measure(name: str, url: str):
    start = time.perf_counter()
    r = httpx.get(url, timeout=10)
    elapsed_ms = (time.perf_counter() - start) * 1000
    cache = r.headers.get("X-Cache", "MISS")
    return elapsed_ms, cache, r.status_code


def print_table(title: str, results: list):
    print(f"\n{title}")
    print(f"{'Endpoint':<20} {'Time':>10}   {'Cache':<6}  {'Status'}")
    print("-" * 55)
    for name, ms, cache, code in results:
        print(f"{name:<20} {ms:>8.2f}ms   {cache:<6}  {code}")


def flush_cache():
    """Flush all cache via order_service /cache/flush endpoint."""
    try:
        r = httpx.post(f"{ORDER_URL}/cache/flush", timeout=5)
        data = r.json()
        print(f"  Flushed {data.get('flushed_keys', '?')} cache keys via /cache/flush")
    except Exception as e:
        print(f"  Could not flush cache: {e}")


def run_test():
    print("=" * 60)
    print("  REDIS CACHE PERFORMANCE TEST")
    print("=" * 60)

    # --- Check services are up ---
    print("\n[1] Checking services...")
    for name, url in [("Order", ORDER_URL), ("Courier", COURIER_URL),
                       ("Tracking", TRACKING_URL), ("Reporting", REPORT_URL)]:
        try:
            r = httpx.get(f"{url}/health", timeout=3)
            status = "OK" if r.status_code == 200 else f"ERR ({r.status_code})"
        except Exception:
            status = "UNREACHABLE"
        print(f"  {name:>12} Service: {status}")

    # --- Flush cache ---
    print("\n[2] Flushing Redis cache...")
    flush_cache()

    # --- First pass: no cache (MISS expected) ---
    print("\n[3] First requests (cold — MISS expected):")
    cold_results = []
    for name, url in ENDPOINTS:
        ms, cache, code = measure(name, url)
        cold_results.append((name, ms, cache, code))
    print_table("  Cold (no cache):", cold_results)

    # --- Second pass: cached (HIT expected) ---
    print("\n[4] Second requests (warm — HIT expected):")
    warm_results = []
    for name, url in ENDPOINTS:
        ms, cache, code = measure(name, url)
        warm_results.append((name, ms, cache, code))
    print_table("  Warm (cached):", warm_results)

    # --- Comparison ---
    print("\n[5] Speedup comparison:")
    print(f"{'Endpoint':<20} {'Cold':>10} {'Warm':>10} {'Speedup':>10}")
    print("-" * 55)
    for cold, warm in zip(cold_results, warm_results):
        name = cold[0]
        cold_ms = cold[1]
        warm_ms = warm[1]
        speedup = cold_ms / warm_ms if warm_ms > 0 else float('inf')
        print(f"{name:<20} {cold_ms:>8.2f}ms {warm_ms:>8.2f}ms {speedup:>8.1f}x")

    # --- Flush and verify cache eviction ---
    print("\n[6] Testing cache eviction...")
    flush_cache()
    ms, cache, code = measure("Orders List", f"{ORDER_URL}/orders/?limit=10")
    evict_status = "PASS" if cache == "MISS" else "FAIL"
    print(f"  After flush → Cache: {cache} ({evict_status}) | {ms:.2f}ms")

    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
