# Traffic Rules Violation Detection — Project Report
### Big Data Streaming Architecture with Apache Kafka & Apache Spark

---

## 1. Project Overview

This project implements a **real-time, distributed traffic rules violation detection system**. The system captures live video frames from traffic cameras, streams them through a Big Data pipeline, applies computer vision algorithms to detect violations, stores the results in MongoDB, and presents them through a purpose-built web dashboard.

The system is built entirely on a **Big Data Streaming architecture** — a fully distributed pipeline using Apache Kafka and Apache Spark Structured Streaming, where video frames are processed in parallel across a streaming architecture and results are visualised in real time via a Flask web dashboard.

---

## 2. System Architecture (Big Data Mode)

```
┌─────────────────────────────────────────────────────────────────┐
│                        BIG DATA PIPELINE                        │
│                                                                 │
│  [Traffic Video]                                                │
│       │                                                         │
│       ▼                                                         │
│  [Kafka Producer]  ──────────────────────────────────────────►  │
│  video_producer.py                                              │
│  • Reads video frames                 [Apache Kafka]            │
│  • Encodes to JPEG → Base64           Topic: traffic-stream     │
│  • Sends to Kafka topic               4 Partitions              │
│  • Includes light state (Red/Green)                             │
│                                            │                    │
│                                            ▼                    │
│                                   [Apache Spark]                │
│                                   stream_processor.py           │
│                                   • Reads micro-batches         │
│                                   • Applies detection logic     │
│                                   • foreachBatch processing     │
│                                            │                    │
│                                            ▼                    │
│                                      [MongoDB]                  │
│                                   Database: traffic_db          │
│                                   Collection: violations        │
│                                            │                    │
│                          ┌─────────────────┴──────────────────┐ │
│                          ▼                                     ▼ │
│                  [Mongo Express]                  [Flask Dashboard] │
│                  http://localhost:8081            http://localhost:5000 │
│                  Raw admin / table view           Live violation cards │
│                                                  Stats + Ticket PDF  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Big Data Tools Used

### 3.1 Apache Kafka
- **Role:** Real-time message broker / distributed streaming platform
- **Version:** Confluent Kafka 7.4.0 (via Docker)
- **What it does:** Receives video frames from camera producers and queues them for Spark to consume. Acts as the backbone of the streaming pipeline.
- **Topic:** `traffic-stream`
- **Partitions:** 4 (one per camera; same camera always goes to same partition via message key)
- **Message format:** JSON `{ camera_id, timestamp, frame_data (base64 JPEG), light (Red/Green) }`
- **Why Kafka?** Kafka handles millions of messages per second, decouples producers from consumers, and guarantees ordered delivery per partition — critical for stateful frame-by-frame detection.

### 3.2 Apache Zookeeper
- **Role:** Cluster coordination service for Kafka
- **Version:** Confluent Zookeeper 7.4.0 (via Docker)
- **What it does:** Manages Kafka broker metadata, leader election, and topic partition state. Kafka cannot function without Zookeeper.

### 3.3 Apache Spark Structured Streaming
- **Role:** Distributed stream processing engine
- **Version:** Spark 3.5.8 with Hadoop 3 (local installation) + PySpark 3.5.x
- **What it does:** Subscribes to the Kafka topic, reads frames in micro-batches (10 frames per trigger), applies the violation detection logic, and outputs results.
- **Processing pattern:** `foreachBatch` — each micro-batch is processed as a Python function, enabling stateful per-camera processing without UDF serialization overhead.
- **Why Spark?** Spark enables horizontally scalable, fault-tolerant stream processing. In a real deployment, it can run across hundreds of machines simultaneously, processing thousands of camera feeds in parallel.

### 3.4 MongoDB
- **Role:** NoSQL document database for storing violation records
- **Version:** MongoDB 8.2.5 (via Docker)
- **Database:** `traffic_db`
- **Collection:** `violations`
- **Stored fields:** `camera_id`, `violation_type`, `timestamp`, `detected_at`, `snapshot_size`
- **Why MongoDB?** Violations are semi-structured data (different fields for different camera types). MongoDB's flexible schema handles this perfectly, unlike rigid SQL tables.

### 3.5 Mongo Express
- **Role:** Web-based MongoDB admin UI
- **URL:** `http://localhost:8081`
- **What it does:** Provides a raw table view of all stored violation documents directly in the browser, useful for quick database inspection.

