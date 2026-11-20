# Seabot: Vessel Deployment Guide & Hardware Prerequisites

This guide defines **where Seabot runs physically and architecturally on a vessel**, the **exact hardware and software prerequisites**, and the **step-by-step procedure to operate it completely offline** with zero internet.

---

## 1. Where Seabot Runs on the Vessel

Seabot is designed for two standard vessel operational environments:

```
[Option A: Standalone Shipboard Laptop]
┌────────────────────────────────────────────────────────┐
│ Bridge / Cargo Control Room (CCR) / ECR Laptop         │
│  - Ollama Engine (127.0.0.1:11434)                     │
│  - FastAPI Backend (127.0.0.1:8001)                    │
│  - ChromaDB + SQLite FTS5 (Local Disk)                 │
│  - Vite / Nginx UI (http://127.0.0.1:3000)             │
│  - User: Single Officer / Engineer operating locally   │
└────────────────────────────────────────────────────────┘

[Option B: Vessel Local Area Network (LAN) Server]
┌────────────────────────────────────────────────────────┐
│ Central Server (Wheelhouse Rack / Ship Office Server)  │
│  - IP: 192.168.1.50 (Vessel Private Subnet)            │
│  - Docker / Native Seabot Stack Bound to 0.0.0.0       │
└───────────────▲──────────────────────────▲─────────────┘
                │ Ethernet / Ship Wi-Fi    │
       ┌────────┴─────────┐       ┌────────┴─────────┐
       │ Bridge Workstation│       │ ECR Tablet / PC  │
       │ http://192.168.1.50:3000│ │ http://192.168.1.50:3000│
       └──────────────────┘       └──────────────────┘
```

### Physical Location Options:
1. **Engine Control Room (ECR) / Cargo Control Room (CCR) Laptop:**  
   Runs directly on the Chief Engineer's or Chief Officer's workstation as a local standalone application.
2. **Central Wheelhouse / Ship Office Server:**  
   Runs as a central daemon on the vessel's internal server. Officers and crew connect from their laptops or ruggedized bridge tablets via the vessel's internal Wi-Fi/Ethernet without consuming any satellite bandwidth.

### Network & Port Configuration:
| Service | Internal Port | Local Loopback | Ship LAN Access |
| :--- | :--- | :--- | :--- |
| **Frontend Web UI** | `3000` | `http://127.0.0.1:3000` | `http://<VESSEL_SERVER_IP>:3000` |
| **Backend REST & SSE API** | `8001` | `http://127.0.0.1:8001` | `http://<VESSEL_SERVER_IP>:8001/api` |
| **Ollama Local LLM Inference** | `11434` | `http://127.0.0.1:11434` | Bound strictly to loopback (`127.0.0.1`) for security |

---

## 2. Hardware Profiles & Prerequisites

Select the hardware profile matching your vessel's hardware specifications (configured in `.env` via `HARDWARE_PROFILE`):

| Profile | Target Machine | RAM | CPU / GPU | LLM Model | Storage Required |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** | Rugged vessel field laptop / older PC | **8 GB** | Quad-core CPU (Intel i5/i7 8th gen+) | `gemma4:e4b` or `llama3:8b-instruct-q4` | 30 GB SSD |
| **STANDARD** *(Default)* | Modern Shipboard Workstation / Laptop | **16 GB** | 6-8 core CPU, or entry GPU (RTX 3050/4050) | `gemma4:12b` or `llama3:latest` | 50 GB SSD |
| **HIGH** | Dedicated Ship Server / GPU Workstation | **32 GB+** | Dedicated NVIDIA GPU (8 GB+ VRAM) | `gemma4:26b` or `gemma4:31b` | 100 GB NVMe SSD |

> [!IMPORTANT]
> **Solid-State Drive (SSD) is Mandatory**: Mechanical hard drives (HDDs) will cause slow model weight loading and high retrieval latency. Always deploy on an SSD or NVMe drive.

---

## 3. Software Prerequisites (Prior to Embarkation / Port Setup)

Because the vessel operates air-gapped at sea, the software runtime must be installed **while in port or prepared on an encrypted USB thumb drive**:

### Windows Workstation / Laptop (Native Mode):
1. **Operating System:** Windows 10 (64-bit) or Windows 11.
2. **Python Environment:** Python 3.11.x (Installed with "Add Python to PATH").
3. **Node.js Environment:** Node.js v20 LTS (or bundled portable Node binary in `scratch/node-v20.18.0-win-x64`).
4. **Ollama for Windows:** Installed from [ollama.com](https://ollama.com) (installed to `AppData\Local\Programs\Ollama\ollama.exe`).
5. **OCR & Document Engine (Optional for Scanned Docs):**
   - **Tesseract OCR:** Installed to `C:\Program Files\Tesseract-OCR\tesseract.exe` (for scanned PDFs).
   - **LibreOffice (Headless):** Installed to `C:\Program Files\LibreOffice\program\soffice.exe` (converts `.docx` files to PDF for true page citations).

### Linux Shipboard Server (Docker Mode):
1. **Operating System:** Ubuntu Server 22.04 LTS, Debian 12, or Rocky Linux 9.
2. **Docker Engine & Docker Compose:** Docker v24+ with `docker compose`.
3. **NVIDIA Container Toolkit:** (Only required if deploying with an NVIDIA GPU).

---

## 4. Pre-Departure Model Weights & Data Bundling

Before the vessel leaves port (while internet is still accessible), the required model weights and pip packages must be cached locally:

```powershell
# 1. Pull Embedding Model (768-dim, fast CPU inference)
ollama pull nomic-embed-text

# 2. Pull Chat & Reasoning Model
ollama pull llama3:latest
# Or for standard profile:
# ollama pull gemma4:12b

# 3. Verify models are present offline:
ollama list
```

Once downloaded, the model weights live permanently in `~/.ollama/models` on disk and will **never request external internet** during voyage.

---

## 5. Daily Operation on the Vessel

### Option 1: Native Windows Launch (Single-Click)
Run the automated batch script located in the project root:
```bat
start.bat
```
This launcher automatically:
1. Verifies Ollama is running in the background.
2. Boots the FastAPI backend on port `8001`.
3. Boots the frontend UI on port `3000` (bound to `0.0.0.0` for vessel LAN access).
4. Opens `http://127.0.0.1:3000` in the default browser.

### Option 2: Linux / Docker Launch
```bash
docker compose up -d
```
All containers (backend, frontend nginx, chroma vector store) start up in an isolated bridge network with outbound WAN access disabled.

---

## 6. Vessel LAN Multi-User Access Setup

To allow engineers in the Engine Control Room or bridge officers to access Seabot from their tablets or secondary PCs:
1. Identify the host machine's local IP address on the ship network (e.g. `192.168.1.50`).
2. Ensure Windows Defender Firewall allows incoming traffic on port `3000`.
3. On any device connected to the vessel LAN, open:
   ```
   http://192.168.1.50:3000
   ```
4. Seabot loads instantly with dark mode enabled for bridge night-watch compliance.
