# Stage 5 Document: Final Delivery & Acceptance Package

**Engineering / Master's Degree Project – Faculty of MIS, WUT**

---

## 1. Final Checklist

| Acceptance Requirement                                   |    Status    | Evidence of Verification                                                                                              |
| :------------------------------------------------------- | :-----------: | :-------------------------------------------------------------------------------------------------------------------- |
| **Working application in the MiNI laboratory**     | **MET** | Application launched and demonstrated on a laboratory computer.                                                       |
| **Complete acceptance tests (MVP)**                | **MET** | All User Stories scenarios from Stage 1 successfully validated live.                                                  |
| **1-page installation guide (A4)**                 | **MET** | File[`stage-5-installation-guide-1page.md`](stage-5-installation-guide-1page.md) included in repository and printed. |
| **Green CI/CD pipeline status**                    | **MET** | All unit tests, integration tests, and linters pass in GitHub Actions.                                                |
| **Source code sanitized of secrets and artifacts** | **MET** | No binaries, credentials, or`.env` files in Git history; `pre-commit` hooks configured.                           |

---

## 2. Acceptance Test Report (User Stories Verification)

|       ID       | Acceptance Scenario Description                               |   Test Result   | Response Time |
| :-------------: | :------------------------------------------------------------ | :--------------: | :-----------: |
| **US-01** | Ingestion of a single metric and JSON schema validation       | **PASSED** |     22 ms     |
| **US-02** | Time-series chart visualization with anomaly indicators       | **PASSED** |    410 ms    |
| **US-03** | Notification rule configuration and Webhook alert dispatch    | **PASSED** |     85 ms     |
| **US-04** | Telemetry data export to CSV format                           | **PASSED** |    180 ms    |
| **US-05** | Malformed payload handling (HTTP 422 validation, no DB crash) | **PASSED** |     12 ms     |

---

## 3. Application Quality Assessment Protocol (Completed by Supervisor)

* **Project Title:** *DataStream – High-Performance Streaming Analytics and Anomaly Detection System for Time-Series Data*
* **Authors:** Alice Kowalska, Bob Nowak, Carol Wiśniewska, David Zieliński
* **Supervisor:** Prof. Jan Promotorski, Ph.D., D.Sc., Eng.

### Application Evaluation Criteria (Max 30 points):

1. **Scope compliance and engineering innovativeness (0–10 pts):** ........... pts
2. **Architecture quality, code cleanliness, and tests (0–10 pts):** ........... pts
3. **Deployment reproducibility, stability, and UI ergonomics (0–10 pts):** ........... pts

* **Total Application Quality Score:** **............ / 30 points**

**Supervisor Evaluation Justification:**

> ....................................................................................................................................................
> ....................................................................................................................................................

---

**Supervisor Signature:** ............................................................ **Date:** ..............................
