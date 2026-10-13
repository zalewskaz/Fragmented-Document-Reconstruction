# Stage 4 Document: Subsystem Integration & Alpha Release

**Engineering / Master's Degree Project – Faculty of MIS, WUT**

---

## 1. Scope of Integration and Alpha Release Status

The Alpha release integrates all application subsystems into a coherent multi-container environment:

* **Frontend SPA (React):** Integrated with the backend API; displays telemetry data in real time via a WebSocket connection.
* **Backend API:** Connected to the TimescaleDB database and Redis buffer; supports JWT authentication and authorization.
* **Analytics Worker:** Processes streams asynchronously, writing performance metrics and anomalies.
* **CI/CD Pipeline (GitHub Actions):** Automatically builds Docker images and executes the full suite of integration tests on every Pull Request.

---

## 2. Integration Test Report in CI

The integration test suite verifies component collaboration with real database instances and the Redis broker running inside test containers:

```
============================= test session starts ==============================
platform linux -- Python 3.11.8, pytest-8.1.1
plugins: anyio-4.3.0, asyncio-0.23.6
collected 18 items

tests/integration/test_database_persistence.py ....                     [ 22%]
tests/integration/test_redis_pubsub_pipeline.py .....                    [ 50%]
tests/integration/test_api_auth_flow.py ........                         [ 94%]
tests/integration/test_end_to_end_alerting.py .                          [100%]

============================== 18 passed in 6.12s ==============================
```

---

## 3. Alpha Release Demonstration Protocol before Supervisor

* **Demonstration Date:** December 12, 2024
* **Demo Scenario:**
  1. Boot up the entire stack using `docker compose up -d` on a clean machine.
  2. User login via the React dashboard and create a new sensor stream: `sensor-alpha-001`.
  3. Start the traffic generator script (100 measurements/s).
  4. Live chart demonstration showing instant flagging of injected anomalies.
  5. Verify no errors in container logs (`docker compose logs`).
* **Supervisor Feedback & Notes:**
  * System operates stably; ensure a clearer color legend on charts for the final version (optimized for black-and-white printing in the thesis).

---

## 4. Feature Freeze Protocol

In accordance with the schedule, effective **December 20, 2024 (Week 12)**, **Feature Freeze** enters into effect in the repository:

1. Complete freeze on introducing new features and modifying architecture.
2. Development work strictly limited to critical bug fixes and optimization.
3. Full team focus on:
   * Conducting benchmark experiments for Chapter 4 of the thesis,
   * Writing and editing the thesis text in \LaTeX,
   * Preparing the 1-page installation guide for the laboratory.

---

**Supervisor Signature (Alpha Version Approval):** ............................................ **Date:** December 15, 2026
