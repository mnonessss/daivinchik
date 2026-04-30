import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from flask import Flask, jsonify, request
from redis import Redis


APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "5000"))
DB_PATH = os.getenv("DB_PATH", "hw3/data.sqlite3")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "120"))
WRITE_BACK_FLUSH_SECONDS = float(os.getenv("WRITE_BACK_FLUSH_SECONDS", "1.0"))
CACHE_STRATEGY = os.getenv("CACHE_STRATEGY", "cache_aside").strip().lower()


@dataclass
class Metrics:
    total_requests = 0
    read_requests = 0
    write_requests = 0
    cache_hits = 0
    cache_misses = 0
    db_reads = 0
    db_writes = 0
    write_back_flush_batches = 0
    write_back_flush_items = 0
    write_back_max_pending = 0

    def to_dict(self):
        return self.__dict__.copy()


class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        self.metrics = Metrics()
        self.write_back_buffer: Dict[int, int] = {}
        self.stop_event = threading.Event()


state = AppState()
redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
app = Flask(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                value INTEGER NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.commit()


def seed_db(seed_size = 1000):
    now = time.time()
    with get_conn() as conn:
        current = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
        if current >= seed_size:
            return
        rows = [(idx, idx * 10, now) for idx in range(1, seed_size + 1)]
        conn.executemany(
            """
            INSERT OR REPLACE INTO items(id, value, updated_at)
            VALUES (?, ?, ?)
            """,
            rows,
        )
        conn.commit()


def db_get(item_id):
    with state.lock:
        state.metrics.db_reads += 1
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM items WHERE id = ?", (item_id,)).fetchone()
        return None if row is None else int(row["value"])


def db_set(item_id, value):
    with state.lock:
        state.metrics.db_writes += 1
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO items(id, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (item_id, value, time.time()),
        )
        conn.commit()


def cache_key(item_id):
    return f"item:{item_id}"


def get_via_cache(item_id):
    key = cache_key(item_id)
    cached = redis_client.get(key)
    with state.lock:
        state.metrics.total_requests += 1
        state.metrics.read_requests += 1
    if cached is not None:
        with state.lock:
            state.metrics.cache_hits += 1
        return int(cached)

    with state.lock:
        state.metrics.cache_misses += 1
    value = db_get(item_id)
    if value is not None:
        redis_client.setex(key, CACHE_TTL_SECONDS, value)
    return value


def write_cache_aside(item_id, value):
    db_set(item_id, value)
    redis_client.delete(cache_key(item_id))


def write_through(item_id, value):
    redis_client.setex(cache_key(item_id), CACHE_TTL_SECONDS, value)
    db_set(item_id, value)


def write_back(item_id, value):
    redis_client.setex(cache_key(item_id), CACHE_TTL_SECONDS, value)
    with state.lock:
        state.write_back_buffer[item_id] = value
        pending = len(state.write_back_buffer)
        if pending > state.metrics.write_back_max_pending:
            state.metrics.write_back_max_pending = pending


def flush_write_back_batch():
    with state.lock:
        if not state.write_back_buffer:
            return
        items = list(state.write_back_buffer.items())
        state.write_back_buffer.clear()
        state.metrics.write_back_flush_batches += 1
        state.metrics.write_back_flush_items += len(items)

    with get_conn() as conn:
        with state.lock:
            state.metrics.db_writes += len(items)
        conn.executemany(
            """
            INSERT INTO items(id, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            [(item_id, value, time.time()) for item_id, value in items],
        )
        conn.commit()


def write_handler(item_id, value):
    with state.lock:
        state.metrics.total_requests += 1
        state.metrics.write_requests += 1
    if CACHE_STRATEGY == "cache_aside":
        write_cache_aside(item_id, value)
    elif CACHE_STRATEGY == "write_through":
        write_through(item_id, value)
    elif CACHE_STRATEGY == "write_back":
        write_back(item_id, value)
    else:
        raise ValueError(f"Unknown CACHE_STRATEGY: {CACHE_STRATEGY}")


def write_back_worker():
    while not state.stop_event.is_set():
        flush_write_back_batch()
        state.stop_event.wait(WRITE_BACK_FLUSH_SECONDS)


@app.get("/get/<int:item_id>")
def get_item(item_id: int):
    value = get_via_cache(item_id)
    if value is None:
        return jsonify({"status": "not_found"}), 404
    return jsonify({"status": "ok", "id": item_id, "value": value})


@app.post("/set/<int:item_id>")
def set_item(item_id: int):
    payload = request.get_json(silent=True) or {}
    if "value" not in payload:
        return jsonify({"error": "value is required"}), 400
    value = int(payload["value"])
    write_handler(item_id, value)
    return jsonify({"status": "ok", "id": item_id, "value": value})


@app.post("/metrics/reset")
def reset_metrics():
    with state.lock:
        state.metrics = Metrics()
        state.write_back_buffer.clear()
    redis_client.flushdb()
    return jsonify({"status": "ok"})


@app.get("/metrics")
def get_metrics():
    with state.lock:
        data = state.metrics.to_dict()
        pending = len(state.write_back_buffer)
    total_cache_accesses = data["cache_hits"] + data["cache_misses"]
    hit_rate = (data["cache_hits"] / total_cache_accesses) if total_cache_accesses else 0.0
    data["cache_hit_rate"] = round(hit_rate, 4)
    data["write_back_pending"] = pending
    data["strategy"] = CACHE_STRATEGY
    return jsonify(data)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "strategy": CACHE_STRATEGY})


def main():
    init_db()
    seed_db()
    if CACHE_STRATEGY == "write_back":
        worker = threading.Thread(target=write_back_worker, daemon=True)
        worker.start()
    app.run(host=APP_HOST, port=APP_PORT, threaded=True)


if __name__ == "__main__":
    main()
