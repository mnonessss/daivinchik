import argparse
import random
import threading
import time
from dataclasses import dataclass

import requests


@dataclass
class RunStats:
    total = 0
    success = 0
    errors = 0
    total_latency_ms = 0.0

    def record(self, ok, latency_ms):
        self.total += 1
        if ok:
            self.success += 1
        else:
            self.errors += 1
        self.total_latency_ms += latency_ms

    def to_dict(self, duration_sec):
        avg_latency = (self.total_latency_ms / self.total) if self.total else 0.0
        throughput = (self.total / duration_sec) if duration_sec else 0.0
        return {
            "total_requests": self.total,
            "success": self.success,
            "errors": self.errors,
            "throughput_req_sec": round(throughput, 2),
            "avg_latency_ms": round(avg_latency, 2),
        }


def worker(
    stop_at: float,
    base_url: str,
    read_ratio: float,
    key_space: int,
    timeout: float,
    lock: threading.Lock,
    shared: RunStats,
):
    local = RunStats()
    while time.time() < stop_at:
        item_id = random.randint(1, key_space)
        do_read = random.random() < read_ratio
        started = time.perf_counter()
        ok = False
        try:
            if do_read:
                response = requests.get(f"{base_url}/get/{item_id}", timeout=timeout)
            else:
                value = random.randint(1, 1_000_000)
                response = requests.post(
                    f"{base_url}/set/{item_id}",
                    json={"value": value},
                    timeout=timeout,
                )
            ok = response.status_code < 500
        except Exception:
            ok = False
        latency_ms = (time.perf_counter() - started) * 1000
        local.record(ok, latency_ms)
    with lock:
        shared.total += local.total
        shared.success += local.success
        shared.errors += local.errors
        shared.total_latency_ms += local.total_latency_ms


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--duration", type=int, default=20)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--read-ratio", type=float, default=0.8)
    parser.add_argument("--key-space", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()

    stop_at = time.time() + args.duration
    lock = threading.Lock()
    shared = RunStats()
    threads = []

    for _ in range(args.workers):
        thread = threading.Thread(
            target=worker,
            args=(
                stop_at,
                args.base_url,
                args.read_ratio,
                args.key_space,
                args.timeout,
                lock,
                shared,
            ),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    print(shared.to_dict(args.duration))


if __name__ == "__main__":
    main()
