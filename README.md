# 🤖 BOTZI – Epicor AI Support Chatbot

> Production-ready RAG chatbot for Epicor ERP technical support.  
> **Stack:** FastAPI · Pinecone · OpenAI GPT-4o-mini · Supabase · Zoho WorkDrive (India DC) · Render · Zoho Cliq

---

## 📁 Project Structure

```
botzi/
├── backend/
│   ├── main.py                    ← FastAPI app entry point
│   ├── routers/
│   │   ├── chat.py                ← POST /api/chat/message
│   │   ├── feedback.py            ← POST /api/feedback
│   │   ├── analytics.py           ← GET  /api/analytics/*
│   │   ├── health.py              ← GET  /api/health  (keep-alive)
│   │   └── cliq.py                ← POST /api/cliq/message (Zoho Cliq bot)
│   ├── services/
│   │   ├── chat_service.py        ← Core RAG pipeline
│   │   ├── pinecone_service.py    ← Vector DB operations
│   │   ├── supabase_service.py    ← Analytics & feedback logging
│   │   └── cache_service.py       ← In-memory TTL cache
│   └── middleware/
│       └── rate_limiter.py        ← Per-IP rate limiting
├── zoho_sync/
│   ├── sync_service.py            ← WorkDrive → Pinecone ingestion
│   └── sync_runner.py             ← Entry point for cron job
├── frontend/
│   ├── index.html                 ← Production chat UI
│   └── analytics.html             ← Admin analytics dashboard
├── scripts/
│   ├── supabase_setup.sql         ← Run once in Supabase SQL editor
│   └── zoho_oauth_setup.py        ← One-time Zoho refresh token helper
├── .vscode/
│   ├── launch.json                ← VS Code run configs
│   └── settings.json
├── .env.example                   ← Copy to .env and fill in keys
├── requirements.txt
├── render.yaml                    ← Render deployment config
└── README.md
```

---

## 🚀 Complete Setup Guide

### Prerequisites
- Python 3.11+
- VS Code
- Git
- Accounts: OpenAI, Pinecone, Supabase, Zoho (India), Render

---

### Step 1 – Clone & Install

```bash
# In VS Code terminal
git clone <your-repo-url>
cd botzi

# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 2 – Create .env File

```bash
cp .env.example .env
```

Then open `.env` and fill in every value (see comments in the file).

---

### Step 3 – Supabase Tables Setup

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Create a new project (choose any region)
3. Go to **SQL Editor → New Query**
4. Paste the entire contents of `scripts/supabase_setup.sql`
5. Click **Run**
6. Copy your **Project URL** and **service_role API Key** into `.env`

---

### Step 4 – Pinecone Setup

1. Go to [https://app.pinecone.io](https://app.pinecone.io)
2. Create a free account
3. **Create Index:**
   - Name: `botzi-docs`
   - Dimensions: `1536`
   - Metric: `cosine`
   - Cloud: AWS  
   - Region: `us-east-1`
4. Copy your **API Key** into `.env`

> ✅ Pinecone Serverless indexes on the free tier are **permanent** –  
> your chunks are never auto-deleted unless you call delete() yourself.

---

### Step 5 – Zoho WorkDrive OAuth (India DC)

**This is a one-time setup to get your refresh token.**

1. Go to [https://api-console.zoho.in](https://api-console.zoho.in)
2. Click **Add Client → Server-based Application**
3. Fill in:
   - Client Name: `BOTZI`
   - Homepage URL: `https://botzi-api.onrender.com`
   - Redirect URI: `https://botzi-api.onrender.com/zoho/callback`
4. Copy **Client ID** and **Client Secret** into `.env`
5. Run the helper script:
   ```bash
   python scripts/zoho_oauth_setup.py
   ```
6. Follow the prompts – it will give you your **Refresh Token**
7. The script also lists your team folders so you can find **ZOHO_TEAM_FOLDER_ID**
8. Copy all values into `.env`

---

### Step 6 – Run Locally in VS Code

**Option A – VS Code Run Config:**
- Press `F5` → select **🚀 Run BOTZI Backend**

**Option B – Terminal:**
```bash
uvicorn backend.main:app --reload --port 8000
```

