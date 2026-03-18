"""
main.py — Entry point for CodeMentor AI Agent.
Run this file to start the app: python main.py

How it works:
  1. print_startup_banner() checks if Ollama is running and the model is available.
  2. build_ui() constructs the Gradio Blocks interface and returns it.
  3. demo.launch() starts the local web server and opens your browser.
"""

from utils.helpers import print_startup_banner
from ui.app import build_ui

if __name__ == "__main__":

    # Step 1 — print a friendly status check in the terminal
    print_startup_banner(model="qwen2:7b", port=7860)

    # Step 2 — build the Gradio UI (returns a gr.Blocks object)
    demo = build_ui()

    # Step 3 — launch the web server
    # Gradio 6 compatible arguments only:
    #   server_name : "0.0.0.0" means "accept connections from any device on the network"
    #                 Use "127.0.0.1" if you only want localhost access.
    #   server_port : the port your browser will connect to (http://localhost:7860)
    #   inbrowser   : automatically opens a browser tab when the server starts
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        inbrowser=True,
    )