# ⚓ Seabot: Fully Offline Maritime RAG Chatbot

Seabot is an **air-gapped, zero-internet Retrieval-Augmented Generation (RAG) assistant** engineered specifically for maritime vessel operations. It allows ship officers, marine engineers, and crew to query vessel technical manuals, emergency checklists, safety management systems, and bunkering spreadsheets with 100% data privacy and verifiable citations.

---

## 🌟 Key Features

- **Strict Grounding & Traceability:** Answers are derived **ONLY** from uploaded documents. If information is absent, Seabot responds with an exact NOT-FOUND notification.
- **Deep-Linked In-App Viewer:** Every factual assertion cites a source tag (e.g., `[S1]`, `[S2]`). Clicking a source chip opens the internal PDF / Excel viewer at the exact cited page with passage coordinates highlighted.
- **Multimodal Diagram Understanding:** Ingests P&ID schematics, electrical wiring drawings, and piping layouts using Gemma 4 vision with technical label extraction and Tesseract OCR verification.
- **Fast Session Persistence:** Recovers exact chat history, unsent drafts, scroll positions, and active document views across browser refreshes in under 1 second.
- **Audited History & Privacy:** Full audit trail for data operations. Support for selective history clearing (Last hour, Today, Last 7 days, All time).
- **Air-Gapped by Design:** Zero CDNs, zero remote fonts, zero external telemetry. Runs completely local via Docker Compose or native services.

---

## 💻 Hardware Profiles & Resource Sizing

Configure your hardware profile in `.env`:

| Profile | Target Machine | Recommended Model | RAM / VRAM Req | First Token Latency |
|---|---|---|---|---|
| **LOW** | 8 GB Core i5 / laptop | `gemma4:4b` | 8 GB RAM | ~3–5s |
| **STANDARD** (Default) | 16 GB Core i7 vessel laptop | `gemma4:12b` (Q4) | 16 GB RAM | < 3s |
| **HIGH** | Vessel server / GPU rack | `gemma4:27b` / `31b` | 24+ GB VRAM | < 1s |

---

## 🚢 Offline Pre-Deployment Preparation (While in Port)

Before departing shore with no satellite or internet connectivity, download Docker images and Ollama model weights to your machine or a USB flash drive:

### Step 1: Pull Model Weights to Local Storage
```bash
# Pull LLM and embedding weights while connected to shore internet
ollama pull gemma4:12b
ollama pull nomic-embed-text
```

### Step 2: Save Container Images (Optional for Air-Gapped USB Transfer)
```bash
docker save ollama/ollama:latest -o ollama_image.tar
```

---

## 🛠️ Installation & Running via Docker Compose

### Windows Installation
1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (ensure WSL2 backend is enabled).
2. Clone or copy the Seabot directory:
   ```powershell
   cd seabot
   copy .env.example .env
   ```
3. Start the application:
   ```powershell
   docker compose up -d
   ```
4. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

### Linux Installation
1. Install Docker Engine and Docker Compose Plugin:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker-ce docker-compose-plugin
   ```
2. Setup environment:
   ```bash
   cd seabot
   cp .env.example .env
   ```
3. Launch services:
   ```bash
   sudo docker compose up -d
   ```
4. Access the web interface at `http://localhost:3000` (or `http://<VESSEL_LAN_IP>:3000`).

---

## 🧪 Testing & Verification

### 1. Run Unit & Integration Tests
```bash
cd backend
python -m pytest tests/unit tests/integration -v
```

### 2. Run Air-Gap Verification Test
The airgap test enforces strict network blocking (disallowing any outbound IP addresses except loopback) and validates system integrity:
```bash
python backend/tests/airgap_test.py
```

### 3. Run Benchmark Evaluation Suite (30 Q&A Pairs)
Seabot includes a benchmark suite containing 20 answerable vessel operation questions and 10 out-of-scope traps:
```bash
python eval/evaluate.py
```

---

## 📂 Project Architecture

```
seabot/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry, CORS, lifespan, SSE
│   │   ├── config.py                # Environment settings
│   │   ├── database.py              # Async SQLite engine
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── schemas.py               # Pydantic v2 schemas
│   │   ├── routers/
│   │   │   ├── chat.py              # SSE RAG streaming endpoint
│   │   │   ├── documents.py         # Multi-document upload & status
│   │   │   ├── viewer.py            # PyMuPDF page rendering & bbox highlights
│   │   │   ├── state.py             # User state persistence
│   │   │   └── health.py            # System health diagnostics
│   │   ├── services/
│   │   │   ├── ingestion/           # PDF, DOCX, Excel, OCR, Chunker
│   │   │   ├── retrieval/           # ChromaDB + SQLite FTS5 BM25 Hybrid RRF
│   │   │   └── llm/                 # Ollama client, Prompts A/B/C, Grounding
│   │   └── workers/
│   │       └── queue.py             # Background task queue
│   └── tests/                       # Unit, integration & airgap tests
├── frontend/
│   ├── src/
│   │   ├── components/              # Sidebar, ChatWindow, MessageInput, Viewer
│   │   ├── pages/                   # ChatPage, ViewerPage
│   │   ├── store/                   # Zustand local & server state sync
│   │   └── api/                     # Axios & SSE streaming client
├── eval/
│   ├── qa_pairs.json                # 30 Maritime Q&A evaluation benchmark
│   └── evaluate.py                  # Automated benchmark scoring script
├── sample_docs/
│   └── seed.py                      # Realistic maritime manual generator
├── docker-compose.yml
└── README.md
```

---

## 🛡️ Troubleshooting & FAQ

- **Ollama connection failed:** Ensure the Ollama container is running (`docker compose ps`) and model weights are present (`docker exec -it seabot-ollama ollama list`).
- **GPU Acceleration:** On systems with NVIDIA GPUs, install the NVIDIA Container Toolkit and uncomment the `deploy.resources.reservations.devices` block in `docker-compose.yml`.
- **Large file uploads:** The default upload limit is 200 MB per file. To change this, update `MAX_UPLOAD_MB` in `.env`.
