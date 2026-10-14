# Stage 3 Document: Core System Implementation & Progress Report

**Engineering / Master's Degree Project – Faculty of MIS, WUT**

---

## 1. Implementation Progress and Repository Status

* **Main branch (`main`) status:** Stable, passing all CI tests.
* **Commit count in period:** 64 commits, 14 merged Pull Requests.
* **Unit test code coverage:** 78% line coverage in backend and analytics modules.

---

## 2. Completed Core Components

### 2.1. Data and Ingestion Layer (Backend)

* Implemented asynchronous FastAPI endpoints (`/api/v1/metrics`, `/api/v1/sensors`) with full Pydantic V2 schema validation.
* Configured automated database migrations using `Alembic` and hypertable partitioning in TimescaleDB.
* Created stream buffering in Redis Streams to prevent database blocking under traffic spikes.

### 2.2. Anomaly Detection Engine (ML Engine)

* Developed the analytical pipeline module based on `scikit-learn` and `NumPy`.
* Implemented two analytical algorithms:
  1. **Statistical Rolling Z-Score:** Immediate detection of value spikes.
  2. **Isolation Forest Model:** Detection of multidimensional contextual anomalies.
* Ensured calculation determinism via a fixed generator seed (`random_state=42`).

---

## 3. First Working End-to-End Trace

Verified the complete data flow (End-to-End Trace) inside Docker containers:

1. Simulation script sends 100 telemetry points with an intentionally injected temperature anomaly ($T = 95^\circ\text{C}$).
2. Ingestion module accepts the payload within 18 ms and pushes it to the Redis queue.
3. Analytics worker retrieves the record, computes the anomaly score ($score = 0.89 > threshold$), flags `is_anomaly=true`, and persists to the database.
4. The `GET /api/v1/metrics/anomalies` query immediately returns the flagged record with its timestamp and value.

---

## 4. Unit Test Report

```
============================= test session starts ==============================
platform linux -- Python 3.11.8, pytest-8.1.1
rootdir: /app, configfile: pyproject.toml
collected 42 items

tests/unit/test_schemas.py .........                                     [ 21%]
tests/unit/test_ingestion_service.py ............                         [ 50%]
tests/unit/test_anomaly_detector.py ...............                       [ 85%]
tests/unit/test_auth.py ......                                            [100%]

============================== 42 passed in 1.48s ==============================
```

---

## 5. Adherence to Schedule and Critical Path

| Scheduled Task (W06–W08)          |           Status           | Notes and Potential Delays                  |
| :--------------------------------- | :-------------------------: | :------------------------------------------ |
| DB migrations & TimescaleDB schema | **100% (Completed)** | Delivered according to plan                 |
| Asynchronous FastAPI ingestion     | **100% (Completed)** | Measured throughput:$> 4\,000$ req/s      |
| Isolation Forest implementation    | **100% (Completed)** | Memory usage optimized                      |
| React UI skeleton                  | **80% (In Progress)** | Minor delay with no impact on critical path |

---

**Supervisor Signature (Stage 3 Acceptance):** ............................................ **Date:** November 22, 2026
