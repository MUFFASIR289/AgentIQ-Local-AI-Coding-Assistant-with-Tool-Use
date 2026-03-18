# 🤖 CodeMentor AI Agent

> A locally-running AI agent powered by **qwen2:7b** via Ollama — your personal tutor for coding, programming, and AI.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Gradio](https://img.shields.io/badge/UI-Gradio-orange?logo=gradio)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20%7C%20qwen2:7b-green)
![License](https://img.shields.io/badge/License-MIT-purple)
![CI](https://github.com/YOUR_USERNAME/simple-ai-agent/actions/workflows/ci.yml/badge.svg)

---

## ✨ Features

- 🧠 **Smart AI Tutor** — Explains code, concepts, ML & AI at any level
- 🛠️ **Built-in Tools** — Run Python code, calculate math, generate templates
- 💬 **Beautiful Chat UI** — Dark-themed Gradio interface with streaming responses
- 🔒 **100% Local** — Your data never leaves your machine (no API keys!)
- 🐍 **Beginner Friendly** — Well-commented code, clear structure, easy setup
- 🧪 **Tested** — pytest suite included
- 🚀 **GitHub Ready** — CI/CD with GitHub Actions

---

## 📁 Project Structure

```
simple-ai-agent/
├── agent/                  # Core AI logic
│   ├── __init__.py
│   ├── agent.py            # ReAct agent loop + Ollama API calls
│   ├── tools.py            # Tool definitions and executors
│   └── prompts.py          # System prompt (personality + instructions)
│
├── ui/                     # User Interface
│   ├── __init__.py
│   └── app.py              # Gradio chat interface
│
├── utils/                  # Shared utilities
│   ├── __init__.py
│   └── helpers.py          # Logger, health checks, startup banner
│
├── tests/                  # Test suite
│   ├── __init__.py
│   └── test_agent.py       # pytest tests
│
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI pipeline
│
├── .vscode/
│   ├── settings.json       # Editor config
│   └── extensions.json     # Recommended extensions
│
├── .env.example            # Environment variable template
├── .gitignore
├── requirements.txt
├── main.py                 # ← Start here
└── README.md
```

---

## 🚀 Quick Start (Step by Step)

### 1. Prerequisites

Make sure you have these installed:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | [python.org](https://python.org) |
| Git | Any | [git-scm.com](https://git-scm.com) |
| Ollama | Latest | [ollama.com](https://ollama.com) |
| VS Code | Latest | [code.visualstudio.com](https://code.visualstudio.com) |

---

### 2. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/simple-ai-agent.git
cd simple-ai-agent
```

---

### 3. Set Up Virtual Environment

A virtual environment keeps your project's packages isolated from the rest of your system.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

You'll see `(venv)` in your terminal — that means it's active! ✅

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5. Set Up Ollama + qwen2:7b

```bash
# Start the Ollama server
ollama serve

# In a NEW terminal, pull the model (one-time, ~4GB download)
ollama pull qwen2:7b
```

Verify it works:
```bash
ollama run qwen2:7b "Hello! Can you help me learn Python?"
```

---

### 6. Run the Agent

```bash
python main.py
```

Your browser will open automatically at **http://localhost:7860** 🎉

---

## 🛠️ Available Tools

The agent can use these tools autonomously:

| Tool | What it does | Example |
|------|-------------|---------|
| `run_python` | Executes Python code safely | "Run: print([x**2 for x in range(5)])" |
| `calculate` | Evaluates math expressions | "What is sqrt(144) * pi?" |
| `get_datetime` | Returns current date & time | "What time is it?" |
| `explain_concept` | Structures concept explanations | "Explain recursion to a beginner" |
| `generate_code_template` | Creates starter code | "Give me a Flask API template" |

---

## 💬 Example Conversations

**Learning Python:**
```
You: Explain list comprehensions like I'm a beginner
AI: Great question! List comprehensions are a concise way to create lists...
```

**Running Code:**
```
You: Write and run a bubble sort in Python
AI: TOOL_CALL: run_python({"code": "..."})
    [runs code, shows output]
    Here's how bubble sort works...
```

**AI/ML concepts:**
```
You: What is the difference between supervised and unsupervised learning?
AI: Think of it this way — supervised learning is like learning with a teacher...
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=agent --cov=utils --cov-report=term-missing
```

---

## 🔧 Configuration

Copy `.env.example` to `.env` to customize settings:

```bash
cp .env.example .env
```

Edit `.env`:
```env
OLLAMA_URL=http://localhost:11434
MODEL_NAME=qwen2:7b
UI_PORT=7860
UI_SHARE=false
```

---

## 🌐 Using a Different Model

You can swap `qwen2:7b` for any Ollama-compatible model:

```bash
# Pull a different model
ollama pull llama3:8b
ollama pull mistral:7b
ollama pull codellama:7b  # great for code!
```

Then update `MODEL_NAME` in `agent/agent.py` or your `.env` file.

---

## 📤 Publishing to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "feat: initial CodeMentor AI agent"

# Create a repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/simple-ai-agent.git
git branch -M main
git push -u origin main
```

---

## 🗺️ What to Learn Next

Once comfortable with this project, explore:

1. **Add web search** — integrate DuckDuckGo or SerpAPI
2. **Memory / RAG** — store conversation history in a vector DB
3. **Multi-agent** — build specialized sub-agents
4. **Voice interface** — add Whisper for speech-to-text
5. **Fine-tuning** — fine-tune the model on your own data

---

## 📄 License

MIT — free to use, modify, and share.

---

## 🙏 Built With

- [Ollama](https://ollama.com) — local LLM runtime
- [qwen2:7b](https://ollama.com/library/qwen2) — the language model
- [Gradio](https://gradio.app) — the UI framework
- [pytest](https://pytest.org) — testing

---

*Made with ❤️ for learners everywhere.*


## ⚠️ Security Note
The `run_python` tool executes code locally on your own machine. 
Do not deploy this as a public web service without implementing 
proper sandboxing. It is designed for local, personal use only.