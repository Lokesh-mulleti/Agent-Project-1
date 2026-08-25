# 🤖 AI Tool-Calling Assistant & Interactive Web Studio

An autonomous, multi-provider AI Agent architecture equipped with dynamic tool calling (Function Calling) capabilities, a high-performance **FastAPI streaming backend**, and a **Cyber-Glass Web Studio UI**. 

The agent inspects user queries, determines when external capabilities are needed, invokes specialized tools (`Calculator`, `Currency Converter`, `AI Document Reader`, `Weather`, `Web Search`), feeds tool outputs back into the LLM context, and synthesizes accurate, real-time responses with live step visualizations.

---

## 🏛️ System Architecture

```
                          USER
                            │
               ┌────────────┴────────────┐
               ↓                         ↓
      Web Studio (Browser)        Terminal CLI
               │                         │
               └────────────┬────────────┘
                            ↓
                    ┌───────────────┐
                    │  FastAPI SSE  │
                    │   & Agent     │
                    └───────┬───────┘
                            ↓
                     ┌─────────────┐
                     │     LLM     │  (Gemini / OpenAI / Mock)
                     └──────┬──────┘
                            │
                 "What should I do?"
                 (Decides tool calls)
                            │
      ┌───────────┬─────────┼──────────┬───────────┐
      ↓           ↓         ↓          ↓           ↓
  Calculator  Currency  Doc Reader   Weather    Search
     Tool       Tool       Tool       Tool       Tool
     (AST)     (Live FX) (PDF/MD/TXT) (Meteo)   (DDG/Wiki)
      │           │         │          │           │
      └───────────┴─────────┼──────────┴───────────┘
                            ↓
                       Tool Result
                            │
                            ↓  Context Re-injection
                           LLM
                            │
                            ↓  Final Synthesis
                     Final Response + Live Step Chips
```

---

## 📂 Project Structure

```
Agent Project-1/
│
├── frontend/                        # Modern Cyber-Glass Web Studio SPA
│   ├── index.html                   # Semantic HTML5 UI (Chat, Doc Reader, Playground)
│   ├── style.css                    # Glassmorphism design system & tool visualizers
│   └── app.js                       # Real-time SSE streaming, file upload, & widgets
│
├── backend/                         # Modular FastAPI Backend & Agent Architecture
│   ├── app/
│   │   ├── __init__.py              # App package
│   │   ├── config.py                # Pydantic environment configuration
│   │   ├── server.py                # FastAPI server with SSE streaming & REST endpoints
│   │   ├── main.py                  # Unified CLI runner & server launcher
│   │   ├── agent/
│   │   │   ├── __init__.py          # Agent package (ToolAgent, ToolRegistry)
│   │   │   ├── agent.py             # Tool calling loop, schema generator, failover chain
│   │   │   └── prompts.py           # Core system instructions with 5-tool guidance
│   │   └── tools/
│   │       ├── __init__.py          # Tool package
│   │       ├── calculator.py        # AST-safe mathematical evaluator
│   │       ├── currency.py          # Real-time currency exchange converter
│   │       ├── doc_reader.py        # Multi-format doc parser, summary & highlights
│   │       ├── weather.py           # Real-time Open-Meteo weather integration
│   │       └── search.py            # DuckDuckGo & Wikipedia search tool
│   ├── requirements.txt             # Backend dependencies
│   └── tests/                       # Complete automated unit & integration test suite
│
├── .env                             # Local environment variables & API keys
├── .env.example                     # Template for API keys & settings
├── Dockerfile                       # Container deployment configuration
└── README.md                        # Documentation
```

---

## 🛠️ Built-in Agent Tools (5 Capabilities)

