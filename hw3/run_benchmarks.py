import ast
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

import requests


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
PYTHON_BIN = sys.executable

APP_PORT = int(os.getenv("APP_PORT", "5000"))
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
BASE_URL = f"http://127.0.0.1:{APP_PORT}"

STRATEGIES = ["cache_aside", "write_through", "write_back"]
PROFILES = [
    {"name": "read_heavy", "read_ratio": 0.8, "duration": 20, "workers": 20},
    {"name": "balanced", "read_ratio": 0.5, "duration": 20, "workers": 20},
    {"name": "write_heavy", "read_ratio": 0.2, "duration": 20, "workers": 20},
]
REDIS_CONTAINER_NAME = "hw3-cache-benchmark-redis"


def ensure_dirs():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def wait_for(url, timeout_sec = 20.0):
    started = time.time()
    while time.time() - started < timeout_sec:
        try:
            response = requests.get(url, timeout=1.0)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise TimeoutError(f"Service is not ready: {url}")


def stop_proc(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def command_exists(command):
    return subprocess.call(
        ["bash", "-lc", f"command -v {command} >/dev/null 2>&1"],
        cwd=ROOT,
    ) == 0


def start_redis_native():
    proc = subprocess.Popen(
        [
            "redis-server",
            "--save",
            "",
            "--appendonly",
            "no",
            "--port",
            str(REDIS_PORT),
        ],
        cwd=ROOT,
    )
    time.sleep(1.0)
    return proc


def start_redis_docker():
    subprocess.call(
        ["docker", "rm", "-f", REDIS_CONTAINER_NAME],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [
            "docker",
            "run",
            "-d",
            "--name",
            REDIS_CONTAINER_NAME,
            "-p",
            f"{REDIS_PORT}:6379",
            "redis:7-alpine",
            "redis-server",
            "--save",
            "",
            "--appendonly",
            "no",
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2.0)
    return REDIS_CONTAINER_NAME


def stop_redis_docker(container_name):
    subprocess.call(
        ["docker", "rm", "-f", container_name],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_app(strategy):
    env = os.environ.copy()
    env["CACHE_STRATEGY"] = strategy
    env["APP_PORT"] = str(APP_PORT)
    env["REDIS_PORT"] = str(REDIS_PORT)
    proc = subprocess.Popen(
        [PYTHON_BIN, str(ROOT / "app.py")],
        cwd=ROOT.parent,
        env=env,
    )
    wait_for(f"{BASE_URL}/health", timeout_sec=30)
    return proc


def run_load(profile):
    command = [
        PYTHON_BIN,
        str(ROOT / "load_generator.py"),
        "--base-url",
        BASE_URL,
        "--duration",
        str(profile["duration"]),
        "--workers",
        str(profile["workers"]),
        "--read-ratio",
        str(profile["read_ratio"]),
    ]
    output = subprocess.check_output(command, cwd=ROOT.parent, text=True)
    return ast.literal_eval(output.strip())


def collect_metrics():
    response = requests.get(f"{BASE_URL}/metrics", timeout=2.0)
    response.raise_for_status()
    return response.json()


def reset_metrics():
    response = requests.post(f"{BASE_URL}/metrics/reset", timeout=2.0)
    response.raise_for_status()


def run_once(strategy, profile):
    reset_metrics()
    load_metrics = run_load(profile)
    app_metrics = collect_metrics()
    row = {
        "strategy": strategy,
        "profile": profile["name"],
        "throughput_req_sec": load_metrics["throughput_req_sec"],
        "avg_latency_ms": load_metrics["avg_latency_ms"],
        "db_accesses": int(app_metrics["db_reads"]) + int(app_metrics["db_writes"]),
        "cache_hit_rate": app_metrics["cache_hit_rate"],
        "db_reads": app_metrics["db_reads"],
        "db_writes": app_metrics["db_writes"],
        "cache_hits": app_metrics["cache_hits"],
        "cache_misses": app_metrics["cache_misses"],
        "write_back_max_pending": app_metrics.get("write_back_max_pending", 0),
        "write_back_flush_batches": app_metrics.get("write_back_flush_batches", 0),
    }
    return row


def save_results(rows):
    ts = int(time.time())
    json_path = RESULTS_DIR / f"benchmark_{ts}.json"
    csv_path = RESULTS_DIR / f"benchmark_{ts}.csv"
    md_path = RESULTS_DIR / f"report_{ts}.md"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)

    columns = list(rows[0].keys()) if rows else []
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    with open(md_path, "w", encoding="utf-8") as file:
        file.write("## Таблица результатов\n\n")
        header = "| strategy | profile | throughput_req_sec | avg_latency_ms | db_accesses | cache_hit_rate | write_back_max_pending |\n"
        sep = "|---|---:|---:|---:|---:|---:|---:|\n"
        file.write(header)
        file.write(sep)
        for row in rows:
            file.write(
                f"| {row['strategy']} | {row['profile']} | {row['throughput_req_sec']} | "
                f"{row['avg_latency_ms']} | {row['db_accesses']} | {row['cache_hit_rate']} | "
                f"{row['write_back_max_pending']} |\n"
            )

    print(f"Saved JSON: {json_path}")
    print(f"Saved CSV:  {csv_path}")
    print(f"Saved MD:   {md_path}")


def main():
    ensure_dirs()
    rows = []
    redis_proc = None
    redis_container = None
    app_proc = None
    try:
        if command_exists("redis-server"):
            redis_proc = start_redis_native()
        else:
            redis_container = start_redis_docker()

        for strategy in STRATEGIES:
            app_proc = start_app(strategy)
            for profile in PROFILES:
                print(f"Running strategy={strategy} profile={profile['name']}")
                row = run_once(strategy, profile)
                rows.append(row)
                print(row)
            stop_proc(app_proc)
            app_proc = None

        save_results(rows)
    finally:
        if app_proc is not None:
            stop_proc(app_proc)
        if redis_proc is not None:
            stop_proc(redis_proc)
        if redis_container is not None:
            stop_redis_docker(redis_container)


if __name__ == "__main__":
    main()
