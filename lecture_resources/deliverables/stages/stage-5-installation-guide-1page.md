# 1-Page System Installation & Deployment Guide (A4 Rapid Guide)

**DataStream System – Faculty of MIS, WUT**

> **For Reviewer and Laboratory Instructor:** This guide enables deploying and launching the complete, fully operational system on a clean machine in under **5 minutes**.

---

### 1. Prerequisites

Before running, ensure the following are installed on the host machine:

* **Docker Engine** (version $\ge 24.0$) and **Docker Compose** (version $\ge 2.20$)
* **Git** (version $\ge 2.30$)
* Free available ports: `8000` (API) and `3000` (Frontend UI)

---

### 2. Quick Start Procedure (3 Steps)

#### Step 1: Clone the repository

```bash
git clone https://gihub.com/group-project-2024/datastream.git
cd datastream
```

#### Step 2: Prepare configuration file

```bash
cp .env.example .env
```

*(Default values in `.env` are pre-configured for instant startup without modifications).*

#### Step 3: Build and start containers

```bash
docker compose up --build -d
```

*Initial image pull and build time: approx. 90–120 seconds.*

---

### 3. Service Access and Health Verification

| Service                                    | URL / Port                       | Default Credentials                    | Description                        |
| :----------------------------------------- | :------------------------------- | :------------------------------------- | :--------------------------------- |
| **Application Dashboard (Frontend)** | `http://localhost:3000`        | `admin@datastream.pw` / `admin123` | Interactive analytics dashboard    |
| **API Documentation (Swagger)**      | `http://localhost:8000/docs`   | Not required                           | Interactive endpoint catalog       |
| **Service Healthcheck**              | `http://localhost:8000/health` | Not required                           | Returns`{ "status": "healthy" }` |

---

### 4. Demo Data Ingestion

To populate the system with a sample telemetry stream containing injected anomalies:

```bash
docker compose exec api python scripts/seed_demo_stream.py --rate 50 --count 1000
```

After executing the script, refresh the chart view in your browser at `http://localhost:3000`.

---

### 5. Running Automated Test Suite

```bash
docker compose exec api pytest tests/ -v
```

---

### 6. Teardown and Environment Cleanup

```bash
docker compose down -v
```

*(The `-v` flag removes database volumes, restoring a clean state).*
