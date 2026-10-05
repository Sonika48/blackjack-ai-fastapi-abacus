"""Destructive local demo: resets the counter, then verifies two live nodes."""
import argparse
import asyncio
import time

import httpx


async def demo(urls, count, concurrency):
    async with httpx.AsyncClient(timeout=30) as client:
        async def call(method, url, **kwargs):
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()["sum"]

        for url in urls:
            await call("GET", url + "/abacus/sum")
        assert await call("DELETE", urls[0] + "/abacus/sum") == 0
        limit = asyncio.Semaphore(concurrency)

        async def add(i):
            async with limit:
                return await call("POST", urls[i % len(urls)] + "/abacus/number", json={"number": 1})

        start = time.perf_counter()
        totals = await asyncio.gather(*(add(i) for i in range(count)))
        elapsed = time.perf_counter() - start
        # Every acknowledged increment must have a distinct serialization position.
        assert sorted(totals) == list(range(1, count + 1)), totals
        observed = await asyncio.gather(*(call("GET", url + "/abacus/sum") for url in urls))
        assert observed == [count] * len(urls), observed
        print(f"PASS: {count} concurrent additions across {len(urls)} nodes; all sums={observed}.")
        print(f"Observed throughput: {count / elapsed:.1f} requests/second ({elapsed:.2f}s); local measurement only.")
        assert await call("POST", urls[1] + "/abacus/number", json={"number": -7}) == count - 7
        assert await call("GET", urls[0] + "/abacus/sum") == count - 7
        for invalid in (True, 1.5, "3", None):
            response = await client.post(urls[0] + "/abacus/number", json={"number": invalid})
            assert response.status_code == 422, response.text
        assert await call("DELETE", urls[1] + "/abacus/sum") == 0
        assert await call("GET", urls[0] + "/abacus/sum") == 0
        # A racing increment/reset has only two valid serial orders.
        for _ in range(20):
            await call("DELETE", urls[0] + "/abacus/sum")
            added, reset = await asyncio.gather(
                call("POST", urls[0] + "/abacus/number", json={"number": 1}),
                call("DELETE", urls[1] + "/abacus/sum"))
            final = await call("GET", urls[0] + "/abacus/sum")
            assert added == 1 and reset == 0 and final in (0, 1)
        await call("DELETE", urls[0] + "/abacus/sum")
        print("PASS: negative additions, validation, cross-node reset, and racing add/reset.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urls", nargs="+", default=["http://localhost:8001", "http://localhost:8002"])
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=50)
    args = parser.parse_args()
    if len(args.urls) < 2 or args.requests < 1 or args.concurrency < 1:
        parser.error("Use at least two URLs and positive request/concurrency counts")
    asyncio.run(demo([url.rstrip("/") for url in args.urls], args.requests, args.concurrency))