### 3.6 Flask Web Dashboard
- **Role:** Purpose-built, real-time violation monitoring web application
- **Framework:** Flask 3.x (Python micro web framework)
- **URL:** `http://localhost:5000`
- **Entry point:** `dashboard/app.py`
- **What it does:**
  - Serves a dark-themed, auto-refreshing (every 5 seconds) dashboard that reads live violation data from MongoDB.
  - Displays **4 live stat counters**: Total Violations, Red Light Crossings, Wrong Direction events, Active Cameras.
  - Shows each violation as a **card** with: camera ID badge, violation type badge, detected timestamp, snapshot thumbnail (cropped vehicle image), and snapshot size.
  - Provides a **"Generate Ticket"** button per violation that opens a printable HTML ticket (`/ticket/<id>`) in a new tab.
  - Exposes a REST JSON API (`/api/violations`, `/api/stats`, `/api/violation/<id>`) that any frontend or script can consume.
  - Streams vehicle **snapshot images** directly from MongoDB Base64 fields via the `/api/violation/<id>/image` endpoint.
  - Shows a live **connection status indicator** (green = MongoDB reachable, red = unreachable).
- **Why Flask?** Lightweight, zero-configuration Python web server that integrates natively with PyMongo. No frontend build step required — pure HTML/CSS/JS rendered by Jinja2 templates.

### 3.7 Docker & Docker Compose
- **Role:** Containerization and infrastructure orchestration
- **What it does:** Runs Zookeeper, Kafka, MongoDB, and Mongo Express as isolated containers with a single command (`docker-compose up -d`). Eliminates installation complexity and ensures reproducibility.

---

## 4. Non-Big-Data Tools & Libraries

| Tool | Purpose |
|------|---------|
| **Python 3.11** | Primary programming language |
| **OpenCV (cv2)** | Computer vision: frame decoding, background subtraction, contour detection |
| **NumPy** | Array operations for image data |
| **kafka-python** | Python Kafka producer client |
| **pymongo** | Python MongoDB client |
| **Flask 3.x** | Web framework for the real-time violation monitoring dashboard |

---

## 5. ML / Computer Vision Models Used

> **Important clarification for the presentation:** This system does **not** use deep learning (no neural networks, no YOLO, no TensorFlow). It uses **classical computer vision algorithms**, which are model-based rather than data-trained. Below is an honest and accurate description.

### 5.1 Gaussian Mixture Model — Background Subtraction (MOG2)
- **Algorithm:** `cv2.createBackgroundSubtractorMOG2()`
- **What it is:** A statistical machine learning algorithm that models each pixel's colour distribution as a mixture of Gaussians. It learns the "background" of a scene over time and identifies any pixel that doesn't fit the background model as a "foreground" object (i.e., a moving vehicle).
- **Used for:** `cam_01`, `cam_02`, `cam_03` (Red Light Crossing detection)
- **How it works:**
  1. For each new frame, MOG2 compares every pixel against its learned background model.
  2. Pixels that deviate significantly are marked as foreground (white in a binary mask).
  3. The mask reveals moving cars as bright blobs.

### 5.2 Contour Detection & Morphological Operations
- **Algorithm:** `cv2.findContours()` + `cv2.morphologyEx()` + Gaussian Blur
- **What it is:** Classical image processing that finds the outlines (contours) of connected foreground regions in the binary mask from MOG2.
- **Used for:** Identifying individual vehicle blobs from the background-subtracted image.

### 5.3 Centroid-Based Object Tracking
- **What it is:** A simple but effective tracking algorithm that assigns each detected vehicle contour a unique ID and tracks its position across frames using Euclidean distance.
- **Used for:** `cam_04` — Direction Violation Detection. Tracks each vehicle's trajectory across frames to determine which direction it is moving.

### 5.4 Virtual Tripwire / Zone-Based Detection
- **What it is:** A rule-based geometric method, not a learned model. Two virtual zones (coordinates) are defined in the video frame. When a vehicle's bounding box centroid crosses from one zone into another, a rule is evaluated.
- **Used for:**
  - `cam_01/02/03`: If a vehicle's centroid is between Zone 1 and Zone 2 **while the light is Red** → Violation.
  - `cam_04`: If a vehicle's centroid crosses the tripwire going in the **wrong direction** → Violation.

