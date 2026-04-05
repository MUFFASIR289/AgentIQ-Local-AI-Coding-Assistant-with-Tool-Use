"""
main.py — Entry point for CodeMentor AI Agent.
Run: python main.py

Startup sequence:
  1. Load .env file (Langfuse keys, config)
  2. Print status banner (Ollama, model, Langfuse)
  3. Initialise Langfuse client (or None if not configured)
  4. Build the Gradio UI, injecting the Langfuse client into the agent
  5. Launch the web server
"""

from utils.helpers import print_startup_banner, init_langfuse
from ui.app import build_ui

if __name__ == "__main__":

    # Step 1 + 2: print status banner (also loads .env via helpers.py)
    print_startup_banner(model="qwen2:7b", port=7860)

    # Step 3: initialise Langfuse — returns a client if credentials are
    # present in .env, or None if not configured (tracing gracefully disabled)
    langfuse_client = init_langfuse()

    # Step 4: build the Gradio UI, passing the Langfuse client through
    # so the AIAgent inside the UI can create traces for every conversation turn
    demo = build_ui(langfuse_client=langfuse_client)

    # Step 5: launch the local web server
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        inbrowser=True,
    )