# Monday.com BI Agent

A FastAPI-powered Business Intelligence agent that answers founder-level questions by fetching **live data** from Monday.com boards.

## Architecture

```
FastAPI (Python) ──► Monday.com GraphQL API   (live board data)
                 ──► Anthropic Claude API      (BI analysis)
                 ◄── HTML/CSS/JS Frontend      (single-page chat)
```

## Features

- 🔴 **Live Monday.com API calls** — no caching, every query hits the API
- 🧠 **Short-term memory** — last 5 conversations used as context
- 🔍 **Visible tool/API trace** — right panel shows every API call in real-time
- 📊 **BI insights** — revenue, pipeline, sector performance, AR analysis
- 💬 **Conversational** — follow-up questions with context

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure .env
```bash
cp .env.example .env
# Edit .env with your actual keys
```

Required keys:
- `MONDAY_API_KEY` — Monday.com API key (Admin > API)
- `MONDAY_BOARD_WO` — Work Orders board ID (from board URL)
- `MONDAY_BOARD_DEALS` — Deals board ID (from board URL)
- `ANTHROPIC_API_KEY` — Anthropic API key

### 3. Import data to Monday.com
- Import `Work_Order_Tracker_Data.xlsx` as a new board → "Work Orders"
- Import `Deal_funnel_Data.xlsx` as a new board → "Deals"
- Note the board IDs from the URLs and add to `.env`

### 4. Run
```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000

## How Monday Board IDs work

When you open a board in Monday.com, the URL looks like:
```
https://yourteam.monday.com/boards/1234567890
```
The number at the end (`1234567890`) is your Board ID.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Chat UI |
| POST | `/query` | Submit BI query |
| GET | `/health` | Config status |
| GET | `/memory` | View memory |
| DELETE | `/memory` | Clear memory |

## Decision Log

### Tech Stack Choices

**FastAPI** — Async support for non-blocking Monday.com + Anthropic API calls. Auto OpenAPI docs. Minimal boilerplate.

**Plain HTML/CSS/JS** — No build step, instant loading, easy to host anywhere. The frontend is sophisticated enough without adding React overhead for a single-page chat.

**httpx** — Async HTTP client that works natively with FastAPI's async handlers.

**In-memory sessions** — The assignment requires short-term memory across 5 chats. A simple list works perfectly for a prototype; no DB overhead.

**Claude claude-opus-4-5** — Best reasoning quality for BI analysis on messy data with nulls and inconsistent formats.

### Data Strategy

Every query triggers **fresh Monday.com API calls** — no caching. The full dataset is passed to Claude with instructions to:
- Treat empty/null/nan as missing
- Normalize currency and date formats
- Communicate data quality caveats in the response

### Memory Design

Last 5 Q&A pairs are stored in memory and injected into the Claude system prompt as context. This enables follow-up questions ("show me just the energy ones" after asking about pipeline).