---

## 6. How Violation Detection Works

### 6.1 Red Light Crossing (`cam_01`, `cam_02`, `cam_03`)

**Step-by-step process:**

1. **Frame arrives** at Spark via Kafka. Each frame is a JPEG image encoded as Base64 text.
2. **Frame is decoded** back to a NumPy image array using OpenCV.
3. **Background Subtraction (MOG2)** processes the frame. After seeing ~10–20 frames, it has learned what the road looks like when empty. Any moving vehicle now appears as a bright white region.
4. **Contour detection** finds each vehicle's bounding box `(x, y, width, height)`.
5. **Zone check:** The system checks if the vehicle's centre point (centroid) falls between two predefined coordinates — the "stop line zone":
   - Zone 1: x=100, y=150 (left boundary)
   - Zone 2: x=450, y=145 (right boundary)
6. **Light state check:** The producer sends `"light": "Red"` in every Kafka message. The stream processor applies this to the camera processor before detection.
7. **If BOTH conditions are true** (vehicle in zone AND light is Red) → **VIOLATION RECORDED.**

**What appears in the terminal:**
```
Batch 11 — 1 VIOLATION(S) DETECTED!
  Camera : cam_01
  Time   : 1773142167.65
  Type   : Red Light Crossing
  Snapshot: [base64 image, length=12688]
```
The snapshot is a cropped image of the offending vehicle, encoded as Base64. It gets saved to MongoDB alongside the violation record.

### 6.2 Wrong Direction (`cam_04`)

1. MOG2 detects moving vehicles as foreground blobs.
2. Each blob is assigned a unique ID and its centroid position is tracked frame-by-frame.
3. The system records whether each vehicle's centroid crosses the virtual tripwire going **up** (correct) or **down** (wrong direction).
4. Going down = **Wrong Direction violation.**

**Terminal output:**
```
ID: 3 crossed going down at Tue Mar 10 17:52:44 2026
Batch 12 — 1 VIOLATION(S) DETECTED!
  Camera : cam_04
  Type   : Wrong Direction
```

---

## 7. Accuracy of Results

### Honest Assessment
Since this system uses rule-based classical computer vision (not a trained classifier), **"accuracy" is defined differently from supervised ML:**

| Metric | Description |
|--------|-------------|
| **True Positive** | Vehicle actually crossed → system detected it |
| **False Positive** | Camera noise or shadow → incorrectly flagged as violation |
| **False Negative** | Vehicle crossed but was missed (e.g., covered by another car) |

### Factors Affecting Accuracy

| Factor | Effect |
|--------|--------|
| **Lighting conditions** | MOG2 is sensitive to sudden light changes (clouds, headlights at night) |
| **Camera angle** | Works best with overhead/angled views where vehicle bounding boxes don't overlap |
| **Threshold tuning** | The `thres` parameter (area threshold ~30px² for cam_01) filters out small false-positive blobs |
| **Background learning** | Accuracy improves after ~10–20 frames as MOG2 stabilises its background model |

### Practical Performance
- **Red Light Crossing:** High precision on clear daytime video. One violation is detected per genuine crossing event, not per frame — the contour must remain in the zone across multiple frames.
- **Wrong Direction:** Depends on vehicle speed and tracking stability. Works correctly for clearly separated vehicles.
- **False positive rate:** Very low on the provided test videos due to well-tuned thresholds.

> **Note to teacher:** The accuracy cannot be expressed as a percentage without a labelled ground-truth dataset. However, live demonstration on the provided videos consistently shows correct detection events matching observable vehicle movements.

---

## 8. How to Interpret Results

The system produces evidence across three layers:

### Terminal Evidence
```
[cam_01] Sent 690 frames to Kafka...   ← Producer: frames are being streamed
[Batch 11] Processed 10 frame(s)...    ← Spark: consuming in micro-batches
Batch 11 — 1 VIOLATION(S) DETECTED!   ← Detection event
  Camera : cam_01                      ← Which camera
  Time   : 1773142167.65              ← Unix timestamp of the event
  Type   : Red Light Crossing          ← Nature of violation
  Snapshot: [base64 image, length=12688] ← Car image was captured
[MongoDB] Saved 1 violation(s)...     ← Persisted to database
```

