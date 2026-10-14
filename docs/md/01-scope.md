# Stage 1 Document: Requirements Specification and Project Scope

**Engineering Project Documentation**  
**Faculty of Mathematics and Information Science**  
**Warsaw University of Technology**  

---

## 1. Document Metadata and Change History

|    Version    |    Date    |     Author     | Description of Change                                 |
| :-----------: | :--------: | :------------: | :---------------------------------------------------- |
| **1.0** | 15.10.2024 | Alice Kowalska | Baseline version for supervisor sign-off              |
| **1.1** | 18.10.2024 |   Bob Nowak   | Added quantifiable non-functional requirements (NFRs) |

* **Project Title:** *A System for Reconstructing Fragmented Documents Based on the Shape and Content of Their Parts*
* **Authors:** Martyna Sadowska, Hanna Szczerbińska, Zuzanna Zalewska
* **Supervisor:** Janusz Rafałko, Ph.D.

---

## 2. One-Sentence Engineering / Research Problem Formulation

> *“The objective of this project is to design, implement, and evaluate a software system capable of reconstructing fragmented (shredded or torn) documents based on an image of their pieces, supported by a dedicated document-splitting module for synthetic dataset generation and testing.”*

---

## 3. Project Scope: MVP vs. Future Work (Scope Management)

### 3.1. Minimum Viable Product (MVP – Passing Scope)

1. **Document Splitting Module (Module 1):** 
   - Supports single and batch mode processing.
   - Allows users to split document images using various algorithms, preview piece borders, re-generate if needed, and apply random rotations and non-overlapping background placement.
   - Saves the generated fragments locally.
2. **Document Reconstruction Module (Module 2):**
   - Extracts individual fragments from an input image (single and batch mode).
   - Reconstructs original documents using selectable or automated algorithms.
   - Displays the reconstructed output, allows iterative refinement (adjusting time/algorithm), and saves the final result locally.

### 3.2. Out of Scope (Future Work)

1. Integration with external cloud storage providers or dedicated mobile applications.

---

## 4. Functional Requirements (User Stories & Acceptance Criteria)

### **US-01: Ingestion of a Single Telemetry Data Point**

* **As an:** External system (e.g., IoT sensor / telemetry script),
* **I want to:** Submit a measurement with a timestamp and numeric value via the `POST /api/v1/metrics` endpoint,
* **So that:** The data is validated, stored in the time-series database, and forwarded to the analytical engine.

> **Acceptance Criteria (Gherkin):**
>
> * **Given:** A running and authenticated ingestion service,
> * **When:** The client sends a `POST` request with a valid JSON payload `{ "sensor_id": "temp-01", "timestamp": 1729000000, "value": 24.5 }`,
> * **Then:** The system returns response status `201 Created` in $\le 50$ ms, and the record is persisted in the TimescaleDB hypertable.
> * **Scenario (Invalid data):**
> * **When:** The client sends a request with a negative timestamp or a missing `value` field,
> * **Then:** The system rejects the request with HTTP `422 Unprocessable Entity` containing a detailed validation error message.

---

### **US-02: Viewing Time-Series Chart with Flagged Anomalies**

* **As an:** Operations engineer / data analyst,
* **I want to:** Open the chart view for a selected sensor covering the last 24 hours with highlighted anomalies,
* **So that:** I can quickly diagnose equipment faults across infrastructure.

> **Acceptance Criteria (Gherkin):**
>
> * **Given:** A user logged in to the web dashboard,
> * **When:** The user selects sensor `sensor_id="temp-01"` and time window `24h` from the menu,
> * **Then:** The line chart renders in $< 1.0$ s with anomalous points highlighted in red.

---

## 5. Quantifiable Non-Functional Requirements (NFRs)

|        ID        | Category                             | Target Quantifiable Metric                                                                                                                           | Verification Method             |
| :--------------: | :----------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------ |
| **NFR-01** | **Response Time (Latency)**    | 95% of write and read requests respond in$< 200$ ms under a load of 50 concurrent virtual users.                                                   | k6 / Locust load benchmark      |
| **NFR-02** | **Throughput**                 | Ingestion engine processes$\ge 5\,000$ events/second on a 4-core machine with 16 GB RAM.                                                           | Locust stress test              |
| **NFR-03** | **Resource Utilization**       | Total idle RAM consumption of the container stack$\le 2.0$ GB; analytical model runs in CPU memory without GPU requirements.                       | `docker stats`                |
| **NFR-04** | **Deployment Reproducibility** | Complete deployment and startup of a clean environment using`docker compose up --build` completes in $< 3$ minutes on a MiNI lab Ubuntu machine. | Stopwatch / installation script |
| **NFR-05** | **Reliability**                | 0 unhandled HTTP 500 exceptions on malformed input data; automated database reconnection retries in containers.                                      | pytest integration test suite   |

---

## 6. Glossary

| Term                                      | Definition                                                                                                                                                                                    |
| :---------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **APD (Archiwum Prac Dyplomowych)** | University Thesis Archive; official web portal of Warsaw University of Technology used for thesis submission, anti-plagiarism verification, and archiving.                                    |
| **Hypertable**                      | A TimescaleDB abstraction that presents time-series data as a single continuous PostgreSQL table while transparently partitioning it into time-based chunks under the hood.                   |
| **Isolation Forest**                | An unsupervised machine learning algorithm for anomaly detection that isolates observations by randomly selecting a feature and split value, where anomalies require fewer splits to isolate. |
| **MVP (Minimum Viable Product)**    | The minimal functional scope of the project fulfilling all foundational requirements for academic project evaluation and defense.                                                             |
| **p95 Latency**                     | The 95th percentile of response time distribution, indicating that 95% of all incoming requests are served in less than the specified duration.                                               |
| **Rolling Z-Score**                 | A localized statistical metric representing the number of standard deviations a given observation deviates from the moving mean over a sliding temporal window.                               |
| **Telemetry**                       | Automated remote collection and transmission of operational measurement data from distributed sensors or agents to a central receiving station.                                               |

---

## 7. Preliminary Risk Register and Role Allocation

*(Detailed Risk Register and RACI Matrix are defined in dedicated documents: [`management/risk-register-and-contingency.md`](../management/risk-register-and-contingency.md) and [`management/team-charter-and-raci.md`](../management/team-charter-and-raci.md).)*

---

## 8. Formal Supervisor Acceptance

* [X] **Scope and MVP Sign-off:** The supervisor has reviewed the requirements specification and approves the MVP scope as the foundation for the engineering / master's degree project.

**Supervisor Signature:** ............................................................ **Date:** October 18, 2026
