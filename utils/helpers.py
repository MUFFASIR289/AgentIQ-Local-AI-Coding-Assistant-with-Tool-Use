"""
Utility helpers — Logging, Ollama health checks, Langfuse initialisation.

Langfuse is initialised here once and imported by agent.py.
If the Langfuse credentials are missing or invalid, the module
gracefully disables tracing so the agent continues to work normally.
This pattern is called "graceful degradation" — observability is
optional infrastructure, not core functionality.
"""

import os
import logging
import requests
from dotenv import load_dotenv

# Load .env file into environment variables so os.getenv() can read them.
# This must happen before any os.getenv() calls below.
# dotenv is included with langfuse's dependencies, so no extra install needed.
load_dotenv()


# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────

def setup_logger(name: str = "agent", level: int = logging.INFO) -> logging.Logger:
    """
    Create a clean, consistently formatted console logger.

    Python's logging module is the professional alternative to print()
    for debugging. It adds timestamps, severity levels (INFO/WARNING/ERROR),
    and the module name to every message automatically.
    """
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


logger = setup_logger("utils")


# ──────────────────────────────────────────────
#  OLLAMA HEALTH CHECKS
# ──────────────────────────────────────────────

def check_ollama_running(url: str = "http://localhost:11434") -> bool:
    """Return True if the Ollama server is reachable."""
    try:
        r = requests.get(url, timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def check_model_available(
    model: str = "qwen2:7b",
    url: str = "http://localhost:11434",
) -> bool:
    """Return True if the specified model is pulled and ready in Ollama."""
    try:
        r = requests.get(f"{url}/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return any(model in m for m in models)
        return False
    except Exception:
        return False


# ──────────────────────────────────────────────
#  LANGFUSE INITIALISATION
# ──────────────────────────────────────────────

def init_langfuse():
    """
    Initialise the Langfuse client using credentials from environment variables.

    Returns a Langfuse client instance if credentials are present and valid,
    or None if credentials are missing — in which case tracing is silently
    disabled and the agent continues to work normally.

    This is called once at startup and the result is passed into the AIAgent
    constructor so every conversation turn can create a trace.

    Why environment variables?
    --------------------------
    Langfuse keys are secrets — they authenticate you to your dashboard.
    Hardcoding them in source code would expose them on GitHub. Instead,
    we store them in a .env file (which is gitignored) and read them at
    runtime using os.getenv(). The .env.example file shows the structure
    without containing real values, so other developers know what to fill in.
    """
    public_key  = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key  = os.getenv("LANGFUSE_SECRET_KEY", "")
    host        = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # Check if real credentials were provided (not placeholder text)
    keys_present = (
        public_key
        and secret_key
        and "your-public-key" not in public_key
        and "your-secret-key" not in secret_key
    )

    if not keys_present:
        logger.warning(
            "Langfuse credentials not found in .env — tracing disabled. "
            "Add LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable."
        )
        return None

    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

        # auth_check() verifies the keys are valid by making a test API call.
        # It raises an exception if the credentials are wrong.
        client.auth_check()

        logger.info(f"✅ Langfuse connected → {host}")
        return client

    except ImportError:
        logger.warning("langfuse package not installed. Run: pip install langfuse")
        return None
    except Exception as e:
        logger.warning(f"Langfuse init failed (tracing disabled): {e}")
        return None


# ──────────────────────────────────────────────
#  STARTUP BANNER
# ──────────────────────────────────────────────

def print_startup_banner(model: str = "qwen2:7b", port: int = 7860):
    """Print a friendly status table in the terminal when the agent starts."""
    ollama_ok = check_ollama_running()
    model_ok  = check_model_available(model) if ollama_ok else False

    ollama_status = "✅ Running"  if ollama_ok else "❌ Not found — run: ollama serve"
    model_status  = "✅ Available" if model_ok  else f"❌ Not pulled — run: ollama pull {model}"

    lf_key    = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    lf_status = "✅ Configured" if lf_key and "your-public-key" not in lf_key else "⚠️  Not configured (optional)"

    banner = f"""
╔══════════════════════════════════════════════╗
║          🤖  CodeMentor AI Agent             ║
╠══════════════════════════════════════════════╣
║  Ollama:    {ollama_status:<32} ║
║  Model:     {model_status:<32} ║
║  Langfuse:  {lf_status:<32} ║
║  UI:        http://localhost:{port:<15} ║
╚══════════════════════════════════════════════╝
"""
    print(banner)

    if not ollama_ok:
        print("⚠️  Start Ollama first:  ollama serve")
        print(f"⚠️  Pull the model:      ollama pull {model}")
        print()