### Flask Dashboard Evidence
Open `http://localhost:5000`:
- **Stats bar** shows live counters: total violations, red-light count, wrong-direction count, active cameras
- Each violation appears as a **card** with camera ID, violation type badge, timestamp, and vehicle snapshot thumbnail
- Click **"Generate Ticket"** to open a formatted printable ticket for that violation
- The dashboard auto-refreshes every 5 seconds, so new detections appear without reloading

### MongoDB Evidence
Open `http://localhost:8081` → `traffic_db` → `violations`:
- Each document is one detected violation event
- The `detected_at` field shows real wall-clock time, proving real-time detection

---

## 9. What Makes This a "Big Data" Project

| Characteristic | How This Project Demonstrates It |
|---|---|
| **Volume** | Each video frame is ~50KB. At 25 FPS across 4 cameras = ~5 MB/second continuous data |
| **Velocity** | Real-time streaming via Kafka; Spark processes micro-batches every few seconds |
| **Variety** | Multi-camera feeds with different violation types; image + metadata in one stream |
| **Scalability** | 4 Kafka partitions = 4 cameras in parallel. Adding more brokers/workers scales linearly |
| **Fault Tolerance** | Spark checkpointing resumes from the last processed offset if the processor restarts |
| **Distributed Processing** | Spark can run across multiple nodes; single-machine here for demo, same code works on a cluster |

---

## 10. File & Component Structure

```
Traffic-Rules-Violation-Detection/
│
├── producer/
│   └── video_producer.py       — Kafka producer: reads video, streams frames
│
├── spark/
│   └── stream_processor.py     — Spark consumer: processes frames, detects violations
│
├── core/
│   └── detector.py             — Headless detection module for Spark workers
│
├── processor/
│   ├── MainProcessor.py        — Per-camera processor manager
│   ├── TrafficProcessor.py     — Red light crossing detection (MOG2 + contours)
│   └── violation_detection.py  — Wrong direction detection (centroid tracking)
│
├── dashboard/
│   ├── app.py                  — Flask web server: REST API + dashboard routes
│   └── templates/
│       ├── index.html          — Live violation monitoring dashboard (dark UI)
│       └── ticket.html         — Printable violation ticket template
│
├── docker-compose.yml          — Infrastructure: Kafka, Zookeeper, MongoDB, Mongo Express
└── requirements_bigdata.txt    — Python dependencies
```

---

## 11. How to Run (Demo Steps)

```bash
# Step 1: Start infrastructure
docker-compose up -d

# Step 2: Start Spark consumer (Terminal 1)
venv\Scripts\activate
python spark\stream_processor.py

# Step 3: Start video producer — Red light (Terminal 2)
venv\Scripts\activate
python producer\video_producer.py --cam cam_01 --video videos\video7.mp4 --light red

# Step 4: Start cam_04 — Direction violations (Terminal 3)
venv\Scripts\activate
python producer\video_producer.py --cam cam_04 --video videos\traffic.avi

# Step 5: Start the Flask Dashboard (Terminal 4)
venv\Scripts\activate
python dashboard\app.py
# Open: http://localhost:5000
# → Live violation cards auto-refresh every 5 seconds
# → Click "Generate Ticket" on any card to open a printable ticket

# Step 6 (optional): Raw database view via Mongo Express
# Open: http://localhost:8081 → traffic_db → violations
```

---

## 12. Summary of Technologies

| Layer | Technology |
|---|---|
| **Data Ingestion** | Apache Kafka 7.4.0 |
| **Stream Processing** | Apache Spark 3.5.8 (PySpark) |
| **Cluster Coordination** | Apache Zookeeper 7.4.0 |
| **Storage** | MongoDB 8.2.5 |
| **Live Web Dashboard** | Flask 3.x + HTML/CSS/JS (port 5000) |
| **Raw DB Monitor** | Mongo Express (port 8081) |
| **Infrastructure** | Docker + Docker Compose |
| **Computer Vision** | OpenCV 4.x (MOG2, contours, centroid tracking) |
| **Language** | Python 3.11 |
| **Frame Transport Format** | JSON + Base64-encoded JPEG over Kafka |

---

*Report prepared: March 2026*  
*Project: Big Data — Real-Time Distributed Traffic Violation Detection*
