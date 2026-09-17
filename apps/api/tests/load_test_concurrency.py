"""
Quorum Multi-Agent Platform - Concurrency & Load Benchmark
Measures throughput, latency percentiles (p50, p95), and failure rates under concurrent swarm dispatch loads.
"""

import asyncio
import statistics
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"
PROJECT_ID = "a9d930d2-03dd-431e-9390-246925165e9a"
TEST_QUERIES = [
    "Scalability Bounds in Post-Quantum Key Exchange",
    "Autonomous Fault-Tolerance in Multi-Agent Consensus",
    "Empirical Verification of Asynchronous Mempool Protocols",
    "Photovoltaic Perovskite Stability Benchmarks",
    "Transformer Attention Complexity in Decentralized Swarms",
]


async def benchmark_single_request(client: httpx.AsyncClient, query: str) -> float:
    """Dispatches a single report creation request and measures latency in milliseconds."""
    start = time.perf_counter()
    resp = await client.post(
        f"{BASE_URL}/api/projects/{PROJECT_ID}/reports",
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=15.0,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    return elapsed_ms


async def run_concurrent_batch(concurrency: int) -> list[float]:
    """Runs a batch of concurrent requests and returns latency measurements."""
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(concurrency):
            query = TEST_QUERIES[i % len(TEST_QUERIES)] + f" (Batch Test #{i+1})"
            tasks.append(benchmark_single_request(client, query))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        latencies = [r for r in results if isinstance(r, float)]
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            print(f"  [Warning] {len(errors)} requests encountered errors.")
        return latencies


async def main():
    print("=" * 65)
    print("  QUORUM CONCURRENCY & ORCHESTRATION BENCHMARK")
    print(f"  Target: {BASE_URL}")
    print("=" * 65)

    # 1. Warmup
    print("\nExecuting warmup request...")
    try:
        warmup_ms = await run_concurrent_batch(1)
        print(f"Warmup round complete: {warmup_ms[0]:.2f}ms")
    except Exception as exc:  # noqa: BLE001
        print(f"Warmup note (fallback mode active): {exc}")

    # 2. Test Concurrency Levels
    concurrency_tiers = [5, 10, 20]
    summary_data = []

    for c in concurrency_tiers:
        print(f"\nBenchmarking Concurrency Level: {c} simultaneous swarm launches...")
        t0 = time.perf_counter()
        latencies = await run_concurrent_batch(c)
        total_time = time.perf_counter() - t0

        if latencies:
            p50 = statistics.median(latencies)
            sorted_lat = sorted(latencies)
            p95_idx = int(len(sorted_lat) * 0.95)
            p95 = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
            mean = statistics.mean(latencies)
            rps = len(latencies) / total_time

            summary_data.append({
                "concurrency": c,
                "completed": len(latencies),
                "total_time_s": total_time,
                "p50_ms": p50,
                "p95_ms": p95,
                "mean_ms": mean,
                "rps": rps,
            })
            print(f"  - Completed: {len(latencies)}/{c}")
            print(f"  - Median (p50): {p50:.2f}ms | p95: {p95:.2f}ms")
            print(f"  - Throughput: {rps:.2f} reports/sec")

    print("\n" + "=" * 65)
    print("  FINAL LOAD BENCHMARK SUMMARY (PITCH READY)")
    print("=" * 65)
    print(f"{'Concurrency':<12} | {'p50 Latency':<12} | {'p95 Latency':<12} | {'Throughput (RPS)':<16}")
    print("-" * 65)
    for s in summary_data:
        print(f"{s['concurrency']:<12} | {s['p50_ms']:.2f}ms{'':<6} | {s['p95_ms']:.2f}ms{'':<6} | {s['rps']:.2f} req/sec")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
