# Отчет: сравнение стратегий кеширования

## Цель работы

Сравнить три стратегии кеширования в одинаковых условиях:

- `Lazy Loading / Cache-Aside`
- `Write-Through`
- `Write-Back`

## Состав стенда

- `application`
- `cache`: Redis
- `БД`: SQLite 
- `load-generator`
- `оркестратор тестов`: `run_benchmarks.py`

## Реализованные стратегии

### 1) Lazy Loading / Cache-Aside

- чтение: сначала из Redis;
- если нет нужных данных в Redis: чтение из БД и запись в кеш;
- запись: сразу в БД, ключ в кеше инвалидируется.

### 2) Write-Through

- чтение: через кеш;
- запись: синхронно и в кеш, и в БД.

### 3) Write-Back

- чтение: через кеш;
- запись: сначала в кеш и буфер;
- запись в БД: отложенно, батчами фоновым worker-ом.

## Единый тест для всех стратегий

Для всех трех стратегий использовался один и тот же сценарий:

- одинаковый key-space (1000 ключей);
- одинаковые параметры генератора: `workers=20`, `duration=20s`;

Профили:
- `read-heavy`: `80% read / 20% write`;
- `balanced`: `50% read / 50% write`;
- `write-heavy`: `20% read / 80% write`.

## Метрики

Собирались обязательные метрики:

- `throughput` (`req/sec`);
- `avg latency` (`ms`);
- `количество обращений в БД` (`db_accesses = db_reads + db_writes`);
- `cache hit rate`.

Дополнительно для `Write-Back`:

- `write_back_max_pending` (максимальный размер буфера отложенных записей);
- `write_back_flush_batches` (число батчей сброса в БД).

## Таблица результатов

| strategy | profile | throughput_req_sec | avg_latency_ms | db_accesses | cache_hit_rate | write_back_max_pending | write_back_flush_batches |
|---|---:|---:|---:|---:|---:|---:|---:|
| cache_aside | read_heavy | 552.35 | 36.20 | 4551 | 0.7293 | 0 | 0 |
| cache_aside | balanced | 422.30 | 47.45 | 6501 | 0.4571 | 0 | 0 |
| cache_aside | write_heavy | 294.55 | 68.13 | 5676 | 0.1764 | 0 | 0 |
| write_through | read_heavy | 515.50 | 38.79 | 2832 | 0.9032 | 0 | 0 |
| write_through | balanced | 376.15 | 53.28 | 4251 | 0.8732 | 0 | 0 |
| write_through | write_heavy | 289.50 | 69.24 | 4875 | 0.8206 | 0 | 0 |
| write_back | read_heavy | 445.80 | 44.84 | 2482 | 0.8886 | 109 | 19 |
| write_back | balanced | 469.45 | 42.56 | 4486 | 0.8912 | 313 | 18 |
| write_back | write_heavy | 456.85 | 43.76 | 5980 | 0.9017 | 389 | 18 |

## Анализ результатов

### Для чтения (read-heavy)

- лучший throughput: `cache_aside` (552.35 req/s);
- минимальная задержка: `cache_aside` (36.20 ms);
- минимальные обращения в БД: `write_back` (2482);
- наибольший hit rate: `write_through` (0.9032).

Вывод: для данного стенда по скорости чтения лидирует `cache_aside`, но по разгрузке БД и hit rate сильнее `write_through`/`write_back`.

### Для записи (write-heavy)

- лучший throughput: `write_back` (456.85 req/s);
- минимальная задержка: `write_back` (43.76 ms);
- `cache_aside` и `write_through` существенно медленнее (около 290 req/s).

Вывод: при доминирующих записях явный лидер — `write_back`, так как запись не блокируется синхронной операцией в БД.

### Для смешанной нагрузки (balanced)

- лучший throughput: `write_back` (469.45 req/s);
- минимальная задержка: `write_back` (42.56 ms);
- `cache_aside` опережает `write_through`, но уступает `write_back`.

Вывод: для mixed-нагрузки в этом тесте оптимален `write_back`.

## Что происходит в Write-Back при накоплении записей

По мере роста доли записи растет максимальный размер буфера:

- `read-heavy`: `write_back_max_pending = 109`;
- `balanced`: `write_back_max_pending = 313`;
- `write-heavy`: `write_back_max_pending = 389`.

Число батчей flush остается близким (`18-19`), но в каждом батче становится больше записей. Это подтверждает характер `write-back`: рост буфера и пакетный сброс в БД.

## Итоговые выводы

- **Для чтения:** в этом эксперименте по скорости чтения лучший `cache_aside`, но по hit rate и DB offload сильны `write_through`/`write_back`.
- **Для записи:** лучший `write_back`.
- **Для смешанной нагрузки:** лучший `write_back`.
- **Практический компромисс:**  
  - `write_through` — предсказуемая консистентность кеша и высокий hit rate;  
  - `write_back` — максимум производительности на write-heavy, но с отложенной записью и риском потери буфера при сбое;  
  - `cache_aside` — простая и понятная схема, но хуже при частых записях.

###Скрин из консоли:
image.png