### 1. 🧮 Calculator (`calculate`)
- **Engine**: Safe Python Abstract Syntax Tree (AST) evaluator (`ast.NodeVisitor`).
- **Security**: Strict sandboxing—zero `eval()` or `exec()`. Malicious imports or OS operations are rejected at parsing time.
- **Operations**: Arithmetic (`+`, `-`, `*`, `/`, `//`, `%`), powers (`**`, `^`), functions (`sqrt`, `sin`, `cos`, `tan`, `log`, `exp`, `factorial`, `abs`, `round`, `floor`, `ceil`), and constants (`pi`, `e`, `tau`).
- **Resilience**: Automatically handles natural language preambles (e.g. `"what is the value for (192 + 193)?"`).

### 2. 💱 Currency Converter (`convert_currency`)
- **Engine**: Real-time conversion via public REST APIs (Frankfurter / Open Exchange API) with comprehensive offline USD parity fallback tables.
- **Coverage**: Supports 40+ global currencies (`USD`, `EUR`, `GBP`, `JPY`, `INR`, `CAD`, `AUD`, `CHF`, `CNY`, `SGD`, etc.).
- **Output**: Formatted exchange rates, inverse conversion rates, and timestamped summaries.

### 3. 📄 AI Document Reader & Highlighter (`read_document`)
- **Formats**: PDF (`pypdf`), Markdown, Plain Text, CSV, and JSON.
- **Capabilities**:
  - **Executive Summary**: 2-3 paragraph concise brief of the core subject.
  - **Key Highlights & Crucial Quotes**: Automatic scoring and extraction of high-importance metrics, findings, and conclusions.
  - **Context-Grounded Q&A**: Answers specific questions targeted at uploaded documents.
  - **Interactive Deck**: Drag-and-drop file upload zone with live visual cards in the Web UI.

### 4. ⛅ Live Weather (`get_weather`)
- **Engine**: Zero API key required—directly interfaces with Open-Meteo REST API.
- **Resolution**: Two-step geocoding and live meteorological data (temperature, apparent "feels like", humidity, wind speed, precipitation, WMO weather descriptions, and daily high/low).
- **Units**: Supports both Celsius and Fahrenheit.

### 5. 🔍 Web Search & Knowledge (`search_web`)
- **Engine**: Multi-tier factual retrieval (DuckDuckGo search, DuckDuckGo Instant Answer API, Wikipedia REST API).

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and set your preferred provider:

```bash
cp .env.example .env
```

```ini
# Choose: 'gemini', 'openai', or 'mock'
LLM_PROVIDER=gemini

# For Google Gemini:
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash

# For OpenAI:
OPENAI_API_KEY=your_actual_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

*(Note: If no API keys are provided, the assistant automatically runs in **Mock mode** offline!)*

---

## 💻 Running the Application

### 🌐 Launch the Web Studio UI (Recommended)
Start the FastAPI streaming server and open the Cyber-Glass Web UI:

```bash
# From project root:
python -m backend.app.main --web

# Or from inside backend directory:
cd backend
python -m app.main --web
```
- **Web UI:** `http://localhost:8000`
- **Interactive Swagger API Docs:** `http://localhost:8000/docs`

---

### 💻 Interactive Terminal CLI Mode
```bash
python -m backend.app.main
```
Or force mock mode (offline, no API keys needed):
```bash
python -m backend.app.main --mock
```

---

### ⚡ Single CLI Query Mode
```bash
# Math calculation
python -m backend.app.main -q "What is (150 * 4) + sqrt(256)?"

# Currency exchange
python -m backend.app.main -q "Convert 1500 USD to EUR and INR"

# Live weather & multi-tool query
python -m backend.app.main -q "What is the weather in Tokyo, and calculate 25 * 9/5 + 32?"
```

---

## 🐳 Docker Deployment

### Build the Docker Image:
```bash
docker build -t ai-tool-agent .
```

### Run the Web Studio UI:
```bash
docker run -p 8000:8000 --env-file .env ai-tool-agent
```
Open `http://localhost:8000` in your browser.

### Run in Terminal Mode:
```bash
docker run -it --rm --env-file .env ai-tool-agent python -m app.main
```

---

## 🧪 Running Automated Tests

Run the complete test suite covering all 5 tools, failovers, AST security, and FastAPI endpoints:

```bash
python -m pytest backend/tests/ -v
```