Open the chat UI:
```
frontend/index.html  ← open in browser (double-click or use Live Server extension)
```

API docs:
```
http://localhost:8000/docs
```

---

### Step 7 – Run First Sync (Load Documents)

```bash
# In VS Code terminal (with .env active)
python -m zoho_sync.sync_runner
```

This will:
- Scan all subfolders under your WorkDrive training docs folder
- Download and extract text from PDF, PPTX, DOCX, TXT files
- Chunk and embed everything into Pinecone
- Record what was synced in Supabase sync_log

**Subsequent runs only process NEW or CHANGED files.**

---

### Step 8 – Deploy to Render

1. Push your project to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial BOTZI deployment"
   git remote add origin https://github.com/your-username/botzi.git
   git push -u origin main
   ```

2. Go to [https://render.com](https://render.com) → **New → Blueprint**
3. Connect your GitHub repo
4. Render will detect `render.yaml` and create 3 services automatically:
   - `botzi-api` – FastAPI backend (Web Service)
   - `botzi-frontend` – Chat UI (Static Site)
   - `botzi-sync` – Daily WorkDrive sync (Cron Job)

5. In Render Dashboard → **botzi-api → Environment**, add all your `.env` values

---

### Step 9 – Keep Render Free Tier Alive 24/7

Render free tier sleeps after 15 minutes of inactivity.  
**Set up a keep-alive ping:**

1. Go to [https://cron-job.org](https://cron-job.org) → create free account
2. Create a new cron job:
   - URL: `https://botzi-api.onrender.com/api/ping`
   - Schedule: Every **1 minute**
3. Save – your backend will now stay alive 24/7

---

### Step 10 – Zoho Cliq Bot Setup

1. Go to [https://cliq.zoho.in](https://cliq.zoho.in)
2. Navigate to **Bots → Create Bot**
3. Bot Name: `BOTZI`
4. Incoming Webhook URL: `https://botzi-api.onrender.com/api/cliq/message`
5. Enable **Incoming Messages**
6. Save and add the bot to your Cliq channels

---

## 🔑 Key Features

| Feature | Implementation |
|---------|---------------|
| Anti-hallucination | Strict system prompt + similarity threshold filtering |
| Top-3 sources with page numbers | Integer page numbers from PDF/PPTX metadata |
| Instant repeat answers | TTL in-memory cache (1 hour default) |
| Conversation history | Per-session rolling 20-turn history |
| Clickable follow-up questions | 3 suggestions from GPT per response |
| Star rating feedback | 1-5 stars → stored in Supabase |
| Usage analytics | chat_interactions table → analytics dashboard |
| Auto doc sync | Zoho WorkDrive → Pinecone (daily cron, incremental) |
| 24/7 uptime | cron-job.org keep-alive ping every 60s |
| Rate limiting | 60 req/min per IP |
| Zoho Cliq integration | /api/cliq/message webhook |

---

## 📊 Analytics Dashboard

Open `frontend/analytics.html` in your browser (update `API` constant to your Render URL).

Shows:
- Total questions, unique users, avg response time
- Average star rating
- High confidence percentage
- Most frequently asked questions

---

## 🔄 Auto Sync Logic

```
WorkDrive scan → compare file_id + modified time vs Supabase sync_log
  ├─ File unchanged?  → SKIP (no re-embedding)
  ├─ File new?        → Download → Extract → Chunk → Embed → Upsert
  └─ File updated?    → Delete old vectors → Re-index new version
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `PINECONE_API_KEY` error | Check `.env` file is loaded correctly |
| Zoho token expired | Refresh tokens are long-lived – if expired, re-run `zoho_oauth_setup.py` |
| Subreport error answers | Make sure relevant docs are in WorkDrive and sync has been run |
| Render sleeping | Verify cron-job.org is pinging `/api/ping` every minute |
| No sources returned | Lower `SIMILARITY_THRESHOLD` in `.env` (try 0.65) |
| Empty answers | Check Pinecone index has vectors: `pinecone.describe_index_stats()` |

---

## 📝 Environment Variables Reference

See `.env.example` for full list with comments.

---

*BOTZI – Built for Mithilai Solutions · Epicor ERP AI Support*
