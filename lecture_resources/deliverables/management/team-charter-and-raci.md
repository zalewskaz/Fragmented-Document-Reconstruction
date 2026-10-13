# Team Charter and Responsibility Assignment Matrix (RACI)

**Engineering / Master's Degree Project – Faculty of MIS, WUT**

---

## 1. General Project Information

* **Project Title:** *DataStream – High-Performance Streaming Analytics and Time-Series Anomaly Detection System*
* **Project Team (Group A):**
  * **Alice Kowalska** (Technical Lead / Architect) – `alice.kowalska@pw.edu.pl`
  * **Bob Nowak** (Backend / Data Engineer) – `bob.nowak@pw.edu.pl`
  * **Carol Wiśniewska** (Frontend / UX / QA) – `carol.wisniewska@pw.edu.pl`
  * **David Zieliński** (MLOps / DevOps / Performance) – `david.zielinski@pw.edu.pl`
* **Supervisor:** Prof. Jan Promotorski, Ph.D., D.Sc., Eng.
* **Laboratory Instructor:** Adam Laborancki, Ph.D., Eng.
* **Main Repository:** `https://gitlab-stud.elka.pw.edu.pl/group-project-2024/datastream`

---

## 2. Communication Rules and Tools

* **Primary Communication Channel:** Slack/Discord channel `#team-datastream` (response time on business days $\le 12$h).
* **Issue Tracker:** GitHub/GitLab Issues with Kanban board.
* **Recurring Team Sync:** Every Tuesday at 18:00 (15–30 minutes, review of previous week and blockers).
* **Supervisor Consultations:** Bi-weekly (Thursdays 14:15), preceded by sending an agenda at least 24h prior to the meeting.

---

## 3. Responsibility Assignment Matrix (RACI Matrix)

Role definitions:

* **R (Responsible):** The person completing the task (direct author of code / documentation).
* **A (Accountable):** The individual ultimately answerable for delivery quality and deadlines (**exactly 1 person per deliverable!**).
* **C (Consulted):** The subject matter expert consulted for technical input and review.
* **I (Informed):** The person kept up to date on progress and final decisions.

| Task / Deliverable                                                   |      Alice      |       Bob       |      Carol      |      David      |
| :------------------------------------------------------------------- | :-------------: | :-------------: | :-------------: | :-------------: |
| **Scope and Schedule Management (Stage 1)**                    |   **A**   |        C        |        C        |        R        |
| **Architecture Design and API Contracts (Stage 2)**            | **A / R** |        C        |        C        |        I        |
| **Ingestion Engine and Database (Stage 3)**                    |        C        | **A / R** |        I        |        R        |
| **ML Models and Anomaly Detection Pipeline (Stage 3)**         |        R        |        C        |        I        | **A / R** |
| **Client Application / UI Dashboard (Stage 4)**                |        I        |        I        | **A / R** |        C        |
| **Docker Infrastructure, CI/CD, and MiNI Lab Setup (Stage 4)** |        C        |        R        |        I        | **A / R** |
| **Performance Experiments and Benchmarks (Chapter 4)**         |        R        |        C        |        I        | **A / R** |
| **User / Deployment Manual and Final Acceptance (Stage 5)**    |   **A**   |        R        |        R        |        R        |
| **Thesis: Chapter 1 (Introduction and Literature Review)**     | **A / R** |        R        |        R        |        R        |
| **Thesis: Chapter 3 (Design and Implementation)**              |   **A**   |        R        |        R        |        R        |
| **Thesis: Chapter 4 (Evaluation and Results)**                 |        R        |        C        |        I        | **A / R** |

---

## 4. Free-Rider Escalation Protocol

To protect the entire team from negative consequences caused by a lack of commitment from any individual member, a 3-stage protocol is established:

1. **Stage I (Weeks 1–4, Internal Team Warning):**
   * If a team member fails to complete assigned tasks in 2 consecutive sprints or misses sync meetings, the lead convenes a dedicated 1-on-1 meeting.
   * A 7-day remediation plan is agreed upon and documented in the Issue Tracker.
2. **Stage II (Weeks 4–6, Notification to Supervisor):**
   * If performance does not improve, the supervisor is formally notified during the next consultation regarding critical path delays caused by lack of contribution from the individual.
3. **Stage III (Weeks 6–8, Formal Escalation to Laboratory Instructor):**
   * Before the completion of Stage 3, the matter is officially escalated to the laboratory instructor with a request for grade differentiation or removal of the student from the team prior to defense.
   * **Key Rule:** Escalating this issue late in weeks 12–15 is strictly unacceptable.

---

## 5. Team Member Signatures

* Alice Kowalska: .................................................... Date: Oct 02, 2026
* Bob Nowak: ........................................................... Date: Oct 02, 2026
* Carol Wiśniewska: ................................................ Date: Oct 02, 2026
* David Zieliński: ..................................................... Date: Oct 02, 2026
