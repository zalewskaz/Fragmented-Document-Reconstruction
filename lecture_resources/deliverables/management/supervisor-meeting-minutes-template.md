# Supervisor Consultation Meeting Minutes

> **Instructions for the Team:**
> Minutes must be prepared immediately after each consultation (within 24h at most) and sent via email to the Supervisor and all team members to prevent misunderstandings and safeguard project scope decisions (*Scope Insurance Policy*).

---

### Meeting Metadata

* **Date & Time:** October 24, 2026, 14:15–14:50
* **Location:** Room 412 MiNI WUT / MS Teams
* **Meeting Number:** Meeting 04 (Prior to Stage 2)
* **Attendees:**
  * Supervisor: Prof. Jan Promotorski, Ph.D., D.Sc., Eng.
  * Team: Alice Kowalska, Bob Nowak, Carol Wiśniewska, David Zieliński

---

### 1. Summary of Presented Progress

* Presented the microservice architecture diagram (Docker containers) and OpenAPI specification for the data ingestion module.
* Presented initial evaluation results of the baseline model (Isolation Forest) on synthetic time-series data.
* Demonstrated a user interface prototype built with React.

---

### 2. Key Decisions Made During Consultation

1. **Database technology selection:** Decided to adopt PostgreSQL with the TimescaleDB extension instead of InfluxDB due to easier relational integration with user accounts and domain data.
2. **Baseline model for Chapter 4:** Agreed that the final reference baseline in experiments will be ARIMA and a simple statistical threshold (z-score), rather than a complex LSTM model.
3. **Formal scope reduction (Scope Control):** Dropped implementation of SMS notifications in favor of Discord/Slack webhook integrations. The SMS module is deferred to the *Future Work* section of the thesis.

---

### 3. Action Items for the Next Meeting

| No. | Task                                                                  |       Assignee       |   Due Date   | Status |
| :-: | :-------------------------------------------------------------------- | :-------------------: | :----------: | :-----: |
| 1. | Implement database migrations in Docker Compose                       |       Bob Nowak       | Oct 31, 2026 |   New   |
| 2. | Prepare a test environment for multi-threaded ingestion               |   David Zieliński   | Nov 02, 2026 |   New   |
| 3. | Update the C4 diagram in Stage 2 documentation                        |    Alice Kowalska    | Nov 05, 2026 |   New   |
| 4. | **Supervisor:** Grant access account on the faculty GPU cluster | Prof. Jan Promotorski | Nov 04, 2026 | Pending |

---

### 4. Next Meeting

* **Proposed Date & Time:** November 05, 2026 (Thursday), 14:15.
* **Goal of Next Meeting:** Demonstrate working backend-frontend integration (Alpha Milestone).

---

### 5. Confirmation / Sign-Off

* [X] Summary emailed to supervisor on: October 24, 2024, 16:30
* [X] Written confirmation received from supervisor (reply email dated: October 25, 2024)
