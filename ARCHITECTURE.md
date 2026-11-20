# Seabot Architecture Reference

## Project Root
`C:\Users\Sunit Kamble\.gemini\antigravity\scratch\seabot\`

## Directory Layout
```
seabot/
├── backend/                  # FastAPI Python 3.11 backend
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, SSE, routers
│   │   ├── config.py         # Settings from .env (pydantic-settings)
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   ├── models.py         # ORM: documents, chats, messages, message_sources, user_state, audit_log
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── chat.py       # POST /chat/ask (SSE), GET/POST/DELETE /chats
│   │   │   ├── documents.py  # POST /documents/upload, GET /documents, DELETE /documents/{id}
│   │   │   ├── viewer.py     # GET /viewer/{doc_id}/page/{page}
│   │   │   └── state.py      # GET/PUT /user_state
│   │   ├── services/
│   │   │   ├── ingestion/
│   │   │   │   ├── pipeline.py      # Orchestrates per-file parsing → chunking → indexing
│   │   │   │   ├── pdf_parser.py    # PyMuPDF: text, tables, images, page render, bbox
│   │   │   │   ├── docx_parser.py   # python-docx + LibreOffice headless → PDF
│   │   │   │   ├── excel_parser.py  # openpyxl: sheet rows → chunks
│   │   │   │   ├── ocr.py           # Tesseract OCR for scanned pages
│   │   │   │   ├── diagram.py       # Diagram detection + Gemma 4 vision captioning
│   │   │   │   └── chunker.py       # 500-800 token chunks, 100 overlap, metadata
│   │   │   ├── retrieval/
│   │   │   │   ├── vector_store.py  # ChromaDB persistent
│   │   │   │   ├── bm25_index.py    # SQLite FTS5 BM25
│   │   │   │   ├── hybrid.py        # RRF fusion + optional rerank
│   │   │   │   └── reranker.py      # bge-reranker (optional)
│   │   │   ├── llm/
│   │   │   │   ├── ollama_client.py # Ollama HTTP client, streaming
│   │   │   │   ├── prompts.py       # Prompts A, B, C as constants
│   │   │   │   └── grounding.py     # Citation verification
│   │   │   ├── history.py           # Chat/message CRUD
│   │   │   └── state_service.py     # user_state read/write
│   │   └── workers/
│   │       └── queue.py             # Background job queue (asyncio)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── airgap_test.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # React + Vite + Tailwind
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx
│   │   │   └── ViewerPage.tsx
│   │   ├── components/
│   │   │   ├── Sidebar.tsx         # Chat list + Document list
│   │   │   ├── ChatWindow.tsx      # Messages, source chips, thumbnails
│   │   │   ├── MessageInput.tsx    # Input + scope chips
│   │   │   ├── DocumentUpload.tsx  # Drag-drop uploader
│   │   │   ├── ClearHistoryModal.tsx
│   │   │   ├── PDFViewer.tsx       # PDF.js bundled
│   │   │   └── ExcelPreview.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   ├── useDocuments.ts
│   │   │   └── useLocalState.ts
│   │   ├── store/
│   │   │   └── appStore.ts         # Zustand store
│   │   └── api/
│   │       └── client.ts           # Fetch wrapper + SSE
│   ├── public/
│   │   └── pdf.worker.min.js       # Bundled PDF.js worker
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
├── sample_docs/              # Sample maritime documents
│   └── seed.py
├── eval/
│   ├── qa_pairs.json         # 30 Q&A pairs (20 answerable, 10 not)
│   └── evaluate.py
├── tests/
│   └── e2e/                  # Playwright E2E tests
├── .env.example
├── docker-compose.yml
└── README.md
```

## Key Constants
- Backend port: 8000
- Frontend port: 3000
- ChromaDB data: ./data/chroma
- SQLite DB: ./data/seabot.db
- Uploaded files: ./data/uploads
- Thumbnails: ./data/thumbnails
- Logs: ./data/logs/seabot.log

## API Endpoints
- POST   /api/documents/upload          # multipart, background job
- GET    /api/documents                 # list all
- DELETE /api/documents/{id}            # remove vectors + files
- POST   /api/chats                     # create chat
- GET    /api/chats                     # list all chats
- GET    /api/chats/{id}               # get chat with messages
- DELETE /api/chats/{id}               # delete chat
- PATCH  /api/chats/{id}               # rename chat
- POST   /api/chats/{id}/ask           # SSE stream answer
- POST   /api/chats/clear              # clear by time range
- GET    /api/viewer/{doc_id}/page/{n} # page image + highlight data
- GET    /api/state                    # user_state
- PUT    /api/state                    # save user_state
- GET    /api/health                   # health check

## DB Schema
```sql
-- documents
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  sha256 TEXT UNIQUE NOT NULL,
  pages INTEGER,
  file_type TEXT,  -- pdf|docx|xlsx
  status TEXT,     -- uploading|parsing|indexing|ready|failed
  error_msg TEXT,
  created_at DATETIME,
  size_bytes INTEGER
);

-- chats
CREATE TABLE chats (
  id TEXT PRIMARY KEY,
  title TEXT,
  created_at DATETIME,
  updated_at DATETIME
);

-- messages
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  chat_id TEXT REFERENCES chats(id),
  role TEXT,  -- user|assistant|system
  content TEXT,
  is_partial INTEGER DEFAULT 0,
  interrupted INTEGER DEFAULT 0,
  created_at DATETIME
);

-- message_sources
CREATE TABLE message_sources (
  id TEXT PRIMARY KEY,
  message_id TEXT REFERENCES messages(id),
  doc_id TEXT REFERENCES documents(id),
  doc_name TEXT,
  page INTEGER,
  chunk_id TEXT,
  chunk_text TEXT,
  bbox TEXT  -- JSON
);

-- user_state
CREATE TABLE user_state (
  id INTEGER PRIMARY KEY DEFAULT 1,
  active_chat_id TEXT,
  sidebar_collapsed INTEGER DEFAULT 0,
  sidebar_scroll INTEGER DEFAULT 0,
  viewer_doc_id TEXT,
  viewer_page INTEGER,
  input_draft TEXT,
  updated_at DATETIME
);

-- audit_log
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT,
  details TEXT,  -- JSON
  created_at DATETIME
);
```

## Chunk Metadata Schema
```json
{
  "chunk_id": "uuid",
  "doc_id": "uuid",
  "doc_name": "Main Engine Manual.pdf",
  "page": 42,
  "section_heading": "3.2 Fuel System",
  "chunk_type": "text|table|diagram|sheet_rows",
  "bbox": [x0, y0, x1, y1],
  "text": "...",
  "thumbnail_path": null,
  "sheet_name": null,
  "row_range": null
}
```

## Prompts (verbatim from spec)

### A. Answer System Prompt
```
You are Seabot, an assistant for seafarers. You answer ONLY from the CONTEXT passages below...
[Full prompt as specified]
```

### B. Diagram Understanding Prompt
```
You are reading one page of a ship technical manual...
[Full prompt as specified — returns JSON]
```

### C. Question Rewrite Prompt
```
Given the chat history and the latest user question, rewrite...
```
