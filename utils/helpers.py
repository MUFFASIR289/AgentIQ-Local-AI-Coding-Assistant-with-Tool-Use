"""
Utility helpers — Logging, Ollama health checks, config loading
"""

import json
import requests
import logging
from pathlib import Path
from datetime import datetime


# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────

def setup_logger(name: str = "agent", level: int = logging.INFO) -> logging.Logger:
    """Create a clean, coloured console logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        fmt = logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger


# ──────────────────────────────────────────────
#  OLLAMA HEALTH CHECK
# ──────────────────────────────────────────────

def check_ollama_running(url: str = "http://localhost:11434") -> bool:
    """Return True if Ollama server is reachable."""
    try:
        r = requests.get(url, timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def check_model_available(model: str = "qwen2:7b", url: str = "http://localhost:11434") -> bool:
    """Return True if the specified model is pulled in Ollama."""
    try:
        r = requests.get(f"{url}/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return any(model in m for m in models)
        return False
    except Exception:
        return False


def print_startup_banner(model: str = "qwen2:7b", port: int = 7860):
    """Print a friendly startup message."""
    ollama_ok = check_ollama_running()
    model_ok = check_model_available(model) if ollama_ok else False

    ollama_status = "✅ Running" if ollama_ok else "❌ Not found — run: ollama serve"
    model_status = "✅ Available" if model_ok else f"❌ Not pulled — run: ollama pull {model}"

    banner = f"""
╔══════════════════════════════════════════════╗
║          🤖  CodeMentor AI Agent             ║
╠══════════════════════════════════════════════╣
║  Ollama:  {ollama_status:<34} ║
║  Model:   {model_status:<34} ║
║  UI:      http://localhost:{port:<18} ║
╚══════════════════════════════════════════════╝
"""
    print(banner)

    if not ollama_ok:
        print("⚠️  Start Ollama first:  ollama serve")
        print(f"⚠️  Pull the model:      ollama pull {model}")
        print()